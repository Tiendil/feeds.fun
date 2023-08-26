import yarl
from bs4 import BeautifulSoup

from ffun.core import logging
from ffun.loader import domain as lo_domain
from ffun.loader import errors as lo_errors
from ffun.parsers import entities as p_entities

logger = logging.get_module_logger()


def fix_url(raw_url: str) -> str:
    url = yarl.URL(raw_url)

    if url.is_absolute():
        if not url.scheme:
            url = url.with_scheme("http")

    else:
        url = yarl.URL("http://" + raw_url)

    return url.human_repr()


async def extract_content(url: str) -> str | None:
    logger.info("extract_content")

    try:
        response = await lo_domain.load_content_with_proxies(url)
        content = await lo_domain.decode_content(response)
    except lo_errors.LoadError:
        logger.info("can_not_access_content")
        return None
    except Exception:
        logger.exception("unexpected_error_while_parsing_feed")
        return None

    return content


async def extract_feed_info(content: str, original_url: str) -> p_entities.FeedInfo | None:
    logger.info("extract_feed_info")

    try:
        return await lo_domain.parse_content(content, original_url=original_url)
    except lo_errors.LoadError:
        logger.info("feed_not_found_at_start_url")
    except Exception:
        logger.exception("unexpected_error_while_parsing_feed")

    return None


def construct_soup(content: str) -> BeautifulSoup | None:
    logger.info("construct_soup")

    try:
        return BeautifulSoup(content, "html.parser")
    except Exception:
        logger.exception("unexpected_error_while_parsing_html")

    return None


async def extract_feeds_from_links(soup: BeautifulSoup) -> list[p_entities.FeedInfo]:
    results = []
    links_to_check = set()

    for link in soup("link"):
        if link.has_attr("href"):
            links_to_check.add(link["href"])

    logger.info("links_to_check", links_to_check=links_to_check)

    for link in links_to_check:
        results.extend(await discover(url=link, stop=True))

    logger.info("results", result_links=[feed_info.url for feed_info in results])

    return results


async def extract_feeds_from_a(soup: BeautifulSoup) -> list[p_entities.FeedInfo]:
    results = []
    links_to_check = set()

    # TODO: can be very-very long, must be improved
    for link in list(soup("a")):
        if link.has_attr("href"):
            links_to_check.add(link["href"])

    logger.info("links_to_check", links_to_check=links_to_check)

    for link in links_to_check:
        results.extend(await discover(url=link, stop=True))

    logger.info("results", result_links=[feed_info.url for feed_info in results])

    return results


# TODO: this is very straightforward implementation, it should be improved
# TODO: check already saved feeds, but remember, that there may be saved only part of the feeds from url
@logging.bound_function()
async def discover(url: str, stop: bool = False) -> list[p_entities.FeedInfo]:
    url = fix_url(url)

    logger.info("fixed_url", url=url)

    logger.info("start_discover")

    content = await extract_content(url)

    if content is None:
        return []

    feed_info = await extract_feed_info(content, original_url=url)

    if feed_info is not None:
        return [feed_info]

    if stop:
        return []

    logger.info("extract_feeds_candidates")

    soup = construct_soup(content)

    if soup is None:
        return []

    logger.info("search_link_candidates")

    results = await extract_feeds_from_links(soup)

    if results:
        # Here we expect "correct" sites behavior "if there are links to feeds, then they will contain all feeds"
        # it is not always be true, but it is good enough for now
        return results

    results = await extract_feeds_from_links(soup)

    return results


async def check_if_feed(url: str) -> p_entities.FeedInfo | None:
    feeds = await discover(url=url, stop=True)

    if not feeds:
        return None

    return feeds[0]
