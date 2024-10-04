import pytest

from ffun.feeds.entities import Feed
from ffun.library import operations
from ffun.library.domain import get_entry, get_feeds_for_entry, normalize_entry
from ffun.library.entities import Entry, EntryChange


class TestNormalizeEntry:
    @pytest.mark.asyncio
    async def test_no_changes(self, cataloged_entry: Entry) -> None:
        changes = await normalize_entry(cataloged_entry)
        assert changes == []

        loaded_entry = await get_entry(cataloged_entry.id)
        assert loaded_entry == cataloged_entry

    @pytest.mark.parametrize("apply", [True, False])
    @pytest.mark.asyncio
    async def test_normalize_external_url(
        self, new_entry: Entry, loaded_feed: Feed, another_loaded_feed: Feed, apply: bool
    ) -> None:
        wrong_url = "/relative/url"
        expected_url = f"{loaded_feed.url}{wrong_url}"

        new_entry = new_entry.replace(external_url=wrong_url)

        assert loaded_feed.source_id == new_entry.source_id

        await operations.catalog_entries(loaded_feed.id, [new_entry])

        # this feed should be ignored, because current logic uses only the oldest link
        await operations.catalog_entries(another_loaded_feed.id, [new_entry])

        entry = await get_entry(new_entry.id)

        changes = await normalize_entry(entry, apply=apply)

        assert changes == [
            EntryChange(
                id=new_entry.id, field="external_url", old_value=new_entry.external_url, new_value=expected_url
            )
        ]

        loaded_entry = await get_entry(new_entry.id)

        if apply:
            assert loaded_entry.external_url == expected_url
        else:
            assert loaded_entry.external_url == wrong_url


class TestGetFeedsForEntry:

    @pytest.mark.asyncio
    async def test_single_feed(self, new_entry: Entry, loaded_feed: Feed) -> None:
        await operations.catalog_entries(loaded_feed.id, [new_entry])

        feeds = await get_feeds_for_entry(new_entry.id)

        assert feeds == {loaded_feed.id}

    @pytest.mark.asyncio
    async def test_multiple_feed(self, new_entry: Entry, loaded_feed: Feed, another_loaded_feed: Feed) -> None:
        await operations.catalog_entries(loaded_feed.id, [new_entry])
        await operations.catalog_entries(another_loaded_feed.id, [new_entry])

        feeds = await get_feeds_for_entry(new_entry.id)

        assert feeds == {loaded_feed.id, another_loaded_feed.id}

    @pytest.mark.asyncio
    async def test_no_feeds(self, new_entry: Entry, loaded_feed: Feed) -> None:
        await operations.catalog_entries(loaded_feed.id, [new_entry])

        await operations.unlink_feed_tail(loaded_feed.id, 0)

        feeds = await get_feeds_for_entry(new_entry.id)

        assert feeds == set()
