import asyncio
import random
import uuid

import pytest

from ffun.core import utils
from ffun.core.tests.helpers import Delta, TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_feed_id
from ffun.domain.entities import FeedId
from ffun.domain.urls import str_to_absolute_url, url_to_uid
from ffun.feeds import errors
from ffun.feeds.domain import get_feed, save_feeds
from ffun.feeds.entities import Feed, FeedError, FeedState
from ffun.feeds.operations import (
    count_total_feeds,
    count_total_feeds_per_last_error,
    count_total_feeds_per_state,
    get_feed_ids_by_uids,
    get_feeds,
    get_next_feeds_to_load,
    get_source_ids,
    mark_feed_as_failed,
    mark_feed_as_loaded,
    mark_feed_as_orphaned,
    save_feed,
    tech_remove_feed,
    update_feed_info,
)
from ffun.feeds.tests import make


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

    @pytest.mark.asyncio
    async def test_same_uid_different_urls(self, new_feed: Feed) -> None:
        url_part = uuid.uuid4().hex

        feed_1 = new_feed.replace(url=f"http://example.com/{url_part}")
        feed_2 = new_feed.replace(id=uuid.uuid4(), url=f"https://example.com/{url_part}")

        feed_1_id = await save_feed(feed_1)
        feed_2_id = await save_feed(feed_2)

        assert feed_1_id == feed_2_id

        assert await get_feed(feed_1_id) == feed_1

        with pytest.raises(errors.NoFeedFound):
            await get_feed(feed_2.id)


