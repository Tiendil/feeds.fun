
import pytest

from ffun.feeds_collections.collections import Collections
from ffun.feeds import domain as f_domain
import pathlib


_root = pathlib.Path(__file__).parent


class TestCollections:

    def test_constructor(self) -> None:
        collections = Collections()

        assert not collections.initialized
        assert collections._collections == []
        assert collections._feeds_in_collections == set()

    @pytest.mark.asyncio
    async def test_initialize__no_feeds(self) -> None:
        collections = Collections()

        await collections.initialize(collection_configs=None)

        assert collections.initialized
        assert collections._collections == []
        assert collections._feeds_in_collections == set()

    @pytest.mark.asyncio
    async def test_initialize__has_feeds(self) -> None:
        collections = Collections()

        await collections.initialize(collection_configs=_root / "fixtures" / "test_collections")

        assert collections.initialized
        assert {c.name for c in collections._collections} == {"Feeds Fun", "Scientific Papers"}

        assert len(collections._feeds_in_collections) == 3

        feeds = await f_domain.get_feeds(collections._feeds_in_collections)

        expected_urls = set()

        for collection in collections._collections:
            for feed_info in collection.feeds:
                expected_urls.add(feed_info.url)

        assert expected_urls == {feed.url for feed in feeds}
