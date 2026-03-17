import datetime
import uuid
from itertools import chain
from unittest import mock
from pytest_mock import MockerFixture

import psycopg
import pytest
import pytest_asyncio
from structlog.testing import capture_logs

from ffun.core import utils
from ffun.core.postgresql import execute
from ffun.core.tests.helpers import Delta, TableSizeDelta, TableSizeNotChanged, assert_logs, assert_times_is_near
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import EntryId, FeedId
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed
from ffun.feeds.tests import make as f_make
from ffun.library import errors
from ffun.library.domain import get_entry
from ffun.library.entities import CollectedEntry, Entry, FeedEntryLink
from ffun.library.operations import (
    _catalog_entry,
    all_entries_iterator,
    catalog_entries,
    count_total_entries,
    get_entries_after_pointer,
    get_entries_by_filter,
    get_entries_by_ids,
    get_feed_links_for_entries,
    get_last_ingested_at,
    get_orphaned_entries,
    remove_entries_by_ids,
    sync_orphaned_entries,
    try_mark_as_orphanes,
    unlink_feed_tail,
    unlink_old_entries,
    update_external_url,
)
from ffun.library.settings import settings
from ffun.library.tests import helpers, make


def _feed_entry_link_created_at(link: FeedEntryLink) -> datetime.datetime:
    return link.created_at


def _collected_entry_published_at(entry: CollectedEntry) -> datetime.datetime:
    return entry.published_at


class TestCatalogEntry:

    @pytest.mark.asyncio
    async def test_new_entry_new_feed(self, loaded_feed_id: FeedId, new_entry: CollectedEntry) -> None:
        ingested_at = utils.now()

        async with TableSizeDelta("l_entries", delta=1):
            async with TableSizeDelta("l_feeds_to_entries", delta=1):
                assert await _catalog_entry(loaded_feed_id, new_entry, ingested_at)

        loaded_entry = await get_entry(new_entry.id)

        assert_times_is_near(loaded_entry.created_at, utils.now())
        assert loaded_entry == new_entry.fake_entry(loaded_entry.created_at)

        links = await get_feed_links_for_entries(execute, [new_entry.id])

        assert len(links[new_entry.id]) == 1

        link = links[new_entry.id][0]

        assert link.feed_id == loaded_feed_id
        assert link.entry_id == new_entry.id
        assert link.published_at == ingested_at
        assert_times_is_near(link.created_at, utils.now())

    @pytest.mark.asyncio
    async def test_same_entry_new_feed(
        self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId, new_entry: CollectedEntry
    ) -> None:
        second_ingested_at = utils.now()
        first_ingested_at = second_ingested_at - datetime.timedelta(minutes=1)

        await _catalog_entry(loaded_feed_id, new_entry, first_ingested_at)

        async with TableSizeNotChanged("l_entries"):
            async with TableSizeDelta("l_feeds_to_entries", delta=1):
                assert not await _catalog_entry(another_loaded_feed_id, new_entry, second_ingested_at)

        loaded_entry = await get_entry(new_entry.id)

        assert_times_is_near(loaded_entry.created_at, utils.now())
        assert loaded_entry == new_entry.fake_entry(loaded_entry.created_at)

        links = await get_feed_links_for_entries(execute, [new_entry.id])

        assert len(links[new_entry.id]) == 2

        sorted_links = sorted(links[new_entry.id], key=_feed_entry_link_created_at)

        link_1 = sorted_links[0]

        assert link_1.feed_id == loaded_feed_id
        assert link_1.entry_id == new_entry.id
        assert link_1.published_at == first_ingested_at
        assert_times_is_near(link_1.created_at, utils.now())

        link_2 = sorted_links[1]

        assert link_2.feed_id == another_loaded_feed_id
        assert link_2.entry_id == new_entry.id
        assert link_2.published_at == second_ingested_at
        assert_times_is_near(link_2.created_at, utils.now())

        assert link_1.created_at < link_2.created_at

    @pytest.mark.asyncio
    async def test_same_entry_same_feed(self, loaded_feed_id: FeedId, new_entry: CollectedEntry) -> None:
        second_ingested_at = utils.now()
        first_ingested_at = second_ingested_at - datetime.timedelta(minutes=1)

        await _catalog_entry(loaded_feed_id, new_entry, first_ingested_at)
        initial_links = await get_feed_links_for_entries(execute, [new_entry.id])
        initial_link = initial_links[new_entry.id][0]

        async with TableSizeNotChanged("l_entries"):
            async with TableSizeNotChanged("l_feeds_to_entries"):
                assert not await _catalog_entry(loaded_feed_id, new_entry, second_ingested_at)

        loaded_entry = await get_entry(new_entry.id)

        assert_times_is_near(loaded_entry.created_at, utils.now())
        assert loaded_entry == new_entry.fake_entry(loaded_entry.created_at)

        links = await get_feed_links_for_entries(execute, [new_entry.id])

        assert len(links[new_entry.id]) == 1

        link = links[new_entry.id][0]

        assert link.feed_id == loaded_feed_id
        assert link.entry_id == new_entry.id
        assert link.published_at == second_ingested_at
        assert link.created_at == initial_link.created_at

    @pytest.mark.asyncio
    async def test_do_not_update_entry_published_at_for_same_entry_same_feed(
        self, loaded_feed_id: FeedId, new_entry: CollectedEntry
    ) -> None:
        second_ingested_at = utils.now()
        first_ingested_at = second_ingested_at - datetime.timedelta(hours=1)

        await _catalog_entry(loaded_feed_id, new_entry, first_ingested_at)

        new_published_at = new_entry.published_at + datetime.timedelta(hours=1)
        updated_entry = new_entry.replace(published_at=new_published_at)

        async with TableSizeNotChanged("l_entries"):
            async with TableSizeNotChanged("l_feeds_to_entries"):
                assert not await _catalog_entry(loaded_feed_id, updated_entry, second_ingested_at)

        loaded_entry = await get_entry(new_entry.id)

        assert loaded_entry.published_at == new_entry.published_at

    @pytest.mark.asyncio
    async def test_do_not_update_entry_published_at_for_same_entry_new_feed(
        self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId, new_entry: CollectedEntry
    ) -> None:
        second_ingested_at = utils.now()
        first_ingested_at = second_ingested_at - datetime.timedelta(hours=1)

        await _catalog_entry(loaded_feed_id, new_entry, first_ingested_at)

        new_published_at = new_entry.published_at + datetime.timedelta(hours=1)
        updated_entry = new_entry.replace(published_at=new_published_at)

        async with TableSizeNotChanged("l_entries"):
            async with TableSizeDelta("l_feeds_to_entries", delta=1):
                assert not await _catalog_entry(another_loaded_feed_id, updated_entry, second_ingested_at)

        loaded_entry = await get_entry(new_entry.id)

        assert loaded_entry.published_at == new_entry.published_at

    @pytest.mark.asyncio
    async def test_new_entry_same_feed(
        self, loaded_feed_id: FeedId, new_entry: CollectedEntry, another_new_entry: CollectedEntry
    ) -> None:
        second_ingested_at = utils.now()
        first_ingested_at = second_ingested_at - datetime.timedelta(minutes=1)

        await _catalog_entry(loaded_feed_id, new_entry, first_ingested_at)

        async with TableSizeDelta("l_entries", delta=1):
            async with TableSizeDelta("l_feeds_to_entries", delta=1):
                assert await _catalog_entry(loaded_feed_id, another_new_entry, second_ingested_at)

        loaded_another_entry = await get_entry(another_new_entry.id)

        assert_times_is_near(loaded_another_entry.created_at, utils.now())
        assert loaded_another_entry == another_new_entry.fake_entry(loaded_another_entry.created_at)

        links = await get_feed_links_for_entries(execute, [another_new_entry.id])

        assert len(links[another_new_entry.id]) == 1

        link = links[another_new_entry.id][0]

        assert link.feed_id == loaded_feed_id
        assert link.entry_id == another_new_entry.id
        assert link.published_at == second_ingested_at
        assert_times_is_near(link.created_at, utils.now())

class TestCatalogEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self, loaded_feed_id: FeedId) -> None:
        async with TableSizeNotChanged("l_entries"):
            count = await catalog_entries(loaded_feed_id, [])
            assert count == 0

    @pytest.mark.asyncio
    async def test_success(
        self, loaded_feed_id: FeedId, new_entry: CollectedEntry, another_new_entry: CollectedEntry
    ) -> None:
        entries_data = [new_entry, another_new_entry]

        async with TableSizeDelta("l_entries", delta=2):
            count = await catalog_entries(loaded_feed_id, entries_data)
            assert count == 2

        loaded_entries = await get_entries_by_ids(ids=[new_entry.id, another_new_entry.id])

        loaded_new_entry = loaded_entries[new_entry.id]
        loaded_another_new_entry = loaded_entries[another_new_entry.id]

        assert len(loaded_entries) == 2

        assert loaded_new_entry is not None
        assert loaded_another_new_entry is not None

        assert_times_is_near(loaded_new_entry.created_at, utils.now())
        assert_times_is_near(loaded_another_new_entry.created_at, utils.now())

        # test that entries saved in reversed order
        assert loaded_new_entry.created_at > loaded_another_new_entry.created_at

        assert loaded_new_entry == new_entry.fake_entry(loaded_new_entry.created_at)
        assert loaded_another_new_entry == another_new_entry.fake_entry(loaded_another_new_entry.created_at)

    @pytest.mark.asyncio
    async def test_count_only_new_entries(self, loaded_feed_id: FeedId, new_entry: CollectedEntry) -> None:
        await _catalog_entry(loaded_feed_id, new_entry, utils.now())

        another_new_entry = new_entry.replace(id=new_entry_id(), external_id=uuid.uuid4().hex)

        async with TableSizeDelta("l_entries", delta=1):
            count = await catalog_entries(loaded_feed_id, [new_entry, another_new_entry])
            assert count == 1

    @pytest.mark.asyncio
    async def test_catalog_old_entries(
        self, loaded_feed: Feed, new_entry: CollectedEntry, another_new_entry: CollectedEntry
    ) -> None:
        await make.n_entries(loaded_feed, n=settings.min_entries_per_feed + 1)

        old_entry = new_entry.replace(
            published_at=utils.now() - settings.max_entry_age - datetime.timedelta(seconds=1)
        )

        async with TableSizeDelta("l_entries", delta=2):
            count = await catalog_entries(loaded_feed.id, [old_entry, another_new_entry])
            assert count == 2

        loaded_entries = await get_entries_by_ids(ids=[old_entry.id, another_new_entry.id])

        assert loaded_entries[old_entry.id] is not None
        assert loaded_entries[another_new_entry.id] is not None

    @pytest.mark.asyncio
    async def test_catalog_all_old_entries_even_above_min_entries_border(self, loaded_feed: Feed) -> None:
        await make.n_entries(loaded_feed, n=settings.min_entries_per_feed - 2)

        old_entries = [
            make.fake_entry(
                loaded_feed.source_id,
                published_at=utils.now() - settings.max_entry_age - datetime.timedelta(minutes=index + 1),
            )
            for index in range(5)
        ]

        async with TableSizeDelta("l_entries", delta=5):
            count = await catalog_entries(loaded_feed.id, old_entries)
            assert count == 5

        loaded_entries = await get_entries_by_ids(ids=[entry.id for entry in old_entries])

        for entry in old_entries:
            assert loaded_entries[entry.id] is not None

    @pytest.mark.asyncio
    async def test_catalog_old_entries_at_min_entries_border(self, loaded_feed: Feed) -> None:
        await make.n_entries(loaded_feed, n=settings.min_entries_per_feed)

        old_entries = [
            make.fake_entry(
                loaded_feed.source_id,
                published_at=utils.now() - settings.max_entry_age - datetime.timedelta(minutes=index + 1),
            )
            for index in range(3)
        ]

        async with TableSizeDelta("l_entries", delta=3):
            count = await catalog_entries(loaded_feed.id, old_entries)
            assert count == 3

        loaded_entries = await get_entries_by_ids(ids=[entry.id for entry in old_entries])

        for entry in old_entries:
            assert loaded_entries[entry.id] is not None


