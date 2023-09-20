import functools
import random
import uuid

import pytest
import pytest_asyncio

from ffun.feeds.domain import save_feed
from ffun.feeds.entities import Feed
from ffun.feeds.tests import make as f_make
from ffun.feeds_collections import predefines


@functools.cache
def all_urls() -> set[str]:
    urls = set()

    for collection in predefines.predefines.values():
        urls.update(collection)

    return urls


@pytest.fixture
def new_collection_feed() -> Feed:
    return f_make.fake_feed(url=random.choice(list(all_urls())))


@pytest_asyncio.fixture
async def saved_collection_feed_id(new_collection_feed: Feed) -> uuid.UUID:
    return await save_feed(new_collection_feed)
