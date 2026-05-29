import pydantic
import pytest

from ffun.api.spa.entities import Feed, Marker, MutableMarker, RemoveMarkerRequest, SetMarkerRequest
from ffun.core import utils
from ffun.domain.domain import new_entry_id
from ffun.domain.urls import str_to_absolute_url
from ffun.feeds.entities import Feed as InternalFeed
from ffun.feeds.entities import FeedError


class TestFeed:
    def test_from_internal__default_entries_metrics_details(self, loaded_feed: InternalFeed) -> None:
        external_feed = Feed.from_internal(
            loaded_feed,
            linked_at=None,
            collection_ids=[],
            entries_loaded=0,
        )

        assert external_feed.entriesLoadedDetails is None
        assert external_feed.siteUrl is None

    @pytest.mark.asyncio
    async def test_from_internal__with_entries_metrics(self, loaded_feed: InternalFeed) -> None:
        linked_at = utils.now()
        site_url = str_to_absolute_url("https://example.com")

        external_feed = Feed.from_internal(
            loaded_feed.replace(site_url=site_url),
            linked_at=linked_at,
            collection_ids=[],
            entries_loaded=3,
            entries_loaded_details=[0, 1, 2],
        )

        assert external_feed.linkedAt == linked_at
        assert external_feed.siteUrl == site_url
        assert external_feed.entriesLoaded == 3
        assert external_feed.entriesLoadedDetails == [0, 1, 2]

    def test_from_internal__with_last_error(self, loaded_feed: InternalFeed) -> None:
        error = FeedError.network_connection_timeout
        failed_feed = loaded_feed.replace(last_error=error)

        external_feed = Feed.from_internal(
            failed_feed,
            linked_at=None,
            collection_ids=[],
            entries_loaded=0,
        )

        assert external_feed.lastError == error.name


class TestSetMarkerRequest:
    def test_accepts_mutable_marker(self) -> None:
        request = SetMarkerRequest(entryId=new_entry_id(), marker=MutableMarker.read)

        assert request.marker.to_internal().value == Marker.read

    def test_rejects_return_only_marker(self) -> None:
        payload: dict[str, object] = {"entryId": new_entry_id(), "marker": Marker.can_see_tags}

        with pytest.raises(pydantic.ValidationError):
            SetMarkerRequest.model_validate(payload)


class TestRemoveMarkerRequest:
    def test_accepts_mutable_marker(self) -> None:
        request = RemoveMarkerRequest(entryId=new_entry_id(), marker=MutableMarker.read)

        assert request.marker.to_internal().value == Marker.read

    def test_rejects_return_only_marker(self) -> None:
        payload: dict[str, object] = {"entryId": new_entry_id(), "marker": Marker.can_see_tags}

        with pytest.raises(pydantic.ValidationError):
            RemoveMarkerRequest.model_validate(payload)
