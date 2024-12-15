import datetime
import enum
from typing import Any

from ffun.core.entities import BaseEntity
from ffun.domain.entities import FeedId, FeedUrl, SourceId


class FeedState(int, enum.Enum):
    not_loaded = 1
    loaded = 2
    damaged = 3
    orphaned = 4


class FeedError(enum.IntEnum):
    network_unknown = 1000

    # TODO: split to network and protocol errors?
    network_no_address_associated_with_hostname = 1001
    network_name_or_service_not_known = 1002
    network_certificate_verify_failed = 1003
    network_connection_timeout = 1004
    network_read_timeout = 1005
    network_illegal_request_line = 1006
    network_non_200_status_code = 1007
    network_disconection_without_response = 1008
    network_undetected_connection_error = 1009
    network_unsupported_protocol = 1010
    network_server_breaks_connection = 1011
    network_too_many_redirects = 1013
    network_ssl_connection_error = 1014
    network_all_connection_attempts_failed = 1015
    network_received_unkomplete_body = 1016
    network_decoding_error = 1017
    network_read_error = 1018
    network_temporary_failure_in_name_resolution = 1019
    network_wrong_ssl_version = 1020

    parsing_unknown = 2000
    parsing_base_error = 2001
    parsing_format_error = 2002
    parsing_unicode_decode_error = 2003
    parsing_feed_content_not_found = 2004

    protocol_unknown = 3000
    protocol_no_entries_in_feed = 3001

    proxy_could_not_resolve_host = 4001
    proxy_connection_refused = 4002
    proxy_connection_403 = 4003
    proxy_no_route_to_host = 4004
    proxy_connection_502 = 4005


class Feed(BaseEntity):
    id: FeedId
    source_id: SourceId
    url: FeedUrl
    state: FeedState = FeedState.not_loaded
    last_error: FeedError | None = None
    load_attempted_at: datetime.datetime | None = None
    loaded_at: datetime.datetime | None = None

    title: str | None
    description: str | None

    def log_info(self) -> dict[str, Any]:
        return {"id": self.id, "state": self.state, "url": self.url, "last_error": self.last_error}
