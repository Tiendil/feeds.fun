import asyncio
import uuid

import pytest

from ffun.core import utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction

from .. import errors
from ..entities import Feed
from ..operations import get_feed, get_next_feeds_to_load, save_feed
from . import make


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


class TestGetNextFeedToLoad:

    @pytest.mark.asyncio
    async def test_find_new_feed(self, saved_feed_id: uuid.UUID) -> None:
        now = utils.now()

        found_feeds = await get_next_feeds_to_load(number=100500,
                                                   loaded_before=now)

        feeds = {feed.id: feed for feed in found_feeds}

        found_feed = feeds[saved_feed_id]

        assert now < found_feed.load_attempted_at

        loaded_feed = await get_feed(saved_feed_id)

        assert loaded_feed.load_attempted_at == found_feed.load_attempted_at

    @pytest.mark.asyncio
    async def test_skip_choosen_feeds(self, saved_feed_id: uuid.UUID) -> None:
        now = utils.now()

        await get_next_feeds_to_load(number=100500,
                                     loaded_before=now)

        found_feeds = await get_next_feeds_to_load(number=100500,
                                                   loaded_before=now)

        assert not found_feeds

    @pytest.mark.asyncio
    async def test_find_choosen_after_time_passes(self, saved_feed_id: uuid.UUID) -> None:

        await get_next_feeds_to_load(number=100500,
                                     loaded_before=utils.now())

        now = utils.now()

        found_feeds = await get_next_feeds_to_load(number=100500,
                                                   loaded_before=now)

        feeds = {feed.id: feed for feed in found_feeds}

        found_feed = feeds[saved_feed_id]

        assert now < found_feed.load_attempted_at

        loaded_feed = await get_feed(saved_feed_id)

        assert loaded_feed.load_attempted_at == found_feed.load_attempted_at

    @pytest.mark.asyncio
    async def test_limit(self) -> None:

        now = utils.now()

        # mark existed feeds as chosen
        await get_next_feeds_to_load(number=100500,
                                     loaded_before=now)

        n = 10
        m = 3

        feed_ids = set()

        for _ in range(n):
            raw_feed = make.fake_feed()
            feed_id = await save_feed(raw_feed)
            feed_ids.add(feed_id)

        while feed_ids:
            found_feeds = await get_next_feeds_to_load(number=m,
                                                       loaded_before=now)

            assert len(found_feeds) == min(m, len(feed_ids))

            found_feed_ids = {feed.id for feed in found_feeds}

            assert found_feed_ids <= feed_ids

            feed_ids -= found_feed_ids

    @pytest.mark.asyncio
    async def test_concurent_run(self) -> None:

        now = utils.now()

        # mark existed feeds as chosen
        await get_next_feeds_to_load(number=100500,
                                     loaded_before=now)

        n = 10
        m = 3

        feed_ids = set()

        for _ in range(n):
            raw_feed = make.fake_feed()
            feed_id = await save_feed(raw_feed)
            feed_ids.add(feed_id)

        tasks = [get_next_feeds_to_load(number=m,
                                        loaded_before=now)
                 for _ in range(n // m + 1)]

        results = await asyncio.gather(*tasks)

        found_feed_ids = {feed.id
                          for feeds in results
                          for feed in feeds}

        assert found_feed_ids == feed_ids
