# TODO: check logging
from bs4 import BeautifulSoup

from ffun.core import logging
from ffun.domain.entities import AbsoluteUrl, UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, adjust_classic_url
from ffun.feeds_discoverer.entities import Context, Discoverer, Result, Status
from ffun.loader import domain as lo_domain
from ffun.loader import errors as lo_errors
from ffun.parsers import entities as p_entities

logger = logging.get_module_logger()


async def _discover_adjust_url(context: Context) -> tuple[Context, Result | None]:
    url = normalize_classic_unknown_url(context.raw_url)

    if url is None:
        return context, Result(feeds=[], status=Status.incorrect_url)

    return context.replace(url=url), None


async def _discover_load_url(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None

    try:
        response = await lo_domain.load_content_with_proxies(context.url)
        content = await lo_domain.decode_content(response)
    except lo_errors.LoadError:
        logger.info("can_not_access_content")
        return context, Result(feeds=[], status=Status.cannot_access_url)
    except Exception:
        logger.exception("unexpected_error_while_parsing_feed")
        return context, Result(feeds=[], status=Status.cannot_access_url)

    return context.replace(content=content), None


async def _discover_extract_feed_info(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None
    assert context.content is not None

    try:
        feed_info = await lo_domain.parse_content(context.content, original_url=context.url)
    except lo_errors.LoadError:
        logger.info("feed_not_found_at_start_url")
        return context, None
    except Exception:
        logger.exception("unexpected_error_while_parsing_feed")
        return context, None

    return context, Result(feeds=[feed_info], status=Status.feeds_found)


async def _discover_create_soup(context: Context) -> tuple[Context, Result | None]:
    assert context.content is not None

    try:
        soup = BeautifulSoup(context.content, "html.parser")
    except Exception:
        logger.exception("unexpected_error_while_parsing_html")
        return context, Result(feeds=[], status=Status.not_html)

    return context.replace(soup=soup), None


async def _discover_extract_feeds_from_links(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None
    assert context.soup is not None

    links_to_check = set()

    for link in context.soup("link"):
        if link.has_attr("href"):
            if link.has_attr("rel") and any(
                rel in link["rel"] for rel in ["author", "help", "icon", "license", "pingback", "search", "stylesheet"]
            ):
                continue
            links_to_check.add(adjust_classic_url(link["href"], context.url))

    logger.info("links_to_check", links_to_check=links_to_check)

    return context.replace(candidate_urls=context.candidate_urls | links_to_check), None


# TODO: test
async def _discover_extract_feeds_from_anchors(context: Context) -> tuple[Context, Result | None]:
    assert context.soup is not None

    links_to_check = set()

    # TODO: can be very-very long, must be improved
    for link in list(context.soup("a")):
        if link.has_attr("href"):
            links_to_check.add(link["href"])

    logger.info("links_to_check", links_to_check=links_to_check)

    return context.replace(candidate_urls=context.candidate_urls | links_to_check), None


# TODO: test
async def _discover_check_candidate_links(context: Context) -> tuple[Context, Result | None]:  # noqa: CCR001
    results: list[Result] = []

    for link in context.candidate_urls:
        # TODO: add concurrency
        # TODO: check depth
        results.append(await discover(url=link, depth=context.depth - 1, discoverers=context.discoverers))

    feeds_mapping: dict[AbsoluteUrl, p_entities.FeedInfo] = {}

    for result in results:
        for feed_info in result.feeds:

            # TODO: replace by uid?
            if feed_info.url in feeds_mapping:
                logger.info("feed_already_found", feed_url=feed_info.url)
                continue

            feeds_mapping[feed_info.url] = feed_info

    feeds = list(feeds_mapping.values())
    feeds.sort(key=lambda feed_info: feed_info.title)

    logger.info("feeds", result_links=[feed_info.url for feed_info in feeds])

    context.candidate_urls.clear()

    if not feeds:
        return context, None

    return context, Result(feeds=feeds, status=Status.feeds_found)


# TODO: teest
async def _discover_stop_recursion(context: Context) -> tuple[Context, Result | None]:
    if context.depth == 0:
        return context, Result(feeds=[], status=Status.no_feeds_found)

    return context, None


# TODO: test list
_discoverers = [
    _discover_adjust_url,
    _discover_load_url,
    _discover_extract_feed_info,
    _discover_stop_recursion,
    _discover_create_soup,
    _discover_extract_feeds_from_links,
    _discover_check_candidate_links,
    _discover_extract_feeds_from_anchors,
    _discover_check_candidate_links,
]


# TODO: test
async def discover(url: UnknownUrl, depth: int, discoverers: list[Discoverer] = _discoverers) -> Result:
    context = Context(raw_url=url, depth=depth, discoverers=discoverers)

    for discoverer in discoverers:
        context, result = await discoverer(context)

        if result is not None:
            return result

    return Result(feeds=[], status=Status.no_feeds_found)
