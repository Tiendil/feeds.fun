import ssl
import uuid

import anyio
import httpx
from furl import furl

from ffun.core import logging, utils
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed, FeedError, FeedState
from ffun.feeds_collections import domain as fc_domain
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.loader import errors
from ffun.loader.settings import Proxy, settings
from ffun.meta import domain as meta_domain
from ffun.parsers import entities as p_entities
from ffun.parsers.domain import parse_feed

logger = logging.get_module_logger()


_user_agent: str = "unknown"


# TODO: tests
def initialize(user_agent: str) -> None:
    global _user_agent

    _user_agent = user_agent


# TODO: tests
async def load_content(  # noqa: CFQ001, CCR001, C901 # pylint: disable=R0912, R0915
    url: str, proxy: Proxy
) -> httpx.Response:
    error_code = FeedError.network_unknown

    log = logger.bind(url=url, proxy=proxy.name, function="load_content")

    try:
        log.info("loading_feed")

        async with httpx.AsyncClient(proxies=proxy.url, headers={"user-agent": _user_agent}) as client:
            response = await client.get(url, follow_redirects=True)

    except httpx.RemoteProtocolError as e:
        message = str(e)

        if "illegal request line" in message:
            # TODO: at least part of such errors are caused by wrong HTTP protocol
            #       for example `http://gopractice.ru/feed/` tries to redirect to use HTTP/0.9
            log.warning("network_illegal_request_line")
            error_code = FeedError.network_illegal_request_line
        elif "Server disconnected without sending a response" in message:
            log.warning("network_disconection_without_response")
            error_code = FeedError.network_disconection_without_response
        elif "peer closed connection without sending complete message body (incomplete chunked read)" in message:
            log.warning("network_received_unkomplete_body")
            error_code = FeedError.network_received_unkomplete_body
        else:
            log.exception("remote_protocol_error_while_loading_feed")

        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.ReadError as e:
        message = str(e)

        if message == "":
            error_code = FeedError.network_read_error
            log.warning("network_read_error")
        else:
            log.exception("unknown_read_error_while_loading_feed")

        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.ConnectError as e:
        message = str(e)

        if "[Errno -2]" in message:
            log.warning("network_name_or_service_not_known")
            error_code = FeedError.network_name_or_service_not_known
        elif "[Errno -3]" in message:
            log.warning("network_temporary_failure_in_name_resolution")
            error_code = FeedError.network_temporary_failure_in_name_resolution
        elif "[Errno -5]" in message:
            log.warning("no_address_associated_with_hostname")
            error_code = FeedError.network_no_address_associated_with_hostname
        elif message == "":
            log.warning("undetected_connection_error")
            error_code = FeedError.network_undetected_connection_error
        elif message == "All connection attempts failed":
            log.warning("network_all_connection_attempts_failed")
            error_code = FeedError.network_all_connection_attempts_failed
        else:
            log.exception("connection_error_while_loading_feed")

        raise errors.LoadError(feed_error_code=error_code) from e

    except ssl.SSLError as e:
        log.warning("network_certificate_verify_failed")
        error_code = FeedError.network_ssl_connection_error
        raise errors.LoadError(feed_error_code=error_code) from e

    except ssl.SSLCertVerificationError as e:
        message = str(e)

        if "CERTIFICATE_VERIFY_FAILED" in message:
            log.warning("network_certificate_verify_failed")
            error_code = FeedError.network_certificate_verify_failed
        else:
            log.exception("ssl_cert_verification_error_while_loading_feed")

        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.ConnectTimeout as e:
        log.warning("network_connect_timeout")
        error_code = FeedError.network_connection_timeout
        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.ReadTimeout as e:
        log.warning("network_read_timeout")
        error_code = FeedError.network_read_timeout
        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.UnsupportedProtocol as e:
        log.warning("network_unsupported_protocol")
        error_code = FeedError.network_unsupported_protocol
        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.TooManyRedirects as e:
        log.warning("network_too_many_redirects")
        error_code = FeedError.network_too_many_redirects
        raise errors.LoadError(feed_error_code=error_code) from e

    except anyio.EndOfStream as e:
        log.warning("server_breaks_connection")
        error_code = FeedError.network_server_breaks_connection
        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.ProxyError as e:
        message = str(e)

        if message.startswith("502 Could not resolve host"):
            log.warning("proxy_could_not_resolve_host")
            error_code = FeedError.proxy_could_not_resolve_host
        elif "TUN_ERR" in message and "ECONNREFUSED" in message:
            log.warning("proxy_connection_refused")
            error_code = FeedError.proxy_connection_refused
        elif "TUN_ERR" in message and "EHOSTUNREACH" in message:
            log.warning("proxy_no_route_to_host")
            error_code = FeedError.proxy_no_route_to_host
        elif "403" in message:
            log.warning("proxy_connection_403")
            error_code = FeedError.proxy_connection_403
        else:
            log.exception("unknown_proxy_error_while_loading_feed")

        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.DecodingError as e:
        log.warning("network_decoding_error")
        error_code = FeedError.network_decoding_error
        raise errors.LoadError(feed_error_code=error_code) from e

    except Exception as e:
        log.exception("error_while_loading_feed")
        raise errors.LoadError(feed_error_code=error_code) from e

    if response.status_code != 200:
        log.warning("network_non_200_status_code", status_code=response.status_code)
        error_code = FeedError.network_non_200_status_code
        raise errors.LoadError(feed_error_code=error_code)

    log.info("feed_loaded", url=url, proxy=proxy.name)

    return response


# TODO: tests
async def decode_content(response: httpx.Response) -> str:
    error_code = FeedError.parsing_base_error

    encoding = response.encoding or "utf-8"

    try:
        return response.content.decode(encoding)
    except UnicodeDecodeError as e:
        logger.warning("unicode_decode_error_while_decoding_feed")
        error_code = FeedError.parsing_unicode_decode_error
        raise errors.LoadError(feed_error_code=error_code) from e
    except Exception as e:
        logger.exception("error_while_decoding_feed")
        raise errors.LoadError(feed_error_code=error_code) from e


# TODO: tests
async def parse_content(content: str, original_url: str) -> p_entities.FeedInfo:
    try:
        feed_info = parse_feed(content, original_url=original_url)
    except Exception as e:
        logger.exception("error_while_parsing_feed")
        raise errors.LoadError(feed_error_code=FeedError.parsing_format_error) from e

    if feed_info is None:
        raise errors.LoadError(feed_error_code=FeedError.parsing_feed_content_not_found)

    if not feed_info.entries:
        raise errors.LoadError(feed_error_code=FeedError.protocol_no_entries_in_feed)

    return feed_info


# TODO: tests
async def load_content_with_proxies(url: str) -> httpx.Response:  # noqa: CCR001
    url_object = furl(url)

    first_exception = None

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
            try:
                return await load_content(str(url_object), proxy)
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
        content = await decode_content(response)
        feed_info = await parse_content(content, original_url=feed.url)
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
