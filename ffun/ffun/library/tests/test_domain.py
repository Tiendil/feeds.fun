import datetime

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from ffun.core import utils
from ffun.core.postgresql import execute
from ffun.feeds.entities import Feed
from ffun.library import operations
from ffun.library.domain import get_entries_by_filter_with_fallback, get_entry, get_feeds_for_entry, normalize_entry, shrink_feed
from ffun.library.entities import CollectedEntry, Entry, EntryChange
from ffun.library.settings import settings
from ffun.library.tests import helpers, make


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
        self, new_entry: CollectedEntry, loaded_feed: Feed, another_loaded_feed: Feed, apply: bool
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
    async def test_single_feed(self, new_entry: CollectedEntry, loaded_feed: Feed) -> None:
        await operations.catalog_entries(loaded_feed.id, [new_entry])

        feeds = await get_feeds_for_entry(new_entry.id)

        assert feeds == {loaded_feed.id}

    @pytest.mark.asyncio
    async def test_multiple_feed(
        self, new_entry: CollectedEntry, loaded_feed: Feed, another_loaded_feed: Feed
    ) -> None:
        await operations.catalog_entries(loaded_feed.id, [new_entry])
        await operations.catalog_entries(another_loaded_feed.id, [new_entry])

        feeds = await get_feeds_for_entry(new_entry.id)

        assert feeds == {loaded_feed.id, another_loaded_feed.id}

    @pytest.mark.asyncio
    async def test_no_feeds(self, new_entry: CollectedEntry, loaded_feed: Feed) -> None:
        await operations.catalog_entries(loaded_feed.id, [new_entry])

        await execute("DELETE FROM l_feeds_to_entries WHERE feed_id = %(feed_id)s AND entry_id = %(entry_id)s", {
            "feed_id": loaded_feed.id,
            "entry_id": new_entry.id,
        })

        feeds = await get_feeds_for_entry(new_entry.id)

        assert feeds == set()


