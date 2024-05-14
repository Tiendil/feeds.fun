import uuid

import pytest

from ffun.core.postgresql import transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.feeds.tests import make as f_make
from ffun.feeds_links.operations import add_link, get_linked_feeds, tech_merge_feeds
from ffun.users.tests import make as u_make


class TestMergeFeeds:
    @pytest.mark.asyncio
    async def test_nothing_to_merge(self, loaded_feed_id: uuid.UUID, another_loaded_feed_id: uuid.UUID) -> None:
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
