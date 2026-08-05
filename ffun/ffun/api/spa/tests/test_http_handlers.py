import datetime
from decimal import Decimal

import pytest

from ffun.api.spa import entities
from ffun.api.spa.http_handlers import (
    _external_feeds,
    api_get_feeds,
    api_get_feeds_by_ids,
    api_get_resource_statistics,
)
from ffun.core import utils
from ffun.domain.entities import UserId
from ffun.feeds.entities import Feed
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library.entities import CollectedEntry
from ffun.product.entities import Resource
from ffun.resources import domain as r_domain
from ffun.resources import entities as r_entities
from ffun.users.entities import User


async def consume_resource(*, user_id: UserId, kind: Resource, amount: int) -> None:
    reservations = await r_domain.try_to_reserve_in_order(
        amount=amount,
        options=[
            r_entities.ResourceReservationOption(
                kind=kind,
                interval_started_at=datetime.datetime.now(tz=datetime.UTC),
            )
        ],
        specifications=[
            r_entities.ResourceReservationSpecification(
                user_id=user_id,
                limits=(amount,),
            )
        ],
    )

    assert len(reservations) == 1
    await r_domain.convert_reserved_to_used(reservations, used=amount)


class TestApiGetFeeds:
    @pytest.mark.asyncio
    async def test_empty_linked_feeds(self, internal_user_id: UserId) -> None:
        response = await api_get_feeds(entities.GetFeedsRequest(), User(id=internal_user_id))

        assert response.feeds == []

    @pytest.mark.asyncio
    async def test_returns_entries_per_day_without_details(
        self, internal_user_id: UserId, loaded_feed: Feed, new_entry: CollectedEntry
    ) -> None:
        await fl_domain.add_link(internal_user_id, loaded_feed.id)
        await l_domain.catalog_entries(loaded_feed.id, [new_entry])

        response = await api_get_feeds(entities.GetFeedsRequest(), User(id=internal_user_id))

        assert len(response.feeds) == 1
        assert response.feeds[0].id == loaded_feed.id
        assert response.feeds[0].young
        assert response.feeds[0].entriesPerDay == 1
        assert response.feeds[0].entriesLoadedDetails is None


class TestExternalFeeds:

    @pytest.mark.asyncio
    async def test_returns_feed_metrics_details(self, loaded_feed: Feed, new_entry: CollectedEntry) -> None:
        linked_at = utils.now()
        await l_domain.catalog_entries(loaded_feed.id, [new_entry])

        feeds = await _external_feeds(
            linked_at_by_feed={loaded_feed.id: linked_at},
            feeds=[loaded_feed],
            with_details=True,
        )

        assert len(feeds) == 1
        assert feeds[0].id == loaded_feed.id
        assert feeds[0].linkedAt == linked_at
        assert feeds[0].young
        assert feeds[0].entriesPerDay == 1
        assert feeds[0].entriesLoadedDetails is not None
        assert len(feeds[0].entriesLoadedDetails) == 30
        assert feeds[0].entriesLoadedDetails[-1] == 1


class TestApiGetFeedsByIds:
    @pytest.mark.asyncio
    async def test_returns_requested_feeds_with_user_link_details(
        self,
        internal_user_id: UserId,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        new_entry: CollectedEntry,
    ) -> None:
        await fl_domain.add_link(internal_user_id, loaded_feed.id)
        await l_domain.catalog_entries(loaded_feed.id, [new_entry])

        response = await api_get_feeds_by_ids(
            entities.GetFeedsByIdsRequest(ids=[loaded_feed.id, another_loaded_feed.id]),
            User(id=internal_user_id),
        )

        feeds = {feed.id: feed for feed in response.feeds}

        assert set(feeds) == {loaded_feed.id, another_loaded_feed.id}

        assert feeds[loaded_feed.id].linkedAt is not None
        assert feeds[loaded_feed.id].young
        assert feeds[loaded_feed.id].entriesPerDay == 1
        loaded_feed_details = feeds[loaded_feed.id].entriesLoadedDetails
        assert loaded_feed_details is not None
        assert len(loaded_feed_details) == 30
        assert loaded_feed_details[-1] == 1

        assert feeds[another_loaded_feed.id].linkedAt is None
        assert feeds[another_loaded_feed.id].young
        assert feeds[another_loaded_feed.id].entriesPerDay == 0
        assert feeds[another_loaded_feed.id].entriesLoadedDetails == [0] * 30

    @pytest.mark.asyncio
    async def test_empty_ids(self, internal_user_id: UserId) -> None:
        response = await api_get_feeds_by_ids(
            entities.GetFeedsByIdsRequest(ids=[]),
            User(id=internal_user_id),
        )

        assert response.feeds == []


class TestApiGetResourceStatistics:
    @pytest.mark.asyncio
    async def test_empty_kinds(self, internal_user_id: UserId) -> None:
        request = entities.GetResourceStatisticsRequest(
            kinds=[],
            interval=entities.ResourceStatisticsInterval.day,
        )

        response = await api_get_resource_statistics(request, User(id=internal_user_id))

        assert response.interval == entities.ResourceStatisticsInterval.day
        assert response.statistics == {}

    @pytest.mark.asyncio
    async def test_returns_complete_zero_filled_series_for_requested_kinds(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
    ) -> None:
        await consume_resource(user_id=internal_user_id, kind=Resource.day_token_usage, amount=2)
        await consume_resource(user_id=internal_user_id, kind=Resource.day_token_usage, amount=4)
        await consume_resource(user_id=internal_user_id, kind=Resource.lifetime_token_usage, amount=5)
        await consume_resource(user_id=another_internal_user_id, kind=Resource.day_token_usage, amount=99)

        request = entities.GetResourceStatisticsRequest(
            kinds=[
                entities.ResourceKind.tokens_cost,
                entities.ResourceKind.day_token_usage,
                entities.ResourceKind.month_token_usage,
                entities.ResourceKind.lifetime_token_usage,
                entities.ResourceKind.lifetime_token_usage,
            ],
            interval=entities.ResourceStatisticsInterval.day,
        )

        response = await api_get_resource_statistics(request, User(id=internal_user_id))
        current_date = datetime.datetime.now(tz=datetime.UTC).date()

        assert response.interval == entities.ResourceStatisticsInterval.day
        assert set(response.statistics) == set(entities.ResourceKind)
        assert response.statistics[entities.ResourceKind.tokens_cost].firstDate == current_date
        assert response.statistics[entities.ResourceKind.tokens_cost].values == [Decimal(0)]
        assert response.statistics[entities.ResourceKind.day_token_usage].firstDate == current_date
        assert response.statistics[entities.ResourceKind.day_token_usage].values == [Decimal(6)]
        assert response.statistics[entities.ResourceKind.month_token_usage].firstDate == current_date
        assert response.statistics[entities.ResourceKind.month_token_usage].values == [Decimal(0)]
        assert response.statistics[entities.ResourceKind.lifetime_token_usage].firstDate == current_date
        assert response.statistics[entities.ResourceKind.lifetime_token_usage].values == [Decimal(5)]