# Most of the functionality is tested in the tests for catalog_entry and other functions
class TestGetLastIngestedAt:

    @pytest.mark.asyncio
    async def test_no_entries(self, loaded_feed_id: FeedId) -> None:
        assert await get_last_ingested_at(execute, loaded_feed_id) is None

    @pytest.mark.asyncio
    async def test_returns_max_ingested_at_for_requested_feed(
        self, loaded_feed: Feed, another_loaded_feed: Feed
    ) -> None:
        first_entry = make.fake_entry(loaded_feed.source_id)
        second_entry = make.fake_entry(another_loaded_feed.source_id)
        third_entry = make.fake_entry(loaded_feed.source_id)

        await catalog_entries(loaded_feed.id, [first_entry])
        await catalog_entries(another_loaded_feed.id, [second_entry])
        await catalog_entries(loaded_feed.id, [third_entry])

        links = await get_feed_links_for_entries(execute, [first_entry.id, third_entry.id])
        expected_ingested_at = max(link.published_at for feed_links in links.values() for link in feed_links)

        assert await get_last_ingested_at(execute, loaded_feed.id) == expected_ingested_at


class TestGetFeedLinksForEntries:

    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        assert await get_feed_links_for_entries(execute, []) == {}


class TestGetEntriesByIds:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        entries = await get_entries_by_ids(ids=[])
        assert entries == {}

    @pytest.mark.asyncio
    async def test_success(self, loaded_feed: Feed, another_loaded_feed: Feed) -> None:
        entries = await make.n_entries(loaded_feed, n=3)
        another_entries = await make.n_entries(another_loaded_feed, n=3)

        entries_list = list(entries.values())
        another_entries_list = list(another_entries.values())

        entries_to_load = [*entries_list[:2], *another_entries_list[:2]]

        loaded_entries = await get_entries_by_ids(ids=[entry.id for entry in entries_to_load])

        assert len(loaded_entries) == 4
        assert entries_to_load[0] == loaded_entries[entries_to_load[0].id]
        assert entries_to_load[1] == loaded_entries[entries_to_load[1].id]
        assert another_entries_list[0] == loaded_entries[another_entries_list[0].id]
        assert another_entries_list[1] == loaded_entries[another_entries_list[1].id]


