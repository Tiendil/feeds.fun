import asyncio
import re

from bs4 import BeautifulSoup

from ffun.core import logging
from ffun.domain.entities import AbsoluteUrl, UnknownUrl
from ffun.domain.urls import (
    adjust_classic_url,
    construct_f_url,
    filter_out_duplicated_urls,
    get_parent_url,
    normalize_classic_unknown_url,
    to_feed_url,
    url_has_extension,
)
from ffun.feeds_discoverer.entities import Context, Discoverer, Result, Status
from ffun.loader import domain as lo_domain
from ffun.loader import errors as lo_errors
from ffun.parsers import entities as p_entities

logger = logging.get_module_logger()


async def _discover_adjust_url(context: Context) -> tuple[Context, Result | None]:

    logger.info("discovering_adjusting_url", raw_url=context.raw_url)

    absolute_url = normalize_classic_unknown_url(context.raw_url)

    logger.info("discovering_absolute_url", raw_url=context.raw_url, adjusted_url=absolute_url)

    if absolute_url is None:
        logger.info("discovering_incorrect_url")
        return context, Result(feeds=[], status=Status.incorrect_url)

    url = to_feed_url(absolute_url)

    logger.info("discovering_normalized_url", raw_url=context.raw_url, adjusted_url=url)

    return context.replace(url=url), None


