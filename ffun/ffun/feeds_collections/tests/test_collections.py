import pathlib
import uuid

import pytest
import pytest_asyncio

from ffun.domain.domain import new_collection_id, new_feed_id
from ffun.domain.urls import url_to_source_uid
from ffun.feeds import domain as f_domain
from ffun.feeds_collections import errors
from ffun.feeds_collections.collections import Collections
from ffun.feeds_collections.entities import Collection, FeedInfo

_root = pathlib.Path(__file__).parent

_test_collections_configs = _root / "fixtures" / "test_collections"


class TestCollections:

    @pytest_asyncio.fixture(scope="session")
    async def collections(self) -> Collections:
        collections = Collections()

        await collections.initialize(collection_configs=_test_collections_configs)

        return collections

    def test_constructor(self) -> None:
        collections = Collections()

        assert not collections.initialized
        assert collections._collections == []
        assert collections._feeds_in_collections == {}

    @pytest.mark.asyncio
    async def test_initialize__no_feeds(self) -> None:
        collections = Collections()

        await collections.initialize(collection_configs=None)

        assert collections.initialized
        assert collections._collections == []
        assert collections._feeds_in_collections == {}

    # Also tests:
    # - Collections.load
    # - Collections.prepare_feeds
    @pytest.mark.asyncio
    async def test_initialize__has_feeds(self, collections: Collections) -> None:
        assert collections.initialized
        assert {c.name for c in collections._collections} == {"Feeds Fun", "Scientific Papers"}

        assert len(collections._feeds_in_collections) == 3

        feeds = await f_domain.get_feeds(collections._feeds_in_collections)
        feed_ids = {feed.id for feed in feeds}

        expected_urls = set()

        for collection in collections._collections:
            for feed_info in collection.feeds:
                assert feed_info.feed_id in collections._feeds_in_collections
                assert feed_info.feed_id in feed_ids
                expected_urls.add(feed_info.url)

        assert expected_urls == {feed.url for feed in feeds}

        # test that feeds created with correct source ids
        source_uids = {url_to_source_uid(url) for url in expected_urls}
        source_ids = await f_domain.get_source_ids(source_uids)

        for feed in feeds:
            assert feed.source_id == source_ids[url_to_source_uid(feed.url)]

        assert collections.count_total_feeds() == len(feeds)
        assert set(collections.all_feed_ids()) == {feed.id for feed in feeds}

    @pytest.mark.asyncio
    async def test_collections(self, collections: Collections) -> None:
        assert collections.collections() == collections._collections
        assert collections.collections() is not collections._collections

    @pytest.mark.asyncio
    async def test_collection(self, collections: Collections) -> None:
        for collection in collections._collections:
            assert collections.collection(collection.id) == collection

    @pytest.mark.asyncio
    async def test_collection__no_collection(self, collections: Collections) -> None:
        with pytest.raises(errors.CollectionNotFound):
            collections.collection(new_collection_id())

    @pytest.mark.asyncio
    async def test_has_feed(self, collections: Collections) -> None:
        assert not collections.has_feed(new_feed_id())

        existed_feed_id = list(collections._feeds_in_collections)[0]
        assert collections.has_feed(existed_feed_id)

    @pytest.mark.asyncio
    async def test_get_feed_info__feed_not_found(self, collections: Collections) -> None:
        with pytest.raises(errors.FeedNotFound):
            collections.get_feed_info(new_feed_id())

    @pytest.mark.asyncio
    async def test_get_feed_info(self, collections: Collections) -> None:
        existed_feed_id = list(collections._feeds_in_collections)[0]

        feed_info = collections.get_feed_info(existed_feed_id)

        assert feed_info.feed_id == existed_feed_id

    @pytest.mark.asyncio
    async def test_validate_collections_ids(self) -> None:
        collections = Collections()

        feed_1 = FeedInfo(url="http://example.com/feed1", title="Feed 1", description="Feed 1")

        collection_1 = Collection(
            id=new_collection_id(), gui_order=1, name=uuid.uuid4().hex, description=uuid.uuid4().hex, feeds=[feed_1]
        )

        collection_2 = Collection(
            id=collection_1.id, gui_order=2, name=uuid.uuid4().hex, description=uuid.uuid4().hex, feeds=[feed_1]
        )

        await collections.add_test_collection(collection_1)

        with pytest.raises(errors.DuplicateCollectionIds):
            await collections.add_test_collection(collection_2)

    @pytest.mark.asyncio
    async def test_validate_gui_order(self) -> None:
        collections = Collections()

        feed_1 = FeedInfo(url="http://example.com/feed1", title="Feed 1", description="Feed 1")

        collection_1 = Collection(
            id=new_collection_id(), gui_order=1, name=uuid.uuid4().hex, description=uuid.uuid4().hex, feeds=[feed_1]
        )

        collection_2 = Collection(
            id=new_collection_id(), gui_order=1, name=uuid.uuid4().hex, description=uuid.uuid4().hex, feeds=[feed_1]
        )

        await collections.add_test_collection(collection_1)

        with pytest.raises(errors.DuplicateCollectionOrders):
            await collections.add_test_collection(collection_2)

    @pytest.mark.asyncio
    async def test_validate_emptiness(self) -> None:
        collections = Collections()

        feed_1 = FeedInfo(url="http://example.com/feed1", title="Feed 1", description="Feed 1")

        collection_1 = Collection(
            id=new_collection_id(), gui_order=1, name=uuid.uuid4().hex, description=uuid.uuid4().hex, feeds=[feed_1]
        )

        collection_2 = Collection(
            id=new_collection_id(), gui_order=2, name=uuid.uuid4().hex, description=uuid.uuid4().hex, feeds=[]
        )

        await collections.add_test_collection(collection_1)

        with pytest.raises(errors.CollectionIsEmpty):
            await collections.add_test_collection(collection_2)

    def test_collections_for_feed(self, collections: Collections) -> None:
        for collection in collections._collections:
            for feed_info in collection.feeds:
                assert feed_info.feed_id is not None
                assert collection.id in collections.collections_for_feed(feed_info.feed_id)

    def test_collections_for_feed__no_collection(self, collections: Collections) -> None:
        for collection in collections._collections:
            assert collection.id not in collections.collections_for_feed(new_feed_id())
