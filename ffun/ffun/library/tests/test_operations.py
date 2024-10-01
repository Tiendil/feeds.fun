import datetime
import uuid
from itertools import chain

import pytest
import pytest_asyncio

from ffun.core import utils
from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_times_is_near
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import FeedId
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed
from ffun.feeds.tests import make as f_make
from ffun.library import errors
from ffun.library.domain import get_entry
from ffun.library.entities import Entry
from ffun.library.operations import (
    all_entries_iterator,
    catalog_entries,
    find_stored_entries_for_feed,
    get_entries_after_pointer,
    get_entries_by_filter,
    get_entries_by_ids,
    # tech_get_feed_entries_tail,
    # tech_move_entry,
    # tech_remove_entries_by_ids,
    update_external_url,
    _catalog_entry,
    get_feed_entry_links,
)
from ffun.library.tests import make


class TestCatalogEntry:

    @pytest.mark.asyncio
    async def test_new_entry_new_feed(self, loaded_feed_id: FeedId, new_entry: Entry) -> None:
        async with TableSizeDelta("l_entries", delta=1):
            async with TableSizeDelta("l_feeds_to_entries", delta=1):
                await _catalog_entry(loaded_feed_id, new_entry)

        loaded_entry = await get_entry(new_entry.id)

        assert_times_is_near(loaded_entry.cataloged_at, utils.now())

        assert loaded_entry == new_entry.replace(cataloged_at=loaded_entry.cataloged_at)

        links = await get_feed_entry_links([new_entry.id])

        assert len(links[new_entry.id]) == 1

        link = links[new_entry.id][0]

        assert link.feed_id == loaded_feed_id
        assert link.entry_id == new_entry.id
        assert_times_is_near(link.created_at, utils.now())

    @pytest.mark.asyncio
    async def test_same_entry_new_feed(self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId, new_entry: Entry) -> None:
        await _catalog_entry(loaded_feed_id, new_entry)

        async with TableSizeNotChanged("l_entries"):
            async with TableSizeDelta("l_feeds_to_entries", delta=1):
                await _catalog_entry(another_loaded_feed_id, new_entry)

        loaded_entry = await get_entry(new_entry.id)

        assert_times_is_near(loaded_entry.cataloged_at, utils.now())

        assert loaded_entry == new_entry.replace(cataloged_at=loaded_entry.cataloged_at)

        links = await get_feed_entry_links([new_entry.id])

        assert len(links[new_entry.id]) == 2

        link_1 = links[new_entry.id][0]

        assert link_1.feed_id == loaded_feed_id
        assert link_1.entry_id == new_entry.id
        assert_times_is_near(link_1.created_at, utils.now())

        link_2 = links[new_entry.id][1]

        assert link_2.feed_id == another_loaded_feed_id
        assert link_2.entry_id == new_entry.id
        assert_times_is_near(link_2.created_at, utils.now())

        assert link_1.created_at < link_2.created_at

    @pytest.mark.asyncio
    async def test_same_entry_same_feed(self, loaded_feed_id: FeedId, new_entry: Entry) -> None:
        await _catalog_entry(loaded_feed_id, new_entry)

        async with TableSizeNotChanged("l_entries"):
            async with TableSizeNotChanged("l_feeds_to_entries"):
                await _catalog_entry(loaded_feed_id, new_entry)

        loaded_entry = await get_entry(new_entry.id)

        assert_times_is_near(loaded_entry.cataloged_at, utils.now())

        assert loaded_entry == new_entry.replace(cataloged_at=loaded_entry.cataloged_at)

        links = await get_feed_entry_links([new_entry.id])

        assert len(links[new_entry.id]) == 1

        link = links[new_entry.id][0]

        assert link.feed_id == loaded_feed_id
        assert link.entry_id == new_entry.id
        assert_times_is_near(link.created_at, utils.now())

    @pytest.mark.asyncio
    async def test_new_entry_same_feed(self, loaded_feed_id: FeedId, new_entry: Entry, another_new_entry: Entry) -> None:
        await _catalog_entry(loaded_feed_id, new_entry)

        async with TableSizeDelta("l_entries", delta=1):
            async with TableSizeDelta("l_feeds_to_entries", delta=1):
                await _catalog_entry(loaded_feed_id, another_new_entry)

        loaded_another_entry = await get_entry(another_new_entry.id)

        assert_times_is_near(loaded_another_entry.cataloged_at, utils.now())

        assert loaded_another_entry == another_new_entry.replace(cataloged_at=loaded_another_entry.cataloged_at)

        links = await get_feed_entry_links([another_new_entry.id])

        assert len(links[another_new_entry.id]) == 1

        link = links[another_new_entry.id][0]

        assert link.feed_id == loaded_feed_id
        assert link.entry_id == another_new_entry.id
        assert_times_is_near(link.created_at, utils.now())


class TestCatalogEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self, loaded_feed_id: FeedId) -> None:
        async with TableSizeNotChanged("l_entries"):
            await catalog_entries(loaded_feed_id, [])

    @pytest.mark.asyncio
    async def test_success(self, loaded_feed_id: FeedId, new_entry: Entry, another_new_entry: Entry) -> None:
        entries_data = [new_entry, another_new_entry]

        async with TableSizeDelta("l_entries", delta=2):
            await catalog_entries(loaded_feed_id, entries_data)

        loaded_entries = await get_entries_by_ids(ids=[new_entry.id, another_new_entry.id])

        loaded_new_entry = loaded_entries[new_entry.id]
        loaded_another_new_entry = loaded_entries[another_new_entry.id]

        assert len(loaded_entries) == 2

        assert loaded_new_entry is not None
        assert loaded_another_new_entry is not None

        assert_times_is_near(loaded_new_entry.cataloged_at, utils.now())
        assert_times_is_near(loaded_another_new_entry.cataloged_at, utils.now())

        assert loaded_new_entry == new_entry.replace(cataloged_at=loaded_new_entry.cataloged_at)
        assert loaded_another_new_entry == another_new_entry.replace(
            cataloged_at=loaded_another_new_entry.cataloged_at
        )


# Most of the functionality is tested in the tests for catalog_entry and other functions
class TestGetFeedEntryLnks:

    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        assert await get_feed_entry_links([]) == {}


class TestFindStoredEntriesForFeed:
    @pytest.mark.asyncio
    async def test_no_entries_stored(self, loaded_feed: Feed) -> None:
        entries = [make.fake_entry(loaded_feed.source_id) for _ in range(3)]
        external_ids = [entry.external_id for entry in entries]

        stored_entries = await find_stored_entries_for_feed(loaded_feed.id, external_ids)

        assert stored_entries == set()

    @pytest.mark.asyncio
    async def test_all_entries_stored(self, loaded_feed: Feed) -> None:
        entries = await make.n_entries(loaded_feed, n=3)
        external_ids = {entry.external_id for entry in entries.values()}

        stored_entries = await find_stored_entries_for_feed(loaded_feed.id, list(external_ids))

        assert stored_entries == external_ids

    @pytest.mark.asyncio
    async def test_some_entries_stored(self, loaded_feed: Feed) -> None:
        new_entries = [make.fake_entry(loaded_feed.source_id) for _ in range(3)]
        saved_entries = await make.n_entries(loaded_feed, n=2)
        external_ids = [entry.external_id for entry in new_entries] + [
            entry.external_id for entry in saved_entries.values()
        ]

        stored_entries = await find_stored_entries_for_feed(loaded_feed.id, external_ids)

        assert stored_entries == set(entry.external_id for entry in saved_entries.values())

    @pytest.mark.asyncio
    async def test_some_entries_stored_in_another_feed(self, loaded_feed: Feed, another_loaded_feed: Feed) -> None:
        saved_entries = await make.n_entries_list(loaded_feed, n=2)
        saved_another_entries = await make.n_entries_list(another_loaded_feed, n=2)

        common_entry = make.fake_entry(loaded_feed.source_id)
        await catalog_entries(loaded_feed.id, [common_entry])
        await catalog_entries(another_loaded_feed.id, [common_entry])

        external_ids = [entry.external_id for entry in chain(saved_entries, saved_another_entries, [common_entry])]

        stored_entries = await find_stored_entries_for_feed(loaded_feed.id, external_ids)
        assert stored_entries == set(entry.external_id for entry in saved_entries) | {common_entry.external_id}

        stored_entries = await find_stored_entries_for_feed(another_loaded_feed.id, external_ids)
        assert stored_entries == set(entry.external_id for entry in saved_another_entries) | {common_entry.external_id}


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
    @pytest.fixture
    def time_border(self) -> datetime.datetime:
        return utils.now() - datetime.timedelta(days=1)

    # TODO: actualize to multiple feeds?
    @pytest_asyncio.fixture
    async def prepared_entries(
        self, loaded_feed: Feed, another_loaded_feed: Feed, time_border: datetime.datetime
    ) -> tuple[list[Entry], list[Entry]]:
        entries = await make.n_entries_list(loaded_feed, n=3)
        another_entries = await make.n_entries_list(another_loaded_feed, n=3)

        common_entry = make.fake_entry(loaded_feed.source_id)
        await catalog_entries(loaded_feed.id, [common_entry])
        await catalog_entries(another_loaded_feed.id, [common_entry])

        await execute(
            "UPDATE l_feeds_to_entries SET created_at = %(time_border)s WHERE entry_id = ANY(%(ids)s)",
            {
                "time_border": time_border - datetime.timedelta(seconds=10),
                "ids": [entries[0].id, another_entries[0].id],
            },
        )

        await execute(
            "UPDATE l_entries SET created_at = %(time_border)s WHERE id = ANY(%(ids)s)",
            {
                "time_border": time_border - datetime.timedelta(seconds=10),
                "ids": [entries[0].id, another_entries[0].id],
            },
        )

        all_entries = await get_entries_by_ids(ids=[entry.id
                                                    for entry in chain(entries, another_entries, [common_entry])])

        all_entries_list = list(all_entries.values())
        all_entries_list.sort(key=lambda entry: entry.cataloged_at)  # type: ignore

        entries_1 = []
        entries_2 = []

        for entry in all_entries_list:
            if entry.id in {e.id for e in entries}:
                entries_1.append(entry)
            elif entry.id in {e.id for e in another_entries}:
                entries_2.append(entry)
            elif entry.id == common_entry.id:
                entries_1.append(entry)
                entries_2.append(entry)
            else:
                raise NotImplementedError()

        return (entries_1, entries_2)

    @pytest.mark.asyncio
    async def test_all(
        self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId, prepared_entries: list[Entry]
    ) -> None:
        loaded_entries = await get_entries_by_filter(feeds_ids=[loaded_feed_id, another_loaded_feed_id], limit=100)

        loaded_entries_ids = {entry.id for entry in loaded_entries}
        assert loaded_entries_ids == {entry.id for entry in chain(*prepared_entries)}

    @pytest.mark.asyncio
    async def test_limit(
        self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId, prepared_entries: list[Entry]
    ) -> None:
        loaded_entries = await get_entries_by_filter(feeds_ids=[loaded_feed_id, another_loaded_feed_id], limit=5)

        loaded_entries_ids = {entry.id for entry in loaded_entries}
        assert loaded_entries_ids == {entry.id for entry in chain(prepared_entries[0][1:], prepared_entries[1][1:])}

    @pytest.mark.asyncio
    async def test_feeds_filter(self, loaded_feed_id: FeedId, prepared_entries: list[Entry]) -> None:
        loaded_entries = await get_entries_by_filter(feeds_ids=[loaded_feed_id], limit=100)
        loaded_entries_ids = {entry.id for entry in loaded_entries}
        assert loaded_entries_ids == {entry.id for entry in prepared_entries[0]}

    @pytest.mark.asyncio
    async def test_time_period(
        self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId, prepared_entries: list[Entry]
    ) -> None:
        loaded_entries = await get_entries_by_filter(
            feeds_ids=[loaded_feed_id, another_loaded_feed_id], limit=100, period=datetime.timedelta(days=1)
        )

        loaded_entries_ids = {entry.id for entry in loaded_entries}
        assert loaded_entries_ids == {entry.id for entry in chain(prepared_entries[0][1:], prepared_entries[1][1:])}


