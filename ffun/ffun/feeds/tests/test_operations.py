import asyncio
import random
import uuid

import pytest

from ffun.core import utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction

from .. import errors
from ..entities import Feed, FeedError, FeedState
from ..operations import (get_feed, get_next_feeds_to_load, mark_feed_as_failed, mark_feed_as_loaded, save_feed,
                          update_feed_info)
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


class TestUpdateFeedInfo:

    @pytest.mark.asyncio
    async def test(self, loaded_feed: Feed) -> None:
        new_title = make.fake_title()
        new_description = make.fake_description()

        await update_feed_info(feed_id=loaded_feed.id,
                               title=new_title,
                               description=new_description)

        updated_feed = await get_feed(loaded_feed.id)

        assert updated_feed.title == new_title
        assert updated_feed.description == new_description


class TestMarkFeedAsLoaded:

    @pytest.mark.asyncio
    async def test(self, loaded_feed: Feed) -> None:
        now = utils.now()

        await mark_feed_as_loaded(feed_id=loaded_feed.id)

        updated_feed = await get_feed(loaded_feed.id)

        assert updated_feed.loaded_at is not None
        assert now < updated_feed.loaded_at
        assert updated_feed.last_error is None
        assert updated_feed.state == FeedState.loaded

    @pytest.mark.asyncio
    async def test_reset_error_state(self, loaded_feed: Feed) -> None:
        await mark_feed_as_failed(feed_id=loaded_feed.id,
                                  state=FeedState.damaged,
                                  error=random.choice(list(FeedError)))

        await mark_feed_as_loaded(feed_id=loaded_feed.id)

        updated_feed = await get_feed(loaded_feed.id)

        assert updated_feed.last_error is None


class TestMarkFeedAsFailed:

    @pytest.mark.asyncio
    async def test(self, loaded_feed: Feed) -> None:
        error = random.choice(list(FeedError))

        await mark_feed_as_failed(feed_id=loaded_feed.id,
                                  state=FeedState.damaged,
                                  error=error)

        updated_feed = await get_feed(loaded_feed.id)

        assert updated_feed.state == FeedState.damaged
        assert updated_feed.last_error == error
