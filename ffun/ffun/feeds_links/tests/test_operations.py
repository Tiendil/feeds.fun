import pytest

from ffun.core.postgresql import transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_logs_has_business_event, capture_logs
from ffun.domain.entities import UserId
from ffun.feeds.entities import FeedId
from ffun.feeds.tests import make as f_make
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.feeds_links.entities import FeedLink
from ffun.feeds_links.operations import (
    add_link,
    count_feeds_per_user,
    count_subset_feeds_per_user,
    get_link,
    get_linked_feeds,
    get_linked_users,
    has_linked_users,
    remove_link,
    tech_merge_feeds,
)
from ffun.users.tests import make as u_make


class TestAddLink:

    @pytest.mark.parametrize("in_collection", [True, False])
    @pytest.mark.asyncio
    async def test_add_link(
        self,
        internal_user_id: UserId,
        saved_feed_id: FeedId,
        in_collection: bool,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        if in_collection:
            await collections.add_test_feed_to_collections(collection_id_for_test_feeds, saved_feed_id)

        with capture_logs() as logs:
            async with TableSizeDelta("fl_links", delta=1):
                await add_link(internal_user_id, saved_feed_id)

        assert_logs_has_business_event(
            logs, "feed_linked", user_id=internal_user_id, feed_id=str(saved_feed_id), in_collection=in_collection
        )

        links = await get_linked_feeds(internal_user_id)

        assert links == [FeedLink(user_id=internal_user_id, feed_id=saved_feed_id, created_at=links[0].created_at)]

    @pytest.mark.asyncio
    async def test_duplicated(self, internal_user_id: UserId, saved_feed_id: FeedId) -> None:
        await add_link(internal_user_id, saved_feed_id)

        async with TableSizeNotChanged("fl_links"):
            await add_link(internal_user_id, saved_feed_id)

        links = await get_linked_feeds(internal_user_id)

        assert links == [FeedLink(user_id=internal_user_id, feed_id=saved_feed_id, created_at=links[0].created_at)]

    @pytest.mark.asyncio
    async def test_multiple_links(
        self, five_internal_user_ids: list[UserId], five_saved_feed_ids: list[FeedId]
    ) -> None:
        user_1_id, user_2_id, user_3_id = five_internal_user_ids[:3]

        f = five_saved_feed_ids

        async with TableSizeDelta("fl_links", delta=6):
            await add_link(user_1_id, f[0])
            await add_link(user_1_id, f[1])

            await add_link(user_2_id, f[1])
            await add_link(user_2_id, f[2])
            await add_link(user_2_id, f[3])

            await add_link(user_3_id, f[3])

        links_1 = await get_linked_feeds(user_1_id)

        assert links_1 == [
            FeedLink(user_id=user_1_id, feed_id=f[0], created_at=links_1[0].created_at),
            FeedLink(user_id=user_1_id, feed_id=f[1], created_at=links_1[1].created_at),
        ]

        links_2 = await get_linked_feeds(user_2_id)

        assert links_2 == [
            FeedLink(user_id=user_2_id, feed_id=f[1], created_at=links_2[0].created_at),
            FeedLink(user_id=user_2_id, feed_id=f[2], created_at=links_2[1].created_at),
            FeedLink(user_id=user_2_id, feed_id=f[3], created_at=links_2[2].created_at),
        ]

        links_3 = await get_linked_feeds(user_3_id)

        assert links_3 == [FeedLink(user_id=user_3_id, feed_id=f[3], created_at=links_3[0].created_at)]


class TestRemoveLink:

    @pytest.mark.parametrize("in_collection", [True, False])
    @pytest.mark.asyncio
    async def test_remove_link(
        self,
        internal_user_id: UserId,
        saved_feed_id: FeedId,
        in_collection: bool,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        if in_collection:
            await collections.add_test_feed_to_collections(collection_id_for_test_feeds, saved_feed_id)

        await add_link(internal_user_id, saved_feed_id)

        with capture_logs() as logs:
            async with TableSizeDelta("fl_links", delta=-1):
                await remove_link(internal_user_id, saved_feed_id)

        assert_logs_has_business_event(
            logs, "feed_unlinked", user_id=internal_user_id, feed_id=str(saved_feed_id), in_collection=in_collection
        )

        links = await get_linked_feeds(internal_user_id)

        assert links == []

    @pytest.mark.asyncio
    async def test_create_after_remove(self, internal_user_id: UserId, saved_feed_id: FeedId) -> None:
        await add_link(internal_user_id, saved_feed_id)
        await remove_link(internal_user_id, saved_feed_id)

        async with TableSizeDelta("fl_links", delta=1):
            await add_link(internal_user_id, saved_feed_id)

        links = await get_linked_feeds(internal_user_id)

        assert links == [FeedLink(user_id=internal_user_id, feed_id=saved_feed_id, created_at=links[0].created_at)]

    @pytest.mark.asyncio
    async def test_remove_only_required(
        self, five_internal_user_ids: list[UserId], five_saved_feed_ids: list[FeedId]
    ) -> None:
        user_1_id, user_2_id, user_3_id = five_internal_user_ids[:3]

        f = five_saved_feed_ids

        await add_link(user_1_id, f[0])
        await add_link(user_1_id, f[1])

        await add_link(user_2_id, f[1])
        await add_link(user_2_id, f[2])
        await add_link(user_2_id, f[3])

        await add_link(user_3_id, f[3])

        async with TableSizeDelta("fl_links", delta=-1):
            await remove_link(user_2_id, f[2])

        links_1 = await get_linked_feeds(user_1_id)
        assert len(links_1) == 2

        links_2 = await get_linked_feeds(user_2_id)

        assert links_2 == [
            FeedLink(user_id=user_2_id, feed_id=f[1], created_at=links_2[0].created_at),
            FeedLink(user_id=user_2_id, feed_id=f[3], created_at=links_2[1].created_at),
        ]

        links_3 = await get_linked_feeds(user_3_id)

        assert len(links_3) == 1


class TestGetLinkedFeeds:
    """This functions is validated by other tests."""

    @pytest.mark.asyncio
    async def test_empty(self, internal_user_id: UserId) -> None:
        links = await get_linked_feeds(internal_user_id)

        assert links == []


class TestGetLink:

    @pytest.mark.asyncio
    async def test_no_link(self, internal_user_id: UserId, saved_feed_id: FeedId) -> None:
        link = await get_link(internal_user_id, saved_feed_id)

        assert link is None

    @pytest.mark.asyncio
    async def test_has_link(self, internal_user_id: UserId, saved_feed_id: FeedId) -> None:
        await add_link(internal_user_id, saved_feed_id)

        link = await get_link(internal_user_id, saved_feed_id)

        assert link is not None

        assert link == FeedLink(user_id=internal_user_id, feed_id=saved_feed_id, created_at=link.created_at)


class TestGetLinkedUsers:

    @pytest.mark.asyncio
    async def test_empty(self, saved_feed_id: FeedId) -> None:
        users = await get_linked_users([saved_feed_id])

        assert users == {}

    @pytest.mark.asyncio
    async def test_returns_only_required(
        self, five_internal_user_ids: list[UserId], saved_feed_id: FeedId, another_saved_feed_id: FeedId
    ) -> None:
        user_1_id, user_2_id, user_3_id = five_internal_user_ids[:3]

        await add_link(user_1_id, saved_feed_id)

        await add_link(user_2_id, saved_feed_id)
        await add_link(user_2_id, another_saved_feed_id)

        await add_link(user_3_id, another_saved_feed_id)

        users = await get_linked_users([saved_feed_id])

        assert users == {saved_feed_id: {user_1_id, user_2_id}}

        users = await get_linked_users([another_saved_feed_id])

        assert users == {another_saved_feed_id: {user_2_id, user_3_id}}

        users = await get_linked_users([saved_feed_id, another_saved_feed_id])

        assert users == {saved_feed_id: {user_1_id, user_2_id}, another_saved_feed_id: {user_2_id, user_3_id}}


class TestHasLinkedUsers:

    @pytest.mark.asyncio
    async def test_no_users(self, saved_feed_id: FeedId) -> None:
        assert not await has_linked_users(saved_feed_id)

    @pytest.mark.asyncio
    async def test_has_users(self, internal_user_id: UserId, saved_feed_id: FeedId) -> None:
        await add_link(internal_user_id, saved_feed_id)

        assert await has_linked_users(saved_feed_id)


class TestCountFeedsPerUser:

    @pytest.mark.asyncio
    async def test(self, five_internal_user_ids: list[UserId], five_saved_feed_ids: list[FeedId]) -> None:
        u = five_internal_user_ids
        f = five_saved_feed_ids

        await add_link(u[0], f[0])
        await add_link(u[0], f[1])
        await add_link(u[0], f[2])
        await add_link(u[1], f[2])
        await add_link(u[1], f[3])
        await add_link(u[2], f[3])

        numbers_after = await count_feeds_per_user()

        assert numbers_after[u[0]] == 3
        assert numbers_after[u[1]] == 2
        assert numbers_after[u[2]] == 1
        assert u[3] not in numbers_after
        assert u[4] not in numbers_after


class TestCountSubsetFeedsPerUser:

    @pytest.mark.asyncio
    async def test(
        self,
        five_internal_user_ids: list[UserId],
        five_saved_feed_ids: list[FeedId],
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        u = five_internal_user_ids
        f = five_saved_feed_ids

        await add_link(u[0], f[0])
        await add_link(u[0], f[1])
        await add_link(u[0], f[2])
        await add_link(u[1], f[2])
        await add_link(u[1], f[3])
        await add_link(u[2], f[3])

        numbers_after = await count_subset_feeds_per_user([f[0], f[2]])

        assert numbers_after[u[0]] == 2
        assert numbers_after[u[1]] == 1
        assert u[2] not in numbers_after
        assert u[3] not in numbers_after
        assert u[4] not in numbers_after


class TestMergeFeeds:
    @pytest.mark.asyncio
    async def test_nothing_to_merge(self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId) -> None:
        async with transaction() as trx:
            await tech_merge_feeds(trx, loaded_feed_id, another_loaded_feed_id)

    @pytest.mark.asyncio
    async def test_move_links(self) -> None:
        feed_1, feed_2, feed_3 = await f_make.n_feeds(3)

        user_a, user_b = await u_make.n_users(2)

        await add_link(user_a, feed_1.id)
        await add_link(user_b, feed_2.id)

        async with TableSizeNotChanged("fl_links"):
            async with transaction() as trx:
                await tech_merge_feeds(trx, from_feed_id=feed_2.id, to_feed_id=feed_3.id)

        links_a = await get_linked_feeds(user_a)
        links_b = await get_linked_feeds(user_b)

        assert {link.feed_id for link in links_a} == {feed_1.id}
        assert {link.feed_id for link in links_b} == {feed_3.id}

    @pytest.mark.asyncio
    async def test_rewrite_links(self) -> None:
        feed_1, feed_2, feed_3 = await f_make.n_feeds(3)

        user_a, user_b = await u_make.n_users(2)

        await add_link(user_a, feed_1.id)
        await add_link(user_b, feed_2.id)
        await add_link(user_b, feed_3.id)

        async with TableSizeDelta("fl_links", delta=-1):
            async with transaction() as trx:
                await tech_merge_feeds(trx, from_feed_id=feed_2.id, to_feed_id=feed_3.id)

        links_a = await get_linked_feeds(user_a)
        links_b = await get_linked_feeds(user_b)

        assert {link.feed_id for link in links_a} == {feed_1.id}
        assert {link.feed_id for link in links_b} == {feed_3.id}

    @pytest.mark.asyncio
    async def test_complex_ops(self) -> None:
        feed_1, feed_2, feed_3 = await f_make.n_feeds(3)

        user_a, user_b, user_c = await u_make.n_users(3)

        await add_link(user_a, feed_1.id)

        await add_link(user_b, feed_2.id)
        await add_link(user_b, feed_3.id)

        await add_link(user_c, feed_2.id)

        async with TableSizeDelta("fl_links", delta=-1):
            async with transaction() as trx:
                await tech_merge_feeds(trx, from_feed_id=feed_2.id, to_feed_id=feed_3.id)

        links_a = await get_linked_feeds(user_a)
        links_b = await get_linked_feeds(user_b)
        links_c = await get_linked_feeds(user_c)

        assert {link.feed_id for link in links_a} == {feed_1.id}
        assert {link.feed_id for link in links_b} == {feed_3.id}
        assert {link.feed_id for link in links_c} == {feed_3.id}
