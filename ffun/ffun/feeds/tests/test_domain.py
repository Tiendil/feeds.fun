import pytest

from ffun.domain.domain import new_feed_id
from ffun.feeds import errors
from ffun.feeds.domain import get_feed


# get_feed function is checked in tests of other functions
class TestGetFeed:
    @pytest.mark.asyncio
    async def test_exception_if_no_feed_found(self) -> None:
        with pytest.raises(errors.NoFeedFound):
            await get_feed(new_feed_id())


# save_feeds function is checked in tests of other functions
class TestSaveFeeds:
    pass
