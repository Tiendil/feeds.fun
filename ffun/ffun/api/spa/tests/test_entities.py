from decimal import Decimal

import pydantic
import pytest

from ffun.api.spa.entities import (
    Feed,
    FeedInfo,
    Marker,
    MutableMarker,
    RemoveMarkerRequest,
    ResourceKind,
    ResourceStatisticsInterval,
    ResourceStatisticsSeries,
    SetMarkerRequest,
)
from ffun.core import utils
from ffun.domain.domain import new_entry_id
from ffun.domain.urls import str_to_absolute_url, str_to_feed_url, url_to_uid
from ffun.feeds.entities import Feed as InternalFeed
from ffun.feeds.entities import FeedError
from ffun.parsers import entities as p_entities
from ffun.product.entities import Resource
from ffun.resources import entities as r_entities


class TestFeed:
    def test_from_internal__default_entries_metrics_details(self, loaded_feed: InternalFeed) -> None:
        external_feed = Feed.from_internal(
            loaded_feed,
            linked_at=None,
            collection_ids=[],
            young=True,
            entries_per_day=0,
        )

        assert external_feed.young
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
            young=False,
            entries_per_day=3,
            entries_loaded_details=[0, 1, 2],
        )

        assert external_feed.linkedAt == linked_at
        assert external_feed.siteUrl == site_url
        assert not external_feed.young
        assert external_feed.entriesPerDay == 3
        assert external_feed.entriesLoadedDetails == [0, 1, 2]

    def test_from_internal__with_last_error(self, loaded_feed: InternalFeed) -> None:
        error = FeedError.network_connection_timeout
        failed_feed = loaded_feed.replace(last_error=error)

        external_feed = Feed.from_internal(
            failed_feed,
            linked_at=None,
            collection_ids=[],
            young=True,
            entries_per_day=0,
        )

        assert external_feed.lastError == error.name


class TestFeedInfo:
    def test_from_internal__keeps_site_url(self) -> None:
        feed_url = str_to_feed_url("https://example.com/feed")
        site_url = str_to_absolute_url("https://example.com")

        external_feed = FeedInfo.from_internal(
            p_entities.FeedInfo(
                url=feed_url,
                site_url=site_url,
                title="Example",
                description="Example feed",
                uid=url_to_uid(feed_url),
                entries=[],
            ),
            is_linked=True,
        )

        assert external_feed.siteUrl == site_url
        assert external_feed.isLinked

    def test_from_internal__keeps_missing_site_url(self) -> None:
        feed_url = str_to_feed_url("https://example.com/feed")

        external_feed = FeedInfo.from_internal(
            p_entities.FeedInfo(
                url=feed_url,
                site_url=None,
                title="Example",
                description="Example feed",
                uid=url_to_uid(feed_url),
                entries=[],
            ),
            is_linked=False,
        )

        assert external_feed.siteUrl is None


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


class TestResourceKind:
    @pytest.mark.parametrize(
        "kind, internal_kind",
        [
            (ResourceKind.tokens_cost, Resource.tokens_cost),
            (ResourceKind.day_token_usage, Resource.day_token_usage),
            (ResourceKind.month_token_usage, Resource.month_token_usage),
            (ResourceKind.lifetime_token_usage, Resource.lifetime_token_usage),
        ],
    )
    def test_to_internal__resource_kind(self, kind: ResourceKind, internal_kind: Resource) -> None:
        assert kind.to_internal() == r_entities.ResourceKind(internal_kind)

    @pytest.mark.parametrize(
        "kind, internal_kind",
        [
            (ResourceKind.tokens_cost, Resource.tokens_cost),
            (ResourceKind.day_token_usage, Resource.day_token_usage),
            (ResourceKind.month_token_usage, Resource.month_token_usage),
            (ResourceKind.lifetime_token_usage, Resource.lifetime_token_usage),
        ],
    )
    def test_from_internal__resource_kind(self, kind: ResourceKind, internal_kind: Resource) -> None:
        assert ResourceKind.from_internal(internal_kind) == kind

    def test_amount_from_internal__token_usage(self) -> None:
        assert ResourceKind.lifetime_token_usage.amount_from_internal(13) == Decimal(13)

    def test_amount_from_internal__tokens_cost(self) -> None:
        assert ResourceKind.tokens_cost.amount_from_internal(1_500_000_000) == Decimal("1.5")


class TestResourceStatisticsInterval:
    @pytest.mark.parametrize(
        "interval",
        [
            ResourceStatisticsInterval.day,
            ResourceStatisticsInterval.month,
            ResourceStatisticsInterval.year,
        ],
    )
    def test_to_internal__interval(self, interval: ResourceStatisticsInterval) -> None:
        assert interval.to_internal() == r_entities.ResourceStatisticsInterval(interval.value)


class TestResourceStatisticsSeries:
    def test_from_internal__empty_values(self) -> None:
        first_date = utils.now().date()
        series = ResourceStatisticsSeries.from_internal(
            kind=ResourceKind.lifetime_token_usage,
            series=r_entities.ResourceStatisticsSeries(first_date=first_date, values=()),
        )

        assert series.firstDate == first_date
        assert series.values == []

    def test_from_internal__zero(self) -> None:
        first_date = utils.now().date()
        series = ResourceStatisticsSeries.from_internal(
            kind=ResourceKind.lifetime_token_usage,
            series=r_entities.ResourceStatisticsSeries(first_date=first_date, values=(0,)),
        )

        assert series.firstDate == first_date
        assert series.values == [Decimal(0)]

    def test_from_internal__converts_values(self) -> None:
        kind = ResourceKind.lifetime_token_usage
        first_date = utils.now().date()

        series = ResourceStatisticsSeries.from_internal(
            kind=kind,
            series=r_entities.ResourceStatisticsSeries(
                first_date=first_date,
                values=(2, 0, 4),
            ),
        )

        assert series.firstDate == first_date
        assert series.values == [Decimal(2), Decimal(0), Decimal(4)]
