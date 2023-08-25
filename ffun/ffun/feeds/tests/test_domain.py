import uuid

import pytest

from .. import errors
from ..domain import get_feed


# get_feed function is checked in tests of other functions
class TestGetFeed:
    @pytest.mark.asyncio
    async def test_exception_if_no_feed_found(self) -> None:
        with pytest.raises(errors.NoFeedFound):
            await get_feed(uuid.uuid4())


# save_feeds function is checked in tests of other functions
class TestSaveFeeds:
    pass
