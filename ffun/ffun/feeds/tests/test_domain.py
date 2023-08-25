import asyncio
import random
import uuid

import pytest

from ffun.core import utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction

from .. import errors
from ..domain import get_feed, save_feeds
from ..entities import Feed, FeedError, FeedState
from ..operations import (
    get_feeds,
    get_next_feeds_to_load,
    mark_feed_as_failed,
    mark_feed_as_loaded,
    mark_feed_as_orphaned,
    save_feed,
    update_feed_info,
)
from . import make


# get_feed function is checked in tests of other functions
class TestGetFeed:
    @pytest.mark.asyncio
    async def test_exception_if_no_feed_found(self) -> None:
        with pytest.raises(errors.NoFeedFound):
            await get_feed(uuid.uuid4())


# save_feeds function is checked in tests of other functions
class TestSaveFeeds:
    pass