async def _discover_load_url(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None

    logger.info("discovering_loading_content", url=context.url)

    try:
        response = await lo_domain.load_content_with_proxies(context.url)
        content = await lo_domain.decode_content(response)
    except lo_errors.LoadError:
        logger.info("can_not_access_content")
        return context, Result(feeds=[], status=Status.cannot_access_url)
    except Exception:
        logger.exception("unexpected_error_while_parsing_feed")
        return context, Result(feeds=[], status=Status.cannot_access_url)

    logger.info("discovering_content_loaded", url=context.url, content_size=len(content))

    return context.replace(content=content), None


async def _discover_extract_feed_info(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None
    assert context.content is not None

    logger.info("discovering_extracting_feed_info", url=context.url)

    try:
        feed_info = await lo_domain.parse_content(context.content, original_url=context.url)
    except lo_errors.LoadError:
        logger.info("feed_not_found_at_start_url")
        return context, None
    except Exception:
        logger.exception("unexpected_error_while_parsing_feed")
        return context, None

    logger.info("discovering_feed_info_extracted", feed_info=feed_info)

    return context, Result(feeds=[feed_info], status=Status.feeds_found)


async def _discover_create_soup(context: Context) -> tuple[Context, Result | None]:
    assert context.content is not None

    logger.info("discovering_creating_soup")

    try:
        soup = BeautifulSoup(context.content, "html.parser")
    except Exception:
        logger.exception("unexpected_error_while_parsing_html")
        return context, Result(feeds=[], status=Status.not_html)

    logger.info("discovering_soup_created")

    return context.replace(soup=soup), None


async def _discover_extract_feeds_from_links(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None
    assert context.soup is not None

    logger.info("discovering_extracting_feeds_from_links", url=context.url)

    links_to_check = set()

    for link in context.soup("link"):
        if link.has_attr("href"):
            if link.has_attr("rel") and any(
                rel in link["rel"] for rel in ["author", "help", "icon", "license", "pingback", "search", "stylesheet"]
            ):
                continue
            links_to_check.add(adjust_classic_url(link["href"], context.url))

    logger.info("discovering_links_extracted", links_to_check=links_to_check)

    return context.replace(candidate_urls=context.candidate_urls | links_to_check), None


async def _discover_extract_feeds_from_anchors(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None

    logger.info("discovering_extracting_feeds_from_anchors", url=context.url)

    allowed_extensions = [".xml", ".rss", ".atom", ".rdf", ".feed", ".php", ".asp", ".aspx", ".json", ".cgi", ""]

    assert context.soup is not None

    anchors_to_check = set()

    for anchor in list(context.soup("a")):
        if anchor.has_attr("href"):
            url = anchor["href"]

            if not url_has_extension(url, allowed_extensions):
                continue

            anchors_to_check.add(adjust_classic_url(url, context.url))

    logger.info("discovering_anchors_extracted", anchors_to_check=anchors_to_check)

    return context.replace(candidate_urls=context.candidate_urls | anchors_to_check), None


async def _discover_check_parent_urls(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None

    logger.info("discovering_checking_parent_urls", url=context.url)

    parent_url = get_parent_url(context.url)

    if parent_url is None:
        logger.info("discovering_no_parent")
        return context, None

    # always check parents on depth of 1 (a.k.a., we expect html with links to feeds)
    result = await discover(url=parent_url, depth=1, discoverers=context.discoverers)

    if result.feeds:
        logger.info("discovering_parent_extracted", parent_url=parent_url)
        return context, result

    logger.info("discovering_no_parent_extracted")
    return context, None


async def _discover_check_candidate_links(context: Context) -> tuple[Context, Result | None]:  # noqa: CCR001

    logger.info("discovering_checking_links", candidate_links=context.candidate_urls)

    filtered_links = filter_out_duplicated_urls(context.candidate_urls)

    tasks = []

    for link in filtered_links:
        tasks.append(discover(url=link, depth=context.depth - 1, discoverers=context.discoverers))

    results: list[Result] = await asyncio.gather(*tasks)

    feeds: list[p_entities.FeedInfo] = []

    for result in results:
        feeds.extend(result.feeds)

    feeds.sort(key=lambda feed_info: feed_info.title)

    if not feeds:
        logger.info("discovering_checking_links_no_feeds_found")
        return context.replace(candidate_urls=set()), None

    logger.info("discovering_checking_links_feeds_found", result_links=[feed_info.url for feed_info in feeds])

    return context.replace(candidate_urls=set()), Result(feeds=feeds, status=Status.feeds_found)


async def _discover_stop_recursion(context: Context) -> tuple[Context, Result | None]:

    logger.info("discovering_check_recursion", depth=context.depth)

    if context.depth == 0:
        logger.info("discovering_recursion_stopped")
        return context, Result(feeds=[], status=Status.no_feeds_found)

    logger.info("discovering_recursion_continued")

    return context, None


_RE_REDDIT_PATH_PREFIX = re.compile(r"^/r/[^/]+/?")


async def _discover_extract_feeds_for_reddit(context: Context) -> tuple[Context, Result | None]:
    """New Reddit site has no links to RSS feeds => we construct them."""
    assert context.url is not None

    logger.info("discovering_reddit_extracting_feeds", url=context.url)

    f_url = construct_f_url(context.url)

    assert f_url is not None

    if f_url.host not in ("www.reddit.com", "reddit.com", "old.reddit.com"):
        # We are not interested in not reddit.com domains
        logger.info("discovering_reddit_not_reddit_domain")
        return context, None

    if f_url.host == "old.reddit.com":
        # Old Reddit site has marked RSS urls in the header
        logger.info("discovering_reddit_old_reddit_domain")
        return context, None

    match = _RE_REDDIT_PATH_PREFIX.match(str(f_url.path))

    if match is None:
        logger.info("discovering_reddit_not_reddit_path")
        return context, None

    base_path = match.group()

    if not base_path.endswith("/"):
        base_path += "/"

    f_url.path = f"{base_path}.rss"
    f_url.query = None

    # this check is required to stop recursion on _discover_check_candidate_links
    if str(f_url) == context.url:
        logger.info("discovering_reddit_same_url")
        return context, None

    logger.info("discovering_reddit_feed", feed_url=f_url)

    return context.replace(candidate_urls={str(f_url)}), None


# Note: we do not add internal feed discoverer here (like db check: url -> uid -> feed_id), because
#       - we do not expect significant performance improvement
#       - internal feed data (news list) may be slightly outdated (not containing the latest news)
_discoverers = [
    _discover_adjust_url,
    # This Reddit urls hack MUST go before loading url
    # because Reddit blocks access to the non-rss urls for bots
    #
    # TODO: Should we simulate browser behavior?
    #       Better not to, but it may be the only way to get the page data.
    _discover_extract_feeds_for_reddit,
    _discover_check_candidate_links,
    _discover_load_url,
    _discover_extract_feed_info,
    _discover_stop_recursion,
    _discover_create_soup,
    _discover_extract_feeds_from_links,
    _discover_check_candidate_links,
    _discover_extract_feeds_from_anchors,
    _discover_check_candidate_links,
    _discover_check_parent_urls,
]


async def discover(url: UnknownUrl | AbsoluteUrl, depth: int, discoverers: list[Discoverer] = _discoverers) -> Result:

    logger.info("discovering_start", url=url, depth=depth)

    context = Context(raw_url=UnknownUrl(url), depth=depth, discoverers=discoverers)

    for discoverer in discoverers:
        context, result = await discoverer(context)

        if result is not None:
            logger.info("discovering_finished", feeds_found=len(result.feeds))
            return result

    logger.info("discovering_finished", feeds_found=0)

    return Result(feeds=[], status=Status.no_feeds_found)
