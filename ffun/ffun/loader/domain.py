import ssl
import uuid

import httpx
from ffun.core import logging
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed, FeedError, FeedState
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.parsers.domain import parse_feed
from structlog.contextvars import bound_contextvars

from . import errors

logger = logging.get_module_logger()


async def load_content(url: str) -> httpx.Response:
    error_code = FeedError.network_unknown

    try:
        async with httpx.AsyncClient() as client:
            return await client.get(url, follow_redirects=True)
    except httpx.RemoteProtocolError as e:
        message = str(e)

        if 'illegal request line' in message:
            # TODO: at least part of such errors are caused by wrong HTTP protocol
            #       for example `http://gopractice.ru/feed/` tries to redirect to use HTTP/0.9
            logger.warning('network_illegal_request_line')
            error_code = FeedError.network_illegal_request_line
        else:
            logger.exception('remote_protocol_error_while_loading_feed')

        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.ConnectError as e:
        message = str(e)

        if '[Errno -2]' in message:
            logger.warning('network_name_or_service_not_known')
            error_code = FeedError.network_name_or_service_not_known
        elif '[Errno -5]' in message:
            logger.warning('no_address_associated_with_hostname')
            error_code = FeedError.network_no_address_associated_with_hostname
        else:
            logger.exception('connection_error_while_loading_feed')

        raise errors.LoadError(feed_error_code=error_code) from e

    except ssl.SSLCertVerificationError as e:
        message = str(e)

        if 'CERTIFICATE_VERIFY_FAILED' in message:
            logger.warning('network_certificate_verify_failed')
            error_code = FeedError.network_certificate_verify_failed
        else:
            logger.exception('ssl_cert_verification_error_while_loading_feed')

        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.ConnectTimeout as e:
        logger.warning('network_connect_timeout')
        error_code = FeedError.network_connection_timeout
        raise errors.LoadError(feed_error_code=error_code) from e

    except httpx.ReadTimeout as e:
        logger.warning('network_read_timeout')
        error_code = FeedError.network_read_timeout
        raise errors.LoadError(feed_error_code=error_code) from e

    except Exception as e:
        logger.exception('error_while_loading_feed')
        raise errors.LoadError(feed_error_code=error_code) from e


async def decode_content(response: httpx.Response) -> str:

    error_code = FeedError.parsing_base_error

    try:
        return response.content.decode(response.encoding)
    except UnicodeDecodeError as e:
        logger.warning('unicode_decode_error_while_decoding_feed')
        error_code = FeedError.parsing_unicode_decode_error
        raise errors.LoadError(feed_error_code=error_code) from e
    except Exception as e:
        logger.exception('error_while_decoding_feed')
        raise errors.LoadError(feed_error_code=error_code) from e


async def parse_content(feed_id: uuid.UUID, content: str) -> list[l_entities.Entry]:
    try:
        return parse_feed(feed_id, content)
    except Exception as e:
        logger.exception('error_while_parsing_feed')
        raise errors.LoadError(feed_error_code=FeedError.parsing_format_error) from e


async def process_feed(feed: Feed) -> None:

    logger.info("loading_feed", feed=feed)

    with bound_contextvars(feed_url=feed.url,
                           feed_id=feed.id):
        try:
            response = await load_content(feed.url)
            content = await decode_content(response)
            entries = parse_feed(feed.id, content)
        except errors.LoadError as e:
            await f_domain.mark_feed_as_failed(feed.id,
                                               state=FeedState.damaged,
                                               error=e.feed_error_code)
            return

    external_ids = [entry.external_id for entry in entries]

    stored_entries_external_ids  = await l_domain.check_stored_entries_by_external_ids(external_ids)

    entries_to_store = [entry for entry in entries
                        if entry.external_id not in stored_entries_external_ids]

    await l_domain.catalog_entries(entries=entries_to_store)

    await f_domain.mark_feed_as_loaded(feed.id)

    logger.info("entries_loaded", loaded_number=len(entries), stored_number=len(entries_to_store))
