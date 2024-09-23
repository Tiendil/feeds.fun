import pathlib

import toml

from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed, FeedId
from ffun.feeds_collections import errors
from ffun.feeds_collections.entities import Collection, CollectionId, FeedInfo
from ffun.feeds_collections.settings import settings


class Collections:
    __slots__ = ("_collections", "initialized", "_feeds_in_collections")

    def __init__(self) -> None:
        self.initialized = False
        self._collections: list[Collection] = []
        self._feeds_in_collections: set[FeedId] = set()

    # TODO: test
    def load(self, collection_configs: pathlib.Path) -> None:
        """Loads all collection configs from the given directory."""
        collections = []

        for path in collection_configs.glob("*.toml"):
            data = toml.loads(path.read_text())

            collection = Collection(**data)

            collections.append(collection)

        self._collections = collections

    # TODO: test
    def validate_collection_ids(self) -> None:
        ids = {c.id for c in self._collections}

        if len(ids) != len(self._collections):
            raise errors.DuplicateCollectionIds()

    # This method may become a bottleneck if there are too many feeds in collections.
    # It could be optimized/removed by refactoring collections to be stored in a database
    # linked to all necessary ids only once.
    async def prepare_feeds(self) -> None:
        feeds_infos = []
        feeds_to_process = []

        # ensure that all feeds are really in the DB
        for collection in self._collections:
            for feed_info in collection.feeds:
                real_feed = Feed(
                    id=f_domain.new_feed_id(),
                    url=feed_info.url,
                    title=feed_info.title,
                    description=feed_info.description,
                )

                feeds_infos.append(real_feed)
                feeds_to_process.append(real_feed)

        feed_ids = await f_domain.save_feeds(feeds_infos)

        self._feeds_in_collections = set(feed_ids)

    # TODO: test
    async def initialize(self, collection_configs: pathlib.Path | None = settings.collection_configs) -> None:

        if collection_configs is not None:
            self.load(collection_configs)

        self.validate_collection_ids()

        await self.prepare_feeds()

        self.initialized = True

    # TODO: test
    def has_feed(self, feed_id: FeedId) -> bool:
        return feed_id in self._feeds_in_collections

    # TODO: test
    async def add_test_collection(self, collection: Collection) -> None:
        self._collections.append(collection)
        await self.initialize(collection_configs=None)

    # TODO: test
    # TODO: switch all mocks in tests to this function
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