class TestGetEntriesByFilter:
    @pytest.fixture  # type: ignore
    def time_border(self) -> datetime.datetime:
        return utils.now() - datetime.timedelta(days=1)

    @pytest_asyncio.fixture  # type: ignore
    async def prepared_entries(
        self, loaded_feed: Feed, another_loaded_feed: Feed, time_border: datetime.datetime
    ) -> tuple[list[Entry], list[Entry]]:
        entries = await make.n_entries_list(loaded_feed, n=3)
        another_entries = await make.n_entries_list(another_loaded_feed, n=3)

        common_entry = make.fake_entry(loaded_feed.source_id)
        await catalog_entries(loaded_feed.id, [common_entry])
        await catalog_entries(another_loaded_feed.id, [common_entry])
        old_time = time_border - datetime.timedelta(seconds=10)

        await helpers.update_link_created_time(loaded_feed.id, entries[0].id, old_time)
        await helpers.update_link_created_time(another_loaded_feed.id, another_entries[0].id, old_time)

        all_entries = await get_entries_by_ids(ids=[entry.id for entry in chain(entries, another_entries, [common_entry])])
        all_links = await get_feed_links_for_entries(execute, [entry.id for entry in chain(entries, another_entries, [common_entry])])

        def entry_for_feed(feed_id: FeedId, entry_id: EntryId) -> Entry:
            entry = all_entries[entry_id]
            assert entry is not None

            for link in all_links[entry_id]:
                if link.feed_id == feed_id:
                    return entry.replace(created_at=link.created_at)

            raise NotImplementedError()

        entries_1 = [entry_for_feed(loaded_feed.id, entry.id) for entry in entries]
        entries_1.append(entry_for_feed(loaded_feed.id, common_entry.id))

        entries_2 = [entry_for_feed(another_loaded_feed.id, entry.id) for entry in another_entries]
        entries_2.append(entry_for_feed(another_loaded_feed.id, common_entry.id))

        entries_1.sort(key=lambda entry: entry.created_at)
        entries_2.sort(key=lambda entry: entry.created_at)

        return (entries_1, entries_2)

    @pytest.mark.asyncio
    async def test_all(
        self,
        loaded_feed_id: FeedId,
        another_loaded_feed_id: FeedId,
        prepared_entries: tuple[list[Entry], list[Entry]],
    ) -> None:
        loaded_entries = await get_entries_by_filter(feeds_ids=[loaded_feed_id, another_loaded_feed_id], limit=100)

        loaded_entries_ids = {entry.id for entry in loaded_entries}
        assert loaded_entries_ids == {entry.id for entry in chain(*prepared_entries)}

    @pytest.mark.asyncio
    async def test_limit(
        self,
        loaded_feed_id: FeedId,
        another_loaded_feed_id: FeedId,
        prepared_entries: tuple[list[Entry], list[Entry]],
    ) -> None:
        loaded_entries = await get_entries_by_filter(feeds_ids=[loaded_feed_id, another_loaded_feed_id], limit=5)

        loaded_entries_ids = {entry.id for entry in loaded_entries}
        assert loaded_entries_ids == {entry.id for entry in chain(prepared_entries[0][1:], prepared_entries[1][1:])}

    @pytest.mark.asyncio
    async def test_feeds_filter(
        self, loaded_feed_id: FeedId, prepared_entries: tuple[list[Entry], list[Entry]]
    ) -> None:
        loaded_entries = await get_entries_by_filter(feeds_ids=[loaded_feed_id], limit=100)
        loaded_entries_ids = {entry.id for entry in loaded_entries}
        assert loaded_entries_ids == {entry.id for entry in prepared_entries[0]}

    @pytest.mark.asyncio
    async def test_time_period(
        self,
        loaded_feed_id: FeedId,
        another_loaded_feed_id: FeedId,
        prepared_entries: tuple[list[Entry], list[Entry]],
    ) -> None:
        loaded_entries = await get_entries_by_filter(
            feeds_ids=[loaded_feed_id, another_loaded_feed_id], limit=100, period=datetime.timedelta(days=1)
        )

        loaded_entries_ids = {entry.id for entry in loaded_entries}
        assert loaded_entries_ids == {entry.id for entry in chain(prepared_entries[0][1:], prepared_entries[1][1:])}

    @pytest.mark.asyncio
    async def test_default_period_uses_max_entry_age(self, loaded_feed: Feed) -> None:
        entries = await make.n_entries_list(loaded_feed, n=3)

        old_time = utils.now() - settings.max_entry_age - datetime.timedelta(seconds=1)

        await helpers.update_link_created_time(loaded_feed.id, entries[0].id, old_time)

        loaded_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100)

        assert {entry.id for entry in loaded_entries} == {entries[1].id, entries[2].id}

    @pytest.mark.asyncio
    async def test_uses_feed_specific_created_at_for_shared_entry(
        self, loaded_feed: Feed, another_loaded_feed: Feed
    ) -> None:
        entry_published_at = utils.now() - datetime.timedelta(hours=1)
        common_entry = make.fake_entry(loaded_feed.source_id, published_at=entry_published_at)

        await catalog_entries(loaded_feed.id, [common_entry])
        await catalog_entries(another_loaded_feed.id, [common_entry])

        loaded_entry = await get_entry(common_entry.id)

        assert loaded_entry.published_at == entry_published_at

        feed_created_at = utils.now() - datetime.timedelta(days=2)
        another_feed_created_at = utils.now() - datetime.timedelta(minutes=10)

        await helpers.update_link_created_time(loaded_feed.id, common_entry.id, feed_created_at)
        await helpers.update_link_created_time(another_loaded_feed.id, common_entry.id, another_feed_created_at)

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100)
        another_feed_entries = await get_entries_by_filter(feeds_ids=[another_loaded_feed.id], limit=100)
        combined_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id, another_loaded_feed.id], limit=100)

        assert len(feed_entries) == 1
        assert len(another_feed_entries) == 1
        assert len(combined_entries) == 1

        assert feed_entries[0].id == common_entry.id
        assert another_feed_entries[0].id == common_entry.id
        assert combined_entries[0].id == common_entry.id

        assert feed_entries[0].published_at == feed_created_at
        assert another_feed_entries[0].published_at == another_feed_created_at
        assert combined_entries[0].published_at == feed_created_at

    @pytest.mark.asyncio
    async def test_order_by_published_at_created_at_and_entry_id(self, loaded_feed: Feed) -> None:
        published_at = utils.now() - datetime.timedelta(hours=1)
        entries: list[CollectedEntry] = [
            make.fake_entry(loaded_feed.source_id, published_at=published_at) for _ in range(4)
        ]

        await catalog_entries(loaded_feed.id, entries)

        created_ats: dict[EntryId, datetime.datetime] = {
            entries[0].id: utils.now() - datetime.timedelta(minutes=3),
            entries[1].id: utils.now() - datetime.timedelta(minutes=1),
            entries[2].id: utils.now() - datetime.timedelta(minutes=2),
            entries[3].id: utils.now() - datetime.timedelta(minutes=2),
        }

        for entry in entries:
            await helpers.update_link_created_time(loaded_feed.id, entry.id, created_ats[entry.id])

        loaded_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100)

        def sort_key(entry: CollectedEntry) -> tuple[datetime.datetime, datetime.datetime, EntryId]:
            return published_at, created_ats[entry.id], entry.id

        expected_order = sorted(entries, key=sort_key, reverse=True)

        assert [entry.id for entry in loaded_entries] == [entry.id for entry in expected_order]


