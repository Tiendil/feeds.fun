import uuid

import pytest
import pytest_asyncio

from ffun.library.domain import catalog_entries, get_entry
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make


@pytest.fixture
def new_entry(loaded_feed_id: uuid.UUID) -> Entry:
    return l_make.fake_entry(loaded_feed_id)


@pytest.fixture
def another_new_entry(another_loaded_feed_id: uuid.UUID) -> Entry:
    return l_make.fake_entry(another_loaded_feed_id)


@pytest_asyncio.fixture
async def cataloged_entry(new_entry: Entry) -> Entry:
    await catalog_entries([new_entry])
    return await get_entry(new_entry.id)


@pytest_asyncio.fixture
async def another_cataloged_entry(another_new_entry: Entry) -> Entry:
    await catalog_entries([another_new_entry])
    return await get_entry(another_new_entry.id)
