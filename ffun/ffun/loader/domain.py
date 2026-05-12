from typing import Mapping

import httpx

from ffun.core import logging
from ffun.dispatcher import domain as d_domain
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import AbsoluteUrl, FeedUrl
from ffun.domain.urls import construct_f_url, url_to_source_uid
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed, FeedId, FeedState
from ffun.feeds_collections.collections import collections
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.loader import errors, operations
from ffun.loader.entities import ProxyState
from ffun.loader.settings import settings
from ffun.parsers import entities as p_entities

logger = logging.get_module_logger()


decode_content = operations.decode_content
parse_content = operations.parse_content


async def load_decoded_content(
    feed_url: FeedUrl,
    headers: dict[str, str] | None = None,
    none_on_error: bool = True,
) -> str | None:
    try:
        response = await load_content_with_proxies(feed_url, headers=headers)
        return await decode_content(response)
    except errors.LoadError as e:
        logger.info("load_decoded_content_error", url=feed_url, error_code=e.feed_error_code)

        if none_on_error:
            return None

        raise
    except Exception:
        logger.exception("unexpected_error_while_loading_decoded_content", url=feed_url)

        if none_on_error:
            return None

        raise


# TODO: tests
async def load_content_with_proxies(  # noqa: CCR001
    url: FeedUrl,
    headers: Mapping[str, object] | None = None,
) -> httpx.Response:
    url_object = construct_f_url(url)

    assert url_object is not None

    first_exception = None

    # TODO: cache states for some time
    proxy_states = await operations.get_proxy_states(names=[proxy.name for proxy in settings.proxies])

    if all(state == ProxyState.suspended for state in proxy_states.values()):
        logger.warning("all_proxies_suspended")
        raise errors.AllProxiesSuspended()

    # We try different protocols because users often make mistakes in the urls
    # to fix them we unite similar urls like http://example.com and https://example.com
    # => we need to check both protocols
    #
    # For now it is straightforward solution, but it should work
    # Most of the domains should support HTTPS => HTTP urls will not be used
    # but in case of full problem with url, we'll be doing unnecessary requests
    # and in case of HTTP-only urls we'll be doing unnecessary requests too
    #
    # ATTENTION: we iterate over protocols even if the user has specified the port, because
    #            1. We do not trust users.
    #            2. We check urls duplicates by removing ports (see domain.urls.url_to_uid
    #
    # TODO: build a separate system of choosing protocol for the url with caching and periodic checks
    for protocol in ("https", "http"):
        logger.info("try_protocol", protocol=protocol)

        url_object.scheme = protocol

        for proxy in settings.proxies:
            logger.info("try_proxy", proxy=proxy.name)

            if proxy_states[proxy.name] == ProxyState.suspended:
                logger.info("skip_suspended_proxy", proxy=proxy.name)
                continue

            try:
                return await operations.load_content(AbsoluteUrl(str(url_object)), proxy, headers=headers)
            except Exception as e:
                logger.info("proxy_error", proxy=proxy.name, error=e)

                if first_exception is None:
                    first_exception = e

        logger.info("all_proxies_failed", protocol=protocol)

    logger.info("all_protocols_failed")

    # in case of error raise the first exception occurred
    # because we should use the most common proxy first
    raise first_exception  # type: ignore


async def detect_orphaned(feed_id: FeedId) -> bool:
    if collections.has_feed(feed_id):
        return False

    if await fl_domain.has_linked_users(feed_id):
        return False

    logger.info("feed_has_no_linked_users")
    await f_domain.mark_feed_as_orphaned(feed_id)

    return True


# TODO: tests
async def extract_feed_info(feed_id: FeedId | None, feed_url: FeedUrl) -> p_entities.FeedInfo | None:
    try:
        content = await load_decoded_content(feed_url, none_on_error=False)
        assert content is not None
        feed_info = await parse_content(content, original_url=feed_url, source=url_to_source_uid(feed_url))
    except errors.AllProxiesSuspended:
        logger.info("all_proxies_suspended")
        return None
    except errors.LoadError as e:
        logger.info("feed_load_error", error_code=e.feed_error_code)

        if feed_id is not None:
            await f_domain.mark_feed_as_failed(feed_id, state=FeedState.damaged, error=e.feed_error_code)

        return None

    logger.info("feed_loaded", entries_number=len(feed_info.entries))

    return feed_info


async def sync_feed_info(feed: Feed, feed_info: p_entities.FeedInfo) -> None:
    title = feed_info.title
    description = feed_info.description

    if collections.has_feed(feed.id):
        collections_feed_info = collections.get_feed_info(feed.id)

        title = collections_feed_info.title
        description = collections_feed_info.description

    if title == feed.title and description == feed.description:
        return

    await f_domain.update_feed_info(feed.id, title=feed_info.title, description=feed_info.description)


async def store_entries(feed: Feed, entries: list[p_entities.EntryInfo]) -> None:
    prepared_entries = [
        entry_info.to_collected_entry(entry_id=new_entry_id(), source_id=feed.source_id) for entry_info in entries
    ]

    new_entries_ids = await l_domain.catalog_entries(feed.id, entries=prepared_entries)
    entries_cataloged = len(new_entries_ids)

    entries_skipped = len(prepared_entries) - entries_cataloged

    logger.info("entries_stored", entries_cataloged=entries_cataloged, entries_skipped=entries_skipped)

    if entries_cataloged > 0:
        await d_domain.push_entries_to_process(new_entries_ids)
        logger.business_event("news_entries_stored", user_id=None, feed_id=feed.id, entries_number=entries_cataloged)


@logging.async_args_to_log("feed.id", "feed.url")
async def process_feed(feed: Feed) -> None:
    logger.info("loading_feed")

    if await detect_orphaned(feed.id):
        return

    feed_info = await extract_feed_info(feed_id=feed.id, feed_url=feed.url)

    if feed_info is not None:
        await sync_feed_info(feed, feed_info)
        await store_entries(feed, feed_info.entries)
        await f_domain.mark_feed_as_loaded(feed.id)
        logger.info("entries_loaded")
    else:
        logger.info("feed_not_loaded")

    # We should sync the list of entries in the feed even if we failed to load it
    # to automatically sync it after any configuration change.
    # We should not do so for orphaned feeds, because they will be removed.
    await l_domain.shrink_feed(feed.id)


async def check_proxies_availability() -> None:
    states = {}

    for proxy in settings.proxies:
        is_available = await operations.is_proxy_available(proxy=proxy, anchors=settings.proxy_anchors)

        states[proxy.name] = ProxyState.available if is_available else ProxyState.suspended

    await operations.update_proxy_states(states)