class TestGetEntriesAfterPointer:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        entries = await get_entries_after_pointer(created_at=utils.now(), entry_id=new_entry_id(), limit=100)
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_some(self, loaded_feed: Feed) -> None:
        enries = await make.n_entries(loaded_feed, n=5)

        entries_list = list(enries.values())
        entries_list.sort(key=lambda entry: (entry.created_at, entry.id))

        loaded_entries = await get_entries_after_pointer(
            created_at=entries_list[2].created_at, entry_id=entries_list[2].id, limit=100
        )

        assert [(entry.id, entry.created_at) for entry in entries_list[3:]] == loaded_entries

    @pytest.mark.asyncio
    async def test_duplicated_created_at(self, loaded_feed: Feed) -> None:
        entries = await make.n_entries(loaded_feed, n=5)

        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.created_at, entry.id))
        base_time = entries_list[1].created_at

        await execute(
            "UPDATE l_entries SET created_at = %(created_at)s WHERE id = ANY(%(ids)s)",
            {"created_at": base_time, "ids": [entry.id for entry in entries_list[1:5]]},  # type: ignore
        )

        entries = await get_entries_by_ids(ids=[entry.id for entry in entries_list])  # type: ignore
        entries_list = [entry for entry in entries.values() if entry is not None]
        entries_list.sort(key=lambda entry: (entry.created_at, entry.id))

        for i in range(1, 4):
            loaded_entries = await get_entries_after_pointer(
                created_at=base_time, entry_id=entries_list[i].id, limit=100
            )

            assert [(entry.id, entry.created_at) for entry in entries_list[i + 1 :]] == loaded_entries

    @pytest.mark.asyncio
    async def test_limit(self, loaded_feed: Feed) -> None:
        entries = await make.n_entries(loaded_feed, n=5)

        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.created_at, entry.id))

        loaded_entries = await get_entries_after_pointer(
            created_at=entries_list[2].created_at, entry_id=entries_list[2].id, limit=2
        )

        assert [(entry.id, entry.created_at) for entry in entries_list[3:5]] == loaded_entries


class TestAllEntriesIterator:
    @pytest.mark.parametrize("chunk", [1, 2, 3, 4, 5, 6, 7])
    @pytest.mark.asyncio
    async def test(self, chunk: int) -> None:
        feed_1_data = await f_make.fake_feed()
        feed_1_id = await f_domain.save_feed(feed_1_data)

        feed_2_data = await f_make.fake_feed()
        feed_2_id = await f_domain.save_feed(feed_2_data)

        entries_1_data = [make.fake_entry(feed_1_data.source_id) for _ in range(3)]
        entries_2_data = [make.fake_entry(feed_2_data.source_id) for _ in range(3)]

        await catalog_entries(feed_1_id, entries_1_data)
        await catalog_entries(feed_2_id, entries_2_data)

        ids = [e.id for e in chain(entries_1_data, entries_2_data)]

        ids.sort()

        found_ids = [entry.id async for entry in all_entries_iterator(chunk=chunk) if entry.id in ids]

        assert found_ids == ids


