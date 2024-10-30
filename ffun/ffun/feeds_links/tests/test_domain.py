import pytest

from ffun.domain.entities import FeedId, UserId
from ffun.feeds_links.domain import get_linked_users_flat
from ffun.feeds_links.operations import add_link


class TestGetLinkedUsersFlat:

    @pytest.mark.asyncio
    async def test_empty(self, saved_feed_id: FeedId) -> None:
        users = await get_linked_users_flat([saved_feed_id])

        assert users == set()

    @pytest.mark.asyncio
    async def test_returns_only_required(
        self, five_internal_user_ids: list[UserId], saved_feed_id: FeedId, another_saved_feed_id: FeedId
    ) -> None:
        user_1_id, user_2_id, user_3_id = five_internal_user_ids[:3]

        await add_link(user_1_id, saved_feed_id)

        await add_link(user_2_id, saved_feed_id)
        await add_link(user_2_id, another_saved_feed_id)

        await add_link(user_3_id, another_saved_feed_id)

        users = await get_linked_users_flat([saved_feed_id])

        assert users == {user_1_id, user_2_id}

        users = await get_linked_users_flat([another_saved_feed_id])

        assert users == {user_2_id, user_3_id}

        users = await get_linked_users_flat([saved_feed_id, another_saved_feed_id])

        assert users == {user_1_id, user_2_id, user_3_id}
