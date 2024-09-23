import functools
import random
import uuid

import pytest
import pytest_asyncio

from ffun.feeds.domain import save_feed
from ffun.feeds.entities import Feed, FeedId
from ffun.feeds.tests import make as f_make
from ffun.feeds_collections.settings import settings
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import Collection, FeedInfo, CollectionId
from ffun.feeds_collections.domain import new_collection_id


@pytest.fixture(scope="session")
def collection_configs_should_be_none_in_tests() -> None:
    assert settings.collection_configs is None


@pytest_asyncio.fixture(scope="session")
async def collection_id_for_test_feeds() -> CollectionId:
    collection = Collection(id=new_collection_id(),
                            name=uuid.uuid4().hex,
                            description=uuid.uuid4().hex,
                            feeds=[])

    await collections.add_test_collection(collection)

    return collection.id


@pytest_asyncio.fixture
async def saved_collection_feed_id(collection_id_for_test_feeds: CollectionId) -> FeedId:
    feeds = await f_make.n_feeds(1)

    feed = feeds[0]

    assert feed.title
    assert feed.description

    feed_info = FeedInfo(url=feed.url, title=feed.title, description=feed.description)

    await collections.add_test_feed_to_collections(collection_id_for_test_feeds, feed_info)

    return feed.id
