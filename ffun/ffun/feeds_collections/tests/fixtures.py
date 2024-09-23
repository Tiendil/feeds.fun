import uuid

import pytest
import pytest_asyncio

from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.domain import new_collection_id
from ffun.feeds_collections.entities import Collection, CollectionId
from ffun.feeds_collections.settings import settings


@pytest.fixture(scope="session")
def collection_configs_should_be_none_in_tests() -> None:
    assert settings.collection_configs is None


@pytest_asyncio.fixture(scope="session")
async def collection_id_for_test_feeds() -> CollectionId:
    collection = Collection(id=new_collection_id(), name=uuid.uuid4().hex, description=uuid.uuid4().hex, feeds=[])

    await collections.add_test_collection(collection)

    return collection.id
