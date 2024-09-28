import pytest_asyncio

from ffun.feeds.domain import get_feed, mark_feed_as_loaded, save_feed
from ffun.feeds.entities import Feed, FeedId
from ffun.feeds.tests import make as f_make


@pytest_asyncio.fixture
async def new_feed() -> Feed:
    return await f_make.fake_feed()


@pytest_asyncio.fixture
async def another_new_feed() -> Feed:
    return await f_make.fake_feed()


@pytest_asyncio.fixture
async def saved_feed_id(new_feed: Feed) -> FeedId:
    return await save_feed(new_feed)


@pytest_asyncio.fixture
async def another_saved_feed_id(another_new_feed: Feed) -> FeedId:
    return await save_feed(another_new_feed)


@pytest_asyncio.fixture
async def saved_feed(saved_feed_id: FeedId) -> Feed:
    return await get_feed(saved_feed_id)


@pytest_asyncio.fixture
async def another_saved_feed(another_saved_feed_id: FeedId) -> Feed:
    return await get_feed(another_saved_feed_id)


@pytest_asyncio.fixture
async def loaded_feed_id(saved_feed_id: FeedId) -> FeedId:
    await mark_feed_as_loaded(saved_feed_id)
    return saved_feed_id


@pytest_asyncio.fixture
async def another_loaded_feed_id(another_saved_feed_id: FeedId) -> FeedId:
    await mark_feed_as_loaded(another_saved_feed_id)
    return another_saved_feed_id


@pytest_asyncio.fixture
async def loaded_feed(loaded_feed_id: FeedId) -> Feed:
    return await get_feed(loaded_feed_id)


@pytest_asyncio.fixture
async def another_loaded_feed(another_loaded_feed_id: FeedId) -> Feed:
    return await get_feed(another_loaded_feed_id)


@pytest_asyncio.fixture
async def five_saved_feed_ids() -> list[FeedId]:
    return [feed.id for feed in await f_make.n_feeds(5)]
