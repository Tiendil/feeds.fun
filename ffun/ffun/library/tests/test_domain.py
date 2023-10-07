import pytest

from ffun.feeds.entities import Feed
from ffun.library.domain import get_entry, normalize_entry
from ffun.library.entities import Entry, EntryChange
from ffun.library.operations import catalog_entries


class TestNormalizeEntry:
    @pytest.mark.asyncio
    async def test_no_changes(self, cataloged_entry: Entry) -> None:
        changes = await normalize_entry(cataloged_entry)
        assert changes == []

        loaded_entry = await get_entry(cataloged_entry.id)
        assert loaded_entry == cataloged_entry

    @pytest.mark.parametrize("apply", [True, False])
    @pytest.mark.asyncio
    async def test_normalize_external_url(self, new_entry: Entry, loaded_feed: Feed, apply: bool) -> None:
        wrong_url = "/relative/url"
        expected_url = f"{loaded_feed.url}{wrong_url}"

        new_entry.external_url = wrong_url

        await catalog_entries([new_entry])

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
