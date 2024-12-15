import asyncio
import ssl

import anyio
import httpx
from pypika import PostgreSQLQuery
from pypika import functions as pypika_fn

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.domain.entities import AbsoluteUrl, FeedUrl
from ffun.feeds.entities import FeedError
from ffun.loader import errors
from ffun.loader.entities import ProxyState
from ffun.loader.settings import Proxy, settings
from ffun.parsers import entities as p_entities
from ffun.parsers.domain import parse_feed

logger = logging.get_module_logger()


_load_semaphor = asyncio.Semaphore(settings.max_concurrent_http_requests)


async def load_content(  # noqa: CFQ001, CCR001, C901 # pylint: disable=R0912, R0915
    url: AbsoluteUrl, proxy: Proxy, user_agent: str, semaphore: asyncio.Semaphore = _load_semaphor
) -> httpx.Response:
    error_code = FeedError.network_unknown

    log = logger.bind(url=url, proxy=proxy.name, function="load_content")

    try:
        log.info("loading_feed")

        headers = {"user-agent": user_agent, "accept-encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8"}

        async with semaphore:
            async with httpx.AsyncClient(proxies=proxy.url, headers=headers) as client:
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
        elif "[SSL:" in message:
            # catch all SSL errors
            log.warning("network_ssl_connection_error")
            error_code = FeedError.network_ssl_connection_error
        else:
            log.exception("connection_error_while_loading_feed")

        raise errors.LoadError(feed_error_code=error_code) from e

    except ssl.SSLError as e:
        # TODO: it is possible, that httpx started to wrap ssl errors into httpx.ConnectError
        #       for example, see CERTIFICATE_VERIFY_FAILED.
        #       If it is true, we may remove this block
        log.warning("network_certificate_verify_failed")
        error_code = FeedError.network_ssl_connection_error
        raise errors.LoadError(feed_error_code=error_code) from e

    except ssl.SSLCertVerificationError as e:
        message = str(e)

        # TODO: it is possible, that httpx started to wrap ssl errors into httpx.ConnectError
        #       for example, see CERTIFICATE_VERIFY_FAILED.
        #       If it is true, we may remove this block
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
        elif "502" in message:
            log.warning("proxy_connection_502")
            error_code = FeedError.proxy_connection_502
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
async def parse_content(content: str, original_url: FeedUrl) -> p_entities.FeedInfo:
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


async def check_proxy(proxy: Proxy, url: str, user_agent: str) -> bool:
    try:
        async with httpx.AsyncClient(proxies=proxy.url, headers={"user-agent": user_agent}) as client:
            response = await client.head(url)
    except Exception as e:
        logger.info("proxy_check_error", proxy=proxy.name, url=url, error=str(e))
        return False

    logger.info("proxy_check", proxy=proxy.name, url=url, status_code=response.status_code)

    return response.status_code == 200


async def is_proxy_available(proxy: Proxy, anchors: list[str], user_agent: str) -> bool:
    tasks = [check_proxy(proxy, url, user_agent) for url in anchors]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return any(result for result in results)


async def get_proxy_states(names: list[str]) -> dict[str, ProxyState]:
    sql = """
    SELECT name, state
    FROM lr_proxy_states
    WHERE name = ANY(%(names)s)
    """

    rows = await execute(sql, {"names": names})

    states = {name: ProxyState.available for name in names}

    for row in rows:
        states[row["name"]] = ProxyState(row["state"])

    return states


async def update_proxy_states(states: dict[str, ProxyState]) -> None:
    if not states:
        return

    query = PostgreSQLQuery.into("lr_proxy_states").columns("name", "state", "updated_at")

    for name, state in states.items():
        query = query.insert(name, state, pypika_fn.Now())

    query = query.on_conflict("name").do_update("state").do_update("updated_at", pypika_fn.Now())

    await execute(str(query))