# get_entries_by_filter_with_fallback uses get_entries_by_filter
# so, we may test only fallback logic
class TestGetEntriesByFilterWithFallback:

    @pytest.fixture  # type: ignore
    def time_delta(self) -> datetime.timedelta:
        return datetime.timedelta(days=1)

    @pytest.fixture  # type: ignore
    def time_border(self, time_delta: datetime.timedelta) -> datetime.datetime:
        return utils.now() - time_delta

    @pytest_asyncio.fixture  # type: ignore
    async def prepared_entries(self, loaded_feed: Feed, time_border: datetime.datetime) -> list[Entry]:
        entries = await make.n_entries_list(loaded_feed, n=3)

        await helpers.update_links_created_time(
            loaded_feed.id, [entry.id for entry in entries], time_border - datetime.timedelta(seconds=10)
        )

        all_entries = await operations.get_entries_by_ids(ids=[entry.id for entry in entries])

        all_entries_list = [entry for entry in all_entries.values() if entry is not None]
        all_entries_list.sort(key=lambda entry: entry.published_at)

        return all_entries_list

    @pytest.mark.asyncio
    async def test_no_entries_at_all(self, time_delta: datetime.timedelta) -> None:
        entries = await get_entries_by_filter_with_fallback(
            feeds_ids=[], period=time_delta, limit=10, fallback_limit=10
        )

        assert entries == []

    @pytest.mark.asyncio
    async def test_has_new_entries(
        self, loaded_feed: Feed, time_border: datetime.datetime, time_delta: datetime.timedelta
    ) -> None:
        entries = await make.n_entries_list(loaded_feed, n=3)

        await helpers.update_link_created_time(loaded_feed.id, entries[-1].id, time_border - datetime.timedelta(seconds=10))

        loaded_entries = await get_entries_by_filter_with_fallback(
            feeds_ids=[loaded_feed.id], period=time_delta, limit=10, fallback_limit=10
        )

        assert {entry.id for entry in loaded_entries} == {entry.id for entry in entries if entry.id != entries[-1].id}

    @pytest.mark.asyncio
    async def test_has_new_entries__limit(
        self, loaded_feed: Feed, time_border: datetime.datetime, time_delta: datetime.timedelta
    ) -> None:
        entries = await make.n_entries_list(loaded_feed, n=3)

        await helpers.update_link_created_time(loaded_feed.id, entries[-1].id, time_border - datetime.timedelta(seconds=10))

        loaded_entries = await get_entries_by_filter_with_fallback(
            feeds_ids=[loaded_feed.id], period=time_delta, limit=1, fallback_limit=10
        )

        assert len(loaded_entries) == 1
        assert loaded_entries[0].id in {entry.id for entry in entries if entry.id != entries[-1].id}

    @pytest.mark.asyncio
    async def test_no_new_entries(
        self, loaded_feed: Feed, time_border: datetime.datetime, time_delta: datetime.timedelta
    ) -> None:
        entries = await make.n_entries_list(loaded_feed, n=3)

        await helpers.update_links_created_time(
            loaded_feed.id, [entry.id for entry in entries], time_border - datetime.timedelta(seconds=10)
        )

        loaded_entries = await get_entries_by_filter_with_fallback(
            feeds_ids=[loaded_feed.id], period=time_delta, limit=1, fallback_limit=10
        )

        assert {entry.id for entry in loaded_entries} == {entry.id for entry in entries}

    @pytest.mark.asyncio
    async def test_fallback_returns_entries_older_than_max_entry_age(
        self, loaded_feed: Feed, time_delta: datetime.timedelta
    ) -> None:
        entries = await make.n_entries_list(loaded_feed, n=3)

        await helpers.update_links_created_time(
            loaded_feed.id,
            [entry.id for entry in entries],
            utils.now() - settings.max_entry_age - datetime.timedelta(days=1),
        )

        loaded_entries = await get_entries_by_filter_with_fallback(
            feeds_ids=[loaded_feed.id], period=time_delta, limit=1, fallback_limit=10
        )

        assert {entry.id for entry in loaded_entries} == {entry.id for entry in entries}

    @pytest.mark.asyncio
    async def test_no_new_entries__limit(
        self, loaded_feed: Feed, time_border: datetime.datetime, time_delta: datetime.timedelta
    ) -> None:
        entries = await make.n_entries_list(loaded_feed, n=3)

        await helpers.update_links_created_time(
            loaded_feed.id, [entry.id for entry in entries], time_border - datetime.timedelta(seconds=10)
        )

        loaded_entries = await get_entries_by_filter_with_fallback(
            feeds_ids=[loaded_feed.id], period=time_delta, limit=1, fallback_limit=1
        )

        assert len(loaded_entries) == 1
        assert loaded_entries[0].id in {entry.id for entry in entries}


class TestShrinkFeed:
    @pytest.mark.asyncio
    async def test_all_required_methods_called(self, mocker: MockerFixture, loaded_feed: Feed) -> None:
        unlink_feed_tail = mocker.patch("ffun.library.operations.unlink_feed_tail", return_value={1, 2})
        unlink_old_entries = mocker.patch("ffun.library.operations.unlink_old_entries", return_value={2, 3})
        try_mark_as_orphanes = mocker.patch("ffun.library.operations.try_mark_as_orphanes")

        await shrink_feed(loaded_feed.id)

        unlink_feed_tail.assert_called_once()  # type: ignore
        unlink_old_entries.assert_called_once()  # type: ignore
        try_mark_as_orphanes.assert_called_once()  # type: ignore

        assert unlink_feed_tail.call_args.args[1] == loaded_feed.id  # type: ignore
        assert unlink_old_entries.call_args.args[1] == loaded_feed.id  # type: ignore
        assert try_mark_as_orphanes.call_args.args[1] == {1, 2, 3}  # type: ignore
