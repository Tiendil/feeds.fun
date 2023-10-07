import uuid

import pytest
import pytest_asyncio

from ffun.feeds.domain import get_feed, mark_feed_as_loaded, save_feed
from ffun.feeds.entities import Feed
from ffun.feeds.tests import make as f_make


@pytest.fixture
def new_feed() -> Feed:
    return f_make.fake_feed()


@pytest.fixture
def another_new_feed() -> Feed:
    return f_make.fake_feed()


@pytest_asyncio.fixture
async def saved_feed_id(new_feed: Feed) -> uuid.UUID:
    return await save_feed(new_feed)


@pytest_asyncio.fixture
async def another_saved_feed_id(another_new_feed: Feed) -> uuid.UUID:
    return await save_feed(another_new_feed)


@pytest_asyncio.fixture
async def saved_feed(saved_feed_id: uuid.UUID) -> Feed:
    return await get_feed(saved_feed_id)


@pytest_asyncio.fixture
async def another_saved_feed(another_saved_feed_id: uuid.UUID) -> Feed:
    return await get_feed(another_saved_feed_id)


@pytest_asyncio.fixture
async def loaded_feed_id(saved_feed_id: uuid.UUID) -> uuid.UUID:
    await mark_feed_as_loaded(saved_feed_id)
    return saved_feed_id


@pytest_asyncio.fixture
async def another_loaded_feed_id(another_saved_feed_id: uuid.UUID) -> uuid.UUID:
    await mark_feed_as_loaded(another_saved_feed_id)
    return another_saved_feed_id


@pytest_asyncio.fixture
async def loaded_feed(loaded_feed_id: uuid.UUID) -> Feed:
    return await get_feed(loaded_feed_id)


@pytest_asyncio.fixture
async def another_loaded_feed(another_loaded_feed_id: uuid.UUID) -> Feed:
    return await get_feed(another_loaded_feed_id)
