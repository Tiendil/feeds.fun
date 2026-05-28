import pytest

from ffun.api.spa import entities
from ffun.api.spa.http_handlers import _external_feeds, api_get_feeds, api_get_feeds_by_ids
from ffun.core import utils
from ffun.domain.entities import UserId
from ffun.feeds.entities import Feed
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library.entities import CollectedEntry
from ffun.users.entities import User


class TestApiGetFeeds:
    @pytest.mark.asyncio
    async def test_empty_linked_feeds(self, internal_user_id: UserId) -> None:
        response = await api_get_feeds(entities.GetFeedsRequest(), User(id=internal_user_id))

        assert response.feeds == []

    @pytest.mark.asyncio
    async def test_returns_entries_loaded_without_details(
        self, internal_user_id: UserId, loaded_feed: Feed, new_entry: CollectedEntry
    ) -> None:
        await fl_domain.add_link(internal_user_id, loaded_feed.id)
        await l_domain.catalog_entries(loaded_feed.id, [new_entry])

        response = await api_get_feeds(entities.GetFeedsRequest(), User(id=internal_user_id))

        assert len(response.feeds) == 1
        assert response.feeds[0].id == loaded_feed.id
        assert response.feeds[0].entriesLoaded == 1
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
        assert feeds[0].entriesLoaded == 1
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
        assert feeds[loaded_feed.id].entriesLoaded == 1
        loaded_feed_details = feeds[loaded_feed.id].entriesLoadedDetails
        assert loaded_feed_details is not None
        assert len(loaded_feed_details) == 30
        assert loaded_feed_details[-1] == 1

        assert feeds[another_loaded_feed.id].linkedAt is None
        assert feeds[another_loaded_feed.id].entriesLoaded == 0
        assert feeds[another_loaded_feed.id].entriesLoadedDetails == [0] * 30

    @pytest.mark.asyncio
    async def test_empty_ids(self, internal_user_id: UserId) -> None:
        response = await api_get_feeds_by_ids(
            entities.GetFeedsByIdsRequest(ids=[]),
            User(id=internal_user_id),
        )

        assert response.feeds == []
