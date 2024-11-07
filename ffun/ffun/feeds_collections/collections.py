import pathlib

import toml

from ffun.core import logging
from ffun.domain.domain import new_feed_id
from ffun.domain.urls import url_to_source_uid
from ffun.feeds import domain as f_domain
from ffun.feeds.domain import get_source_ids
from ffun.feeds.entities import Feed, FeedId
from ffun.feeds_collections import errors
from ffun.feeds_collections.entities import Collection, CollectionId, FeedInfo
from ffun.feeds_collections.settings import settings

logger = logging.get_module_logger()


class Collections:
    __slots__ = ("_collections", "initialized", "_feeds_in_collections")

    def __init__(self) -> None:
        self.initialized = False
        self._collections: list[Collection] = []
        self._feeds_in_collections: dict[FeedId, set[CollectionId]] = {}

    def collections(self) -> list[Collection]:
        return list(self._collections)

    def all_feed_ids(self) -> list[FeedId]:
        return list(self._feeds_in_collections.keys())

    def count_total_feeds(self) -> int:
        return len(self._feeds_in_collections)

    def collection(self, collection_id: CollectionId) -> Collection:
        for collection in self._collections:
            if collection.id == collection_id:
                return collection

        raise errors.CollectionNotFound()

    def load(self, collection_configs: pathlib.Path) -> None:
        """Loads all collection configs from the given directory."""
        collections = []

        for path in collection_configs.glob("*.toml"):
            data = toml.loads(path.read_text())

            collection = Collection(**data)

            collections.append(collection)

        self._collections = collections

    def validate_collection_ids(self) -> None:
        ids = {c.id for c in self._collections}

        if len(ids) != len(self._collections):
            raise errors.DuplicateCollectionIds()

    def validate_collection_gui_order(self) -> None:
        orders = {c.gui_order for c in self._collections}

        if len(orders) != len(self._collections):
            raise errors.DuplicateCollectionOrders()

    def validate_collection_is_not_empty(self) -> None:
        for collection in self._collections:
            if not collection.feeds:
                raise errors.CollectionIsEmpty()

    # This method may become a bottleneck if there are too many feeds in collections.
    # It could be optimized/removed by refactoring collections to be stored in a database
    # linked to all necessary ids only once.
    async def prepare_feeds(self) -> None:
        logger.info("preparing_feeds")

        feeds = []
        feeds_collections = []
        feed_infos = []

        source_uids = {
            feed_info.url: url_to_source_uid(feed_info.url)
            for collection in self._collections
            for feed_info in collection.feeds
        }

        source_ids = await get_source_ids(source_uids.values())

        # ensure that all feeds are really in the DB
        for collection in self._collections:
            for feed_info in collection.feeds:
                real_feed = Feed(
                    id=new_feed_id(),
                    source_id=source_ids[source_uids[feed_info.url]],
                    url=feed_info.url,
                    title=feed_info.title,
                    description=feed_info.description,
                )

                feed_infos.append(feed_info)
                feeds.append(real_feed)
                feeds_collections.append(collection.id)

        feed_ids = await f_domain.save_feeds(feeds)

        for feed_id, collection_id, feed_info in zip(feed_ids, feeds_collections, feed_infos):
            feed_info.feed_id = feed_id

            if feed_id not in self._feeds_in_collections:
                self._feeds_in_collections[feed_id] = set()

            self._feeds_in_collections[feed_id].add(collection_id)

        logger.info("feeds_prepared")

    def collections_for_feed(self, feed_id: FeedId) -> list[CollectionId]:
        return list(self._feeds_in_collections.get(feed_id, []))

    async def initialize(self, collection_configs: pathlib.Path | None = settings.collection_configs) -> None:
        logger.info("initializing_collections")

        if collection_configs is not None:
            self.load(collection_configs)

        self.validate_collection_ids()
        self.validate_collection_gui_order()
        self.validate_collection_is_not_empty()

        await self.prepare_feeds()

        self.initialized = True

        logger.info("collections_initialized")

    def has_feed(self, feed_id: FeedId) -> bool:
        return feed_id in self._feeds_in_collections

    # TODO: refactor collections logic to have only single feed object
    def get_feed_info(self, feed_id: FeedId) -> FeedInfo:
        for collection_id in self._feeds_in_collections.get(feed_id, ()):
            collection = self.collection(collection_id)

            for feed_info in collection.feeds:
                if feed_info.feed_id == feed_id:
                    return feed_info

        raise errors.FeedNotFound()

    async def add_test_collection(self, collection: Collection) -> None:
        self._collections.append(collection)
        await self.initialize(collection_configs=None)

    async def add_test_feed_to_collections(self, collection_id: CollectionId, feed_id: FeedId) -> None:

        feed = await f_domain.get_feed(feed_id)

        assert feed.title
        assert feed.description

        feed_info = FeedInfo(url=feed.url, title=feed.title, description=feed.description)

        for collection in self._collections:
            if collection.id == collection_id:
                collection.feeds.append(feed_info)
                break
        else:
            raise NotImplementedError("Collection not found")

        await self.initialize(collection_configs=None)


collections = Collections()