class TestUpdateExternalUrl:
    @pytest.mark.asyncio
    async def test(self, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        new_url = make.fake_url()

        assert cataloged_entry.external_url != new_url

        await update_external_url(cataloged_entry.id, new_url)

        loaded_entry = await get_entry(cataloged_entry.id)
        assert loaded_entry.external_url == new_url

        loaded_another_entry = await get_entry(another_cataloged_entry.id)
        assert loaded_another_entry.external_url == another_cataloged_entry.external_url


class TestUnlinkFeedTail:

    @pytest.mark.asyncio
    async def test_too_short_head(self, loaded_feed: Feed) -> None:
        with pytest.raises(errors.FeedHeadIsTooShort):
            await unlink_feed_tail(execute, loaded_feed.id, offset=settings.min_entries_per_feed - 1)

    @pytest.mark.asyncio
    async def test_respect_last_ingestion(self, loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 3

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)

        await catalog_entries(loaded_feed.id, entries[:keep_entries])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_feed_tail(execute, loaded_feed.id, offset=min_entries)

        assert unlinked == {entry.id for entry in entries[min_entries + 3 :]}

        assert_logs(logs, feed_has_no_entries_tail=0, feed_entries_tail_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)
        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:min_entries + 3]}

    @pytest.mark.asyncio
    async def test_respect_offset(self, loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 3

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)

        await catalog_entries(loaded_feed.id, entries[:min_entries])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_feed_tail(execute, loaded_feed.id, offset=min_entries + 3)

        assert unlinked == {entry.id for entry in entries[min_entries + 3 :]}

        assert_logs(logs, feed_has_no_entries_tail=0, feed_entries_tail_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)

        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:min_entries + 3]}

    @pytest.mark.asyncio
    async def test_default_offset(self, loaded_feed: Feed, mocker: MockerFixture) -> None:
        min_entries = settings.min_entries_per_feed

        expected_offset = min_entries + 2

        mocker.patch("ffun.library.settings.settings.max_entries_per_feed", expected_offset)

        entries = await make.n_entries_list(loaded_feed, n=min_entries + 5)

        await catalog_entries(loaded_feed.id, entries[:min_entries])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-3):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_feed_tail(execute, loaded_feed.id)

        assert unlinked == {entry.id for entry in entries[expected_offset:]}

    @pytest.mark.asyncio
    async def test_no_entries(self, loaded_feed: Feed) -> None:
        with capture_logs() as logs:
            async with TableSizeNotChanged("l_feeds_to_entries"):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_feed_tail(execute, loaded_feed.id)

        assert unlinked == set()

        assert_logs(logs, feed_has_no_entries=1, feed_entries_tail_removed=0)  # type: ignore

    @pytest.mark.asyncio
    async def test_less_than_min_entries(self, loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries - 3

        assert keep_entries > 2

        entries = await make.n_entries_list(loaded_feed, n=keep_entries)

        await catalog_entries(loaded_feed.id, entries[:-2])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeNotChanged("l_feeds_to_entries"):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_feed_tail(execute, loaded_feed.id, offset=min_entries)

        assert unlinked == set()

        assert_logs(logs, feed_has_no_entries_tail=1, feed_entries_tail_removed=0)

    @pytest.mark.asyncio
    async def test_respect_separate_feed(self, loaded_feed: Feed, another_loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 3

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)
        await catalog_entries(loaded_feed.id, entries[:min_entries])

        another_entries = await make.n_entries_list(another_loaded_feed, n=keep_entries + 5)
        await catalog_entries(another_loaded_feed.id, another_entries[:min_entries])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_feed_tail(execute, loaded_feed.id, offset=min_entries + 3)

        assert unlinked == {entry.id for entry in entries[min_entries + 3 :]}

        assert_logs(logs, feed_has_no_entries_tail=0, feed_entries_tail_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)
        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:min_entries + 3]}

        another_feed_entries = await get_entries_by_filter(feeds_ids=[another_loaded_feed.id], limit=100500)
        assert {entry.id for entry in another_feed_entries} == {entry.id for entry in another_entries}

    @pytest.mark.asyncio
    async def test_respect_neighbour_feed(self, loaded_feed: Feed, another_loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 3

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)
        await catalog_entries(loaded_feed.id, entries[:min_entries])

        await catalog_entries(another_loaded_feed.id, entries)
        await catalog_entries(another_loaded_feed.id, entries[:min_entries])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_feed_tail(execute, loaded_feed.id, offset=min_entries + 3)

        assert unlinked == {entry.id for entry in entries[min_entries + 3 :]}

        assert_logs(logs, feed_has_no_entries_tail=0, feed_entries_tail_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)
        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:min_entries + 3]}

        another_feed_entries = await get_entries_by_filter(feeds_ids=[another_loaded_feed.id], limit=100500)
        assert {entry.id for entry in another_feed_entries} == {entry.id for entry in entries}


