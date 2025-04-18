import uuid

import pytest
import pytest_asyncio

from ffun.domain.domain import new_collection_id
from ffun.domain.entities import CollectionSlug
from ffun.domain.urls import str_to_absolute_url, to_feed_url
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import Collection, CollectionId, FeedInfo
from ffun.feeds_collections.settings import settings


@pytest.fixture(scope="session", autouse=True)
def collection_configs_must_be_none_in_tests() -> None:
    assert settings.collection_configs is None


@pytest_asyncio.fixture(scope="session")
async def collection_id_for_test_feeds(collection_configs_must_be_none_in_tests: None) -> CollectionId:

    feed_id_ = uuid.uuid4().hex

    feed = FeedInfo(
        url=to_feed_url(str_to_absolute_url(f"http://example.com/{feed_id_}")),
        title=f"Feed {feed_id_}",
        description=f"Feed {feed_id_}",
    )

    collection = Collection(
        id=new_collection_id(),
        slug=CollectionSlug(uuid.uuid4().hex),
        gui_order=1,
        name=uuid.uuid4().hex,
        description=uuid.uuid4().hex,
        feeds=[feed],
        show_on_main=True,
    )

    await collections.add_test_collection(collection)

    return collection.id