class TestGetNextFeedToLoad:
    @pytest.mark.asyncio
    async def test_find_new_feed(self, saved_feed_id: FeedId) -> None:
        now = utils.now()

        found_feeds = await get_next_feeds_to_load(number=100500, loaded_before=now)

        feeds = {feed.id: feed for feed in found_feeds}

        found_feed = feeds[saved_feed_id]

        assert now < found_feed.load_attempted_at

        loaded_feed = await get_feed(saved_feed_id)

        assert loaded_feed.load_attempted_at == found_feed.load_attempted_at

    @pytest.mark.asyncio
    async def test_skip_choosen_feeds(self, saved_feed_id: FeedId) -> None:
        now = utils.now()

        await get_next_feeds_to_load(number=100500, loaded_before=now)

        found_feeds = await get_next_feeds_to_load(number=100500, loaded_before=now)

        assert not found_feeds

    @pytest.mark.asyncio
    async def test_find_choosen_after_time_passes(self, saved_feed_id: FeedId) -> None:
        await get_next_feeds_to_load(number=100500, loaded_before=utils.now())

        now = utils.now()

        found_feeds = await get_next_feeds_to_load(number=100500, loaded_before=now)

        feeds = {feed.id: feed for feed in found_feeds}

        found_feed = feeds[saved_feed_id]

        assert now < found_feed.load_attempted_at

        loaded_feed = await get_feed(saved_feed_id)

        assert loaded_feed.load_attempted_at == found_feed.load_attempted_at

    @pytest.mark.asyncio
    async def test_limit(self) -> None:
        now = utils.now()

        # mark existed feeds as chosen
        await get_next_feeds_to_load(number=100500, loaded_before=now)

        n = 10
        m = 3

        feed_ids = set(await save_feeds([await make.fake_feed() for _ in range(n)]))

        while feed_ids:
            found_feeds = await get_next_feeds_to_load(number=m, loaded_before=now)

            assert len(found_feeds) == min(m, len(feed_ids))

            found_feed_ids = {feed.id for feed in found_feeds}

            assert found_feed_ids <= feed_ids

            feed_ids -= found_feed_ids

    @pytest.mark.asyncio
    async def test_concurent_run(self) -> None:
        now = utils.now()

        # mark existed feeds as chosen
        await get_next_feeds_to_load(number=100500, loaded_before=now)

        n = 10
        m = 3

        feed_ids = set(await save_feeds([await make.fake_feed() for _ in range(n)]))

        tasks = [get_next_feeds_to_load(number=m, loaded_before=now) for _ in range(n // m + 1)]

        results = await asyncio.gather(*tasks)

        found_feed_ids = {feed.id for feeds in results for feed in feeds}

        assert found_feed_ids == feed_ids


class TestUpdateFeedInfo:
    @pytest.mark.asyncio
    async def test(self, saved_feed: Feed) -> None:
        new_title = make.fake_title()
        new_description = make.fake_description()

        await update_feed_info(feed_id=saved_feed.id, title=new_title, description=new_description)

        updated_feed = await get_feed(saved_feed.id)

        assert updated_feed.title == new_title
        assert updated_feed.description == new_description


class TestMarkFeedAsLoaded:
    @pytest.mark.asyncio
    async def test(self, saved_feed: Feed) -> None:
        now = utils.now()

        await mark_feed_as_loaded(feed_id=saved_feed.id)

        updated_feed = await get_feed(saved_feed.id)

        assert updated_feed.loaded_at is not None
        assert now < updated_feed.loaded_at
        assert updated_feed.last_error is None
        assert updated_feed.state == FeedState.loaded

    @pytest.mark.asyncio
    async def test_reset_error_state(self, saved_feed: Feed) -> None:
        await mark_feed_as_failed(feed_id=saved_feed.id, state=FeedState.damaged, error=random.choice(list(FeedError)))

        await mark_feed_as_loaded(feed_id=saved_feed.id)

        updated_feed = await get_feed(saved_feed.id)

        assert updated_feed.last_error is None


class TestMarkFeedAsFailed:
    @pytest.mark.asyncio
    async def test(self, saved_feed: Feed) -> None:
        error = random.choice(list(FeedError))

        await mark_feed_as_failed(feed_id=saved_feed.id, state=FeedState.damaged, error=error)

        updated_feed = await get_feed(saved_feed.id)

        assert updated_feed.state == FeedState.damaged
        assert updated_feed.last_error == error


class TestMarkFeedAsOrphaned:
    @pytest.mark.asyncio
    async def test(self, saved_feed: Feed) -> None:
        await mark_feed_as_orphaned(feed_id=saved_feed.id)

        assert saved_feed.loaded_at is None

        updated_feed = await get_feed(saved_feed.id)

        assert updated_feed.loaded_at is None
        assert updated_feed.last_error is None
        assert updated_feed.state == FeedState.orphaned

    @pytest.mark.asyncio
    async def test_reset_error_state(self, saved_feed: Feed) -> None:
        await mark_feed_as_failed(feed_id=saved_feed.id, state=FeedState.damaged, error=random.choice(list(FeedError)))

        await mark_feed_as_orphaned(feed_id=saved_feed.id)

        updated_feed = await get_feed(saved_feed.id)

        assert updated_feed.last_error is None


class TestGetFeeds:
    @pytest.mark.asyncio
    async def test(self) -> None:
        n = 3

        feed_ids = []

        for _ in range(n + 2):
            raw_feed = await make.fake_feed()
            feed_id = await save_feed(raw_feed)
            feed_ids.append(feed_id)

        loaded_feeds = await get_feeds(feed_ids[1:-1])

        assert len(loaded_feeds) == n

        assert set(feed_ids[1:-1]) == {feed.id for feed in loaded_feeds}


class TestGetFeedIdsByUids:

    @pytest.mark.asyncio
    async def test_no_uids_passed(self) -> None:
        ids = await get_feed_ids_by_uids([])

        assert ids == {}

    @pytest.mark.asyncio
    async def test_load(self, saved_feed: Feed, another_saved_feed: Feed) -> None:
        uids = [
            url_to_uid(saved_feed.url),
            url_to_uid(another_saved_feed.url),
            url_to_uid(str_to_absolute_url(f"http://{uuid.uuid4().hex}.com/")),
        ]

        ids = await get_feed_ids_by_uids(uids)

        assert len(ids) == 2

        assert ids[uids[0]] == saved_feed.id
        assert ids[uids[1]] == another_saved_feed.id


class TestGetSourceIds:

    @pytest.mark.asyncio
    async def test_no_uids_passed(self) -> None:
        async with TableSizeNotChanged("f_sources"):
            ids = await get_source_ids([])

        assert ids == {}

    @pytest.mark.asyncio
    async def test_all_new(self) -> None:
        n = 3

        uids = [f"{uuid.uuid4().hex}.com" for _ in range(n)]

        async with TableSizeDelta("f_sources", delta=n):
            ids = await get_source_ids(uids)

        assert set(ids.keys()) == set(uids)

    @pytest.mark.asyncio
    async def test_partially_saved(self) -> None:
        n = 5
        m = 3

        uids = [f"{uuid.uuid4().hex}.com" for _ in range(n)]

        await get_source_ids(uids[:m])

        async with TableSizeDelta("f_sources", delta=n - m):
            ids = await get_source_ids(uids)

        assert set(ids.keys()) == set(uids)


class TestTechRemoveFeed:
    @pytest.mark.asyncio
    async def test(self, saved_feed: Feed) -> None:
        async with TableSizeDelta("f_feeds", delta=-1):
            await tech_remove_feed(saved_feed.id)

        with pytest.raises(errors.NoFeedFound):
            await get_feed(saved_feed.id)

    @pytest.mark.asyncio
    async def test_no_feed(self) -> None:
        await tech_remove_feed(new_feed_id())


class TestCountTotalFeeds:

    @pytest.mark.asyncio
    async def test(self) -> None:
        async with Delta(count_total_feeds, delta=3):
            await save_feeds([await make.fake_feed() for _ in range(3)])


class TestCountTotalFeedsPerState:

    @pytest.mark.asyncio
    async def test(self) -> None:
        numbers_before = await count_total_feeds_per_state()

        await save_feeds(
            [
                await make.fake_feed(state=FeedState.loaded),
                await make.fake_feed(state=FeedState.damaged),
                await make.fake_feed(state=FeedState.loaded),
                await make.fake_feed(state=FeedState.orphaned),
                await make.fake_feed(state=FeedState.loaded),
            ]
        )

        numbers_after = await count_total_feeds_per_state()

        assert numbers_after[FeedState.loaded] == numbers_before.get(FeedState.loaded, 0) + 3
        assert numbers_after[FeedState.damaged] == numbers_before.get(FeedState.damaged, 0) + 1
        assert numbers_after[FeedState.orphaned] == numbers_before.get(FeedState.orphaned, 0) + 1


class TestCountTotalFeedsPerLastError:

    @pytest.mark.asyncio
    async def test(self) -> None:
        numbers_before = await count_total_feeds_per_last_error()

        feeds = await make.n_feeds(5)

        await mark_feed_as_loaded(feed_id=feeds[0].id)
        await mark_feed_as_failed(
            feed_id=feeds[1].id, state=FeedState.damaged, error=FeedError.network_wrong_ssl_version
        )
        await mark_feed_as_loaded(feed_id=feeds[2].id)
        await mark_feed_as_failed(
            feed_id=feeds[3].id, state=FeedState.damaged, error=FeedError.network_wrong_ssl_version
        )
        await mark_feed_as_failed(
            feed_id=feeds[4].id, state=FeedState.damaged, error=FeedError.protocol_no_entries_in_feed
        )

        numbers_after = await count_total_feeds_per_last_error()

        assert (
            numbers_after[FeedError.network_wrong_ssl_version]
            == numbers_before[FeedError.network_wrong_ssl_version] + 2
        )
        assert (
            numbers_after[FeedError.protocol_no_entries_in_feed]
            == numbers_before[FeedError.protocol_no_entries_in_feed] + 1
        )
