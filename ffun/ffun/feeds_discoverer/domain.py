# TODO: do we need yarl? we have furl already
# TODO: check logging
import yarl
from bs4 import BeautifulSoup

from ffun.domain.urls import fix_full_url
from ffun.core import logging
from ffun.loader import domain as lo_domain
from ffun.loader import errors as lo_errors
from ffun.parsers import entities as p_entities
from ffun.feeds_discoverer.entities import Result, Context, Status, Discoverer

logger = logging.get_module_logger()


async def _discover_normalize_url(context: Context) -> tuple[Context, Result | None]:
    context.url = fix_full_url(context.raw_url)

    if context.url is None:
        return context, Result(feeds=[], status=Status.incorrect_url)

    return context, None


async def _discover_load_url(context: Context) -> tuple[Context, Result | None]:
    assert context.url is not None

    try:
        response = await lo_domain.load_content_with_proxies(context.url)
        context.content = await lo_domain.decode_content(response)
    except lo_errors.LoadError:
        logger.info("can_not_access_content")
        return context, Result(feeds=[], status=Status.cannot_access_url)
    except Exception:
        logger.exception("unexpected_error_while_parsing_feed")
        return context, Result(feeds=[], status=Status.cannot_access_url)

    return context, None


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


# TODO: test
async def _discover_create_soup(context: Context) -> tuple[Context, Result | None]:
    assert context.content is not None

    try:
        context.soup = BeautifulSoup(context.content, "html.parser")
    except Exception:
        logger.exception("unexpected_error_while_parsing_html")
        return context, Result(feeds=[], status=Status.not_html)

    return context, None


# TODO: test
async def _discover_extract_feeds_from_links(context: Context) -> tuple[Context, Result | None]:
    assert context.soup is not None

    links_to_check = set()

    for link in context.soup("link"):
        if link.has_attr("href"):
            links_to_check.add(link["href"])

    logger.info("links_to_check", links_to_check=links_to_check)

    context.candidate_urls.extend(links_to_check)

    return context, None


# TODO: test
async def _discover_extract_feeds_from_anchors(context: Context) -> tuple[Context, Result | None]:
    assert context.soup is not None

    results = []
    links_to_check = set()

    # TODO: can be very-very long, must be improved
    for link in list(context.soup("a")):
        if link.has_attr("href"):
            links_to_check.add(link["href"])

    logger.info("links_to_check", links_to_check=links_to_check)

    context.candidate_urls.extend(links_to_check)

    return context, None


# TODO: test
async def _discover_check_candidate_links(context: Context) -> tuple[Context, Result | None]:
    feeds = []

    for link in context.candidate_urls:
        # TODO: add concurrency
        # TODO: check depth
        feeds.extend(await discover(url=link, depth=context.depth - 1, discoverers=context.discoverers))

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
_discoverers = [_discover_normalize_url,
                _discover_load_url,
                _discover_extract_feed_info,
                _discover_stop_recursion,
                _discover_create_soup,
                _discover_extract_feeds_from_links,
                _discover_check_candidate_links,
                _discover_extract_feeds_from_anchors,
                _discover_check_candidate_links]


# TODO: test
async def discover(url: str, depth: int, discoverers: list[Discoverer] = _discoverers) -> Result:
    context = Context(raw_url=url, depth=depth, discoverers=discoverers)

    for discoverer in discoverers:
        context, result = await discoverer(context)

        if result is not None:
            return result

    return Result(feeds=[], status=Status.no_feeds_found)
