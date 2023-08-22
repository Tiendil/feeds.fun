import uuid

import pytest

from .. import errors
from ..entities import Feed
from ..operations import get_feed, save_feed


class TestSaveFeed:

    @pytest.mark.asyncio
    async def test_new_feed(self, new_feed: Feed) -> None:
        feed_id = await save_feed(new_feed)
        assert feed_id == new_feed.id
        assert await get_feed(new_feed.id) == new_feed

    @pytest.mark.asyncio
    async def test_existed_feed(self, new_feed: Feed) -> None:
        original_feed_id = await save_feed(new_feed)

        cloned_feed = new_feed.replace(id=uuid.uuid4())

        saved_feed_id = await save_feed(cloned_feed)

        assert original_feed_id == saved_feed_id

        assert await get_feed(original_feed_id) == new_feed

        with pytest.raises(errors.NoFeedFound):
            await get_feed(cloned_feed.id)


# get_feed function is checked in tests of other functions
class TestGetFeed:

    @pytest.mark.asyncio
    async def test_exception_if_no_feed_found(self) -> None:
        with pytest.raises(errors.NoFeedFound):
            await get_feed(uuid.uuid4())
