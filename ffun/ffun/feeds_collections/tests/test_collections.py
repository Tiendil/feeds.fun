
import pytest

from ffun.feeds_collections.collections import Collections


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