class TestUnlinkOldEntries:

    @pytest.mark.asyncio
    async def test_no_entries(self, loaded_feed: Feed) -> None:
        with capture_logs() as logs:
            async with TableSizeNotChanged("l_feeds_to_entries"):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_old_entries(execute, loaded_feed.id)

        assert unlinked == set()

        assert_logs(logs, feed_has_no_entries=1, feed_has_no_old_entries=0)  # type: ignore

    @pytest.mark.asyncio
    async def test_no_old_entries(self, loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 3

        entries = await make.n_entries_list(loaded_feed, n=keep_entries)

        with capture_logs() as logs:  # type: ignore
            async with TableSizeNotChanged("l_feeds_to_entries"):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_old_entries(execute, loaded_feed.id, period=datetime.timedelta(days=1))

        assert unlinked == set()

        assert_logs(logs, feed_has_no_old_entries=1, feed_old_entries_removed=0)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)

        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries}

    @pytest.mark.asyncio
    async def test_respect_last_ingestion(self, loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 3

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)

        await catalog_entries(loaded_feed.id, entries[:keep_entries])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_old_entries(execute, loaded_feed.id, period=datetime.timedelta(days=0))

        assert unlinked == {entry.id for entry in entries[keep_entries:]}

        assert_logs(logs, feed_has_no_old_entries=0, feed_old_entries_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)

        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:keep_entries]}

    @pytest.mark.asyncio
    async def test_respect_min_entries(self, loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        last_ingested = min_entries - 3

        entries = await make.n_entries_list(loaded_feed, n=min_entries + 5)

        await catalog_entries(loaded_feed.id, entries[:last_ingested])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_old_entries(execute, loaded_feed.id, period=datetime.timedelta(days=0))

        assert unlinked == {entry.id for entry in entries[min_entries:]}

        assert_logs(logs, feed_has_no_old_entries=0, feed_old_entries_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)

        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:min_entries]}

    @pytest.mark.asyncio
    async def test_respect_period(self, loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 2

        now = utils.now()
        day = datetime.timedelta(days=1)

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)
        await catalog_entries(loaded_feed.id, entries[:min_entries])

        await helpers.update_link_created_time(loaded_feed.id, entries[-1].id, now - 5*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-2].id, now - 5*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-3].id, now - 3*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-4].id, now - 3*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-5].id, now - 3*day)

        await helpers.update_link_created_time(loaded_feed.id, entries[-6].id, now - 1*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-7].id, now - 1*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-8].id, now - 1*day)

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_old_entries(execute, loaded_feed.id, period=day * 2)

        assert unlinked == {entry.id for entry in entries[keep_entries:]}

        assert_logs(logs, feed_has_no_old_entries=0, feed_old_entries_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)

        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:keep_entries]}

    @pytest.mark.asyncio
    async def test_default_period(self, loaded_feed: Feed, mocker: MockerFixture) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 2

        now = utils.now()
        day = datetime.timedelta(days=1)

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)
        await catalog_entries(loaded_feed.id, entries[:min_entries])

        await helpers.update_link_created_time(loaded_feed.id, entries[-1].id, now - 5*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-2].id, now - 5*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-3].id, now - 3*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-4].id, now - 3*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-5].id, now - 3*day)

        await helpers.update_link_created_time(loaded_feed.id, entries[-6].id, now - 1*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-7].id, now - 1*day)
        await helpers.update_link_created_time(loaded_feed.id, entries[-8].id, now - 1*day)

        mocker.patch("ffun.library.settings.settings.max_entry_age", day * 2)

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_old_entries(execute, loaded_feed.id)

        assert unlinked == {entry.id for entry in entries[keep_entries:]}

        assert_logs(logs, feed_has_no_old_entries=0, feed_old_entries_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)

        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:keep_entries]}

    @pytest.mark.asyncio
    async def test_respect_separate_feed(self, loaded_feed: Feed, another_loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 3

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)
        await catalog_entries(loaded_feed.id, entries[:keep_entries])

        another_entries = await make.n_entries_list(another_loaded_feed, n=keep_entries + 5)
        await catalog_entries(another_loaded_feed.id, another_entries[:keep_entries])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_old_entries(execute, loaded_feed.id, period=datetime.timedelta(days=0))

        assert unlinked == {entry.id for entry in entries[keep_entries:]}

        assert_logs(logs, feed_has_no_old_entries=0, feed_old_entries_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)
        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:keep_entries]}

        another_feed_entries = await get_entries_by_filter(feeds_ids=[another_loaded_feed.id], limit=100500)
        assert {entry.id for entry in another_feed_entries} == {entry.id for entry in another_entries}

    @pytest.mark.asyncio
    async def test_respect_neighbour_feed(self, loaded_feed: Feed, another_loaded_feed: Feed) -> None:
        min_entries = settings.min_entries_per_feed
        keep_entries = min_entries + 3

        entries = await make.n_entries_list(loaded_feed, n=keep_entries + 5)
        await catalog_entries(loaded_feed.id, entries[:keep_entries])

        await catalog_entries(another_loaded_feed.id, entries)
        await catalog_entries(another_loaded_feed.id, entries[:keep_entries])

        with capture_logs() as logs:  # type: ignore
            async with TableSizeDelta("l_feeds_to_entries", delta=-5):
                async with TableSizeNotChanged("l_entries"):
                    unlinked = await unlink_old_entries(execute, loaded_feed.id, period=datetime.timedelta(days=0))

        assert unlinked == {entry.id for entry in entries[keep_entries:]}

        assert_logs(logs, feed_has_no_old_entries=0, feed_old_entries_removed=1)  # type: ignore

        feed_entries = await get_entries_by_filter(feeds_ids=[loaded_feed.id], limit=100500)
        assert {entry.id for entry in feed_entries} == {entry.id for entry in entries[:keep_entries]}

        another_feed_entries = await get_entries_by_filter(feeds_ids=[another_loaded_feed.id], limit=100500)
        assert {entry.id for entry in another_feed_entries} == {entry.id for entry in entries}


