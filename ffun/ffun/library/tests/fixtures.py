import pytest_asyncio

from ffun.domain.entities import FeedId
from ffun.feeds.entities import Feed
from ffun.library.domain import catalog_entries, get_entry
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make


@pytest_asyncio.fixture
def new_entry(loaded_feed: Feed) -> Entry:
    return l_make.fake_entry(loaded_feed.source_id)


@pytest_asyncio.fixture
def another_new_entry(another_loaded_feed: Feed) -> Entry:
    return l_make.fake_entry(another_loaded_feed.source_id)


@pytest_asyncio.fixture
async def cataloged_entry(loaded_feed_id: FeedId, new_entry: Entry) -> Entry:
    await catalog_entries(loaded_feed_id, [new_entry])
    return await get_entry(new_entry.id)


@pytest_asyncio.fixture
async def another_cataloged_entry(another_loaded_feed_id: FeedId, another_new_entry: Entry) -> Entry:
    await catalog_entries(another_loaded_feed_id, [another_new_entry])
    return await get_entry(another_new_entry.id)
