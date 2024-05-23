import uuid

import httpx
from furl import furl

from ffun.core import logging, utils
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed, FeedState
from ffun.feeds_collections import domain as fc_domain
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.loader import errors, operations
from ffun.loader.entities import ProxyState
from ffun.loader.settings import settings
from ffun.meta import domain as meta_domain
from ffun.parsers import entities as p_entities

logger = logging.get_module_logger()


_user_agent: str = "unknown"


decode_content = operations.decode_content
parse_content = operations.parse_content


# TODO: tests
def initialize(user_agent: str) -> None:
    global _user_agent

    _user_agent = user_agent


# TODO: tests
async def load_content_with_proxies(url: str) -> httpx.Response:  # noqa: CCR001
    url_object = furl(url)

    first_exception = None

    # TODO: cache states for some time
    proxy_states = await operations.get_proxy_states(names=[proxy.name for proxy in settings.proxies])

    if all(state == ProxyState.suspended for state in proxy_states.values()):
        logger.warning("all_proxies_suspended")
        raise errors.AllProxiesSuspended()

    # We try different protocols because users often make mistakes in the urls
    # to fix them we unity similar urls like http://example.com and https://example.com
    # => we need to check both protocols
    #
    # For now it is straightforward solution, but it should work
    # Most of the domains should support HTTPS => HTTP urls will not be used
    # but in case of full problem with url, we'll be doing unnecessary requests
    # and in case of HTTP-only urls we'll be doing unnecessary requests too
    #
    # TODO: build a separate system of choosing protocol for the url with caching and periodic checks
    for protocol in ("https", "http"):
        url_object.scheme = protocol

        for proxy in settings.proxies:
            if proxy_states[proxy.name] == ProxyState.suspended:
                logger.info("skip_suspended_proxy", proxy=proxy.name)
                continue

            try:
                return await operations.load_content(str(url_object), proxy, _user_agent)
            except Exception as e:
                if first_exception is None:
                    first_exception = e

    # in case of error raise the first exception occurred
    # because we should use the most common proxy first
    raise first_exception  # type: ignore


async def detect_orphaned(feed_id: uuid.UUID) -> bool:
    if await fc_domain.is_feed_in_collections(feed_id):
        return False

    if await fl_domain.has_linked_users(feed_id):
        return False

    logger.info("feed_has_no_linked_users")
    await f_domain.mark_feed_as_orphaned(feed_id)

    return True


# TODO: tests
async def extract_feed_info(feed: Feed) -> p_entities.FeedInfo | None:
    try:
        response = await load_content_with_proxies(feed.url)
        content = await operations.decode_content(response)
        feed_info = await operations.parse_content(content, original_url=feed.url)
    except errors.AllProxiesSuspended:
        logger.info("all_proxies_suspended")
        return None
    except errors.LoadError as e:
        logger.info("feed_load_error", error_code=e.feed_error_code)
        await f_domain.mark_feed_as_failed(feed.id, state=FeedState.damaged, error=e.feed_error_code)
        return None

    logger.info("feed_loaded", entries_number=len(feed_info.entries))

    return feed_info


async def sync_feed_info(feed: Feed, feed_info: p_entities.FeedInfo) -> None:
    if feed_info.title == feed.title and feed_info.description == feed.description:
        return

    await f_domain.update_feed_info(feed.id, title=feed_info.title, description=feed_info.description)


async def store_entries(feed_id: uuid.UUID, entries: list[p_entities.EntryInfo]) -> None:
    external_ids = [entry.external_id for entry in entries]

    stored_entries_external_ids = await l_domain.check_stored_entries_by_external_ids(feed_id, external_ids)

    entries_to_store = [entry for entry in entries if entry.external_id not in stored_entries_external_ids]

    prepared_entries = [
        l_entities.Entry(feed_id=feed_id, id=uuid.uuid4(), cataloged_at=utils.now(), **entry_info.model_dump())
        for entry_info in entries_to_store
    ]

    await l_domain.catalog_entries(entries=prepared_entries)

    logger.info("entries_stored", entries_number=len(prepared_entries))


@logging.bound_function()
async def process_feed(feed: Feed) -> None:
    logger.info("loading_feed")

    if await detect_orphaned(feed.id):
        return

    feed_info = await extract_feed_info(feed)

    if feed_info is None:
        return

    await sync_feed_info(feed, feed_info)

    await store_entries(feed.id, feed_info.entries)

    await meta_domain.limit_entries_for_feed(feed.id)

    await f_domain.mark_feed_as_loaded(feed.id)

    logger.info("entries_loaded")


async def check_proxies_availability() -> None:
    states = {}

    for proxy in settings.proxies:
        is_available = await operations.is_proxy_available(
            proxy=proxy, anchors=settings.proxy_anchors, user_agent=_user_agent
        )

        states[proxy.name] = ProxyState.available if is_available else ProxyState.suspended

    await operations.update_proxy_states(states)