class TestRemoveEntriesByIds:

    @pytest.mark.asyncio
    async def test_no_entries_in_request(self) -> None:
        async with TableSizeNotChanged("l_orphaned_entries"):
            await remove_entries_by_ids(execute, [new_entry_id()])

    @pytest.mark.asyncio
    async def test_no_entries_to_remove(self) -> None:
        async with TableSizeNotChanged("l_orphaned_entries"):
            await remove_entries_by_ids(execute, [])

    @pytest.mark.asyncio
    async def test_remove(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("ffun.library.settings.settings.min_entries_per_feed", 6)

        entries = await make.n_entries_list(loaded_feed, n=10)

        await catalog_entries(
            another_loaded_feed.id,
            [entry.collected_entry() for entry in entries[2:7]],
        )
        await catalog_entries(loaded_feed.id, entries[:6])

        unlinked = await unlink_feed_tail(execute, loaded_feed.id, 6)
        await try_mark_as_orphanes(execute, unlinked)

        # 8 is orphaned
        # 6 is linked only to another_loaded_feed
        # 4,5 are linked to both feeds
        # 0 is linked only to loaded_feed

        entries_to_remove = [entries[0].id, entries[4].id, entries[5].id, entries[6].id, entries[8].id]

        async with TableSizeDelta("l_orphaned_entries", delta=-1):
            async with TableSizeDelta("l_feeds_to_entries", delta=-6):
                async with TableSizeDelta("l_entries", delta=-5):
                    await remove_entries_by_ids(execute, entries_to_remove)

    @pytest.mark.asyncio
    async def test_raise_concurent_operation_on_removed_entries(self) -> None:
        execute_mock = mock.AsyncMock(side_effect=psycopg.errors.ForeignKeyViolation())
        entry_ids = [new_entry_id()]

        with pytest.raises(errors.ConcurentOperationOnRemovedEntries):
            await remove_entries_by_ids(execute_mock, entry_ids)


class TestGetOrphanedEntries:

    @pytest_asyncio.fixture(autouse=True)  # type: ignore
    async def cleanup_orphaned_entries(self) -> None:
        await execute("DELETE FROM l_orphaned_entries")

    @pytest.mark.asyncio
    async def test_no_orphaned_entries(self) -> None:
        assert await get_orphaned_entries(limit=100) == set()

    @pytest.mark.asyncio
    async def test_zero_limit(self) -> None:
        assert await get_orphaned_entries(limit=0) == set()

    @pytest.mark.asyncio
    async def test_orphaned_entries(self) -> None:
        ids = {new_entry_id(), new_entry_id()}
        await try_mark_as_orphanes(execute, ids)

        assert await get_orphaned_entries(limit=100) == ids

    @pytest.mark.asyncio
    async def test_limit(self) -> None:
        ids = {new_entry_id() for _ in range(10)}
        await try_mark_as_orphanes(execute, ids)

        orphaned_entries = await get_orphaned_entries(limit=2)

        assert len(orphaned_entries) == 2

        assert len(orphaned_entries & ids) == 2


class TestTryMarkAsOrphanes:

    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        async with TableSizeNotChanged("l_orphaned_entries"):
            await try_mark_as_orphanes(execute, [])

    @pytest.mark.asyncio
    async def test_no_orphanes_found(self, loaded_feed: Feed) -> None:
        entries = await make.n_entries_list(loaded_feed, n=3)

        async with TableSizeNotChanged("l_orphaned_entries"):
            await try_mark_as_orphanes(execute, [entry.id for entry in entries])

    @pytest.mark.asyncio
    async def test_orphanes_found(self, loaded_feed: Feed, mocker: MockerFixture) -> None:
        mocker.patch("ffun.library.settings.settings.min_entries_per_feed", 3)
        entries = await make.n_entries_list(loaded_feed, n=5)
        await catalog_entries(loaded_feed.id, entries[:3])

        await unlink_feed_tail(execute, loaded_feed.id, 3)

        async with TableSizeDelta("l_orphaned_entries", delta=2):
            await try_mark_as_orphanes(execute, [entry.id for entry in entries])

        orphaned_entries = await get_orphaned_entries(limit=100500)

        assert orphaned_entries & {entry.id for entry in entries} == {entry.id for entry in entries[3:]}


class TestSyncOrphanedEntries:

    @pytest.mark.asyncio
    async def test_no_orphaned_entries(self) -> None:
        async with TableSizeNotChanged("l_orphaned_entries"):
            await sync_orphaned_entries()

    @pytest.mark.asyncio
    async def test_keep_actual_orphaned_entries(self, loaded_feed: Feed, mocker: MockerFixture) -> None:
        mocker.patch("ffun.library.settings.settings.min_entries_per_feed", 3)
        entries = await make.n_entries_list(loaded_feed, n=5)
        await catalog_entries(loaded_feed.id, entries[:3])

        unlinked = await unlink_feed_tail(execute, loaded_feed.id, 3)
        await try_mark_as_orphanes(execute, unlinked)

        async with TableSizeNotChanged("l_orphaned_entries"):
            await sync_orphaned_entries()

        orphaned_entries = await get_orphaned_entries(limit=100500)

        assert orphaned_entries & {entry.id for entry in entries} == {entry.id for entry in entries[3:]}

    @pytest.mark.asyncio
    async def test_remove_no_longer_orphaned_entries(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("ffun.library.settings.settings.min_entries_per_feed", 3)
        entries = await make.n_entries_list(loaded_feed, n=5)
        await catalog_entries(loaded_feed.id, entries[:3])

        unlinked = await unlink_feed_tail(execute, loaded_feed.id, 3)
        await try_mark_as_orphanes(execute, unlinked)
        await catalog_entries(
            another_loaded_feed.id,
            [entries[3].collected_entry()],
        )

        async with TableSizeDelta("l_orphaned_entries", delta=-1):
            await sync_orphaned_entries()

        orphaned_entries = await get_orphaned_entries(limit=100500)

        assert orphaned_entries & {entry.id for entry in entries} == {entries[4].id}


class TestCountTotalEntries:

    @pytest.mark.asyncio
    async def test(self, loaded_feed: Feed) -> None:
        async with Delta(count_total_entries, delta=3):
            await make.n_entries_list(loaded_feed, n=3)