class TestGetEntriesAfterPointer:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        entries = await get_entries_after_pointer(created_at=utils.now(), entry_id=new_entry_id(), limit=100)
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_some(self, loaded_feed: Feed) -> None:
        enries = await make.n_entries(loaded_feed, n=5)

        entries_list = list(enries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        loaded_entries = await get_entries_after_pointer(
            created_at=entries_list[2].cataloged_at, entry_id=entries_list[2].id, limit=100
        )

        assert [(entry.id, entry.cataloged_at) for entry in entries_list[3:]] == loaded_entries

    @pytest.mark.asyncio
    async def test_duplicated_created_at(self, loaded_feed: Feed) -> None:
        entries = await make.n_entries(loaded_feed, n=5)

        entries_list = list(entries.values())

        base_time = entries_list[1].cataloged_at

        await execute(
            "UPDATE l_entries SET created_at = %(created_at)s WHERE id = ANY(%(ids)s)",
            {"created_at": base_time, "ids": [entry.id for entry in entries_list[1:5]]},
        )

        entries = await get_entries_by_ids(ids=[entry.id for entry in entries_list])  # type: ignore

        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        for i in range(1, 4):
            loaded_entries = await get_entries_after_pointer(
                created_at=base_time, entry_id=entries_list[i].id, limit=100
            )

            assert [(entry.id, entry.cataloged_at) for entry in entries_list[i + 1 :]] == loaded_entries

    @pytest.mark.asyncio
    async def test_limit(self, loaded_feed: Feed) -> None:
        entries = await make.n_entries(loaded_feed, n=5)

        entries_list = list(entries.values())

        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        loaded_entries = await get_entries_after_pointer(
            created_at=entries_list[2].cataloged_at, entry_id=entries_list[2].id, limit=2
        )

        assert [(entry.id, entry.cataloged_at) for entry in entries_list[3:5]] == loaded_entries


class TestAllEntriesIterator:
    @pytest.mark.parametrize("chunk", [1, 2, 3, 4, 5, 6, 7])
    @pytest.mark.asyncio
    async def test(self, chunk: int) -> None:
        feed_1_data = await f_make.fake_feed()
        feed_1_id = await f_domain.save_feed(feed_1_data)

        feed_2_data = await f_make.fake_feed()
        feed_2_id = await f_domain.save_feed(feed_2_data)

        entries_1_data = [await make.fake_entry(feed_1_id) for _ in range(3)]
        entries_2_data = [await make.fake_entry(feed_2_id) for _ in range(3)]

        await catalog_entries(entries_1_data)
        await catalog_entries(entries_2_data)

        ids = [(e.feed_id, e.id) for e in chain(entries_1_data, entries_2_data)]

        ids.sort()

        found_ids = [
            (entry.feed_id, entry.id)
            async for entry in all_entries_iterator(chunk=chunk)
            if (entry.feed_id, entry.id) in ids
        ]

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


class TestTechMoveEntry:
    @pytest.mark.asyncio
    async def test_moved(self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId, cataloged_entry: Entry) -> None:
        async with TableSizeNotChanged("l_entries"):
            await tech_move_entry(cataloged_entry.id, another_loaded_feed_id)

        loaded_entry = await get_entry(cataloged_entry.id)

        assert loaded_entry.feed_id == another_loaded_feed_id

        assert cataloged_entry.replace(feed_id=another_loaded_feed_id) == loaded_entry

    @pytest.mark.asyncio
    async def test_feed_has_the_same_entry(
        self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId, new_entry: Entry
    ) -> None:
        duplicated_entry = new_entry.replace(feed_id=another_loaded_feed_id, id=uuid.uuid4())

        await catalog_entries([new_entry, duplicated_entry])

        async with TableSizeNotChanged("l_entries"):
            with pytest.raises(errors.CanNotMoveEntryAlreadyInFeed):
                await tech_move_entry(duplicated_entry.id, loaded_feed_id)

        loaded_entry = await get_entry(new_entry.id)

        assert loaded_entry == new_entry.replace(cataloged_at=loaded_entry.cataloged_at)

        loaded_duplicated_entries = await get_entry(duplicated_entry.id)

        assert loaded_duplicated_entries == duplicated_entry.replace(
            cataloged_at=loaded_duplicated_entries.cataloged_at
        )


class TestTechRemoveEntriesByIds:
    @pytest.mark.asyncio
    async def test_removed(self, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId) -> None:
        entries = await make.n_entries(loaded_feed_id, n=3)
        another_entries = await make.n_entries(another_loaded_feed_id, n=3)

        entries_list = list(entries.values())
        another_entries_list = list(another_entries.values())

        async with TableSizeDelta("l_entries", delta=-2):
            await tech_remove_entries_by_ids([entries_list[0].id, another_entries_list[0].id])

        loaded_entries = await get_entries_by_ids([entry.id for entry in entries_list + another_entries_list])

        assert loaded_entries[entries_list[0].id] is None
        assert loaded_entries[another_entries_list[0].id] is None

    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        async with TableSizeNotChanged("l_entries"):
            await tech_remove_entries_by_ids([])
            await tech_remove_entries_by_ids([new_entry_id()])

    @pytest.mark.asyncio
    async def test_already_removed(self, loaded_feed_id: FeedId) -> None:
        entries = await make.n_entries(loaded_feed_id, n=3)

        entries_list = list(entries.values())

        await tech_remove_entries_by_ids([entry.id for entry in entries_list])

        async with TableSizeNotChanged("l_entries"):
            await tech_remove_entries_by_ids([entry.id for entry in entries_list])


class TestTechGetFeedEntriesTail:
    @pytest.mark.asyncio
    async def test_nothing_to_return(self, loaded_feed_id: FeedId) -> None:
        await make.n_entries(loaded_feed_id, n=5)

        ids = await tech_get_feed_entries_tail(loaded_feed_id, offset=10)

        assert ids == set()

    @pytest.mark.asyncio
    async def test_zero_head(self, loaded_feed_id: FeedId) -> None:
        entries = await make.n_entries(loaded_feed_id, n=5)

        ids = await tech_get_feed_entries_tail(loaded_feed_id, offset=0)

        assert ids == set(entry.id for entry in entries.values())

    @pytest.mark.asyncio
    async def test_not_excceed_limit(self, loaded_feed_id: FeedId) -> None:
        await make.n_entries(loaded_feed_id, n=5)

        ids = await tech_get_feed_entries_tail(loaded_feed_id, offset=10)

        assert ids == set()

    @pytest.mark.asyncio
    async def test_offset(self, loaded_feed_id: FeedId) -> None:
        entries = await make.n_entries_list(loaded_feed_id, n=15)

        ids = await tech_get_feed_entries_tail(loaded_feed_id, offset=10)

        assert ids == set(entry.id for entry in entries[10:])
