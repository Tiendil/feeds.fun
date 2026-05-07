import pytest
from structlog.testing import capture_logs

from ffun.core.tests.helpers import assert_logs
from ffun.dispatcher import domain as d_domain
from ffun.dispatcher.entities import EntryToProcess
from ffun.domain.domain import new_entry_id
from ffun.feeds.entities import Feed
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.librarian.background_processors import EntriesProcessor
from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.library.tests import helpers as l_helpers
from ffun.library.tests import make as l_make
from ffun.ontology import domain as o_domain
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind


def _entry_sort_key(entry: Entry) -> tuple[object, object]:
    return (entry.created_at, entry.id)


def _feed_retention_sort_key(entry: Entry) -> tuple[object, object]:
    return (entry.published_at, entry.created_at)


class TestEntriesProcessors:
    @pytest.mark.asyncio
    async def test_no_entries_to_process(self, fake_entries_processor: EntriesProcessor) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        with capture_logs() as logs:  # type: ignore
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=1)  # type: ignore

    @pytest.mark.asyncio
    async def test_entries_more_than_concurrency(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 9)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        await d_domain.push_entries_to_tag(fake_entries_processor.id, [entry.id for entry in entries_list])

        assert fake_entries_processor.concurrency <= len(entries)

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=fake_entries_processor.id
        )
        expected_processed_entries = {record.item.entry_id for record in records[: fake_entries_processor.concurrency]}
        expected_queued_entries = {record.item.entry_id for record in records[fake_entries_processor.concurrency :]}

        with capture_logs() as logs:  # type: ignore
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0)  # type: ignore

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})  # type: ignore

        assert len(tags) == fake_entries_processor.concurrency
        assert set(tags) == expected_processed_entries

        for tagged_entry_ids in tags.values():
            assert tagged_entry_ids == set(expected_ids.values())

        records = await d_domain.get_entries_to_tag(processor_id=fake_entries_processor.id, limit=100)

        assert {record.item.entry_id for record in records} == expected_queued_entries

        await d_domain.acknowledge([record.id for record in records if record.id is not None])

    @pytest.mark.asyncio
    async def test_entries_less_than_concurrency(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        await d_domain.push_entries_to_tag(fake_entries_processor.id, [entry.id for entry in entries_list])

        assert fake_entries_processor.concurrency > len(entries)

        with capture_logs() as logs:  # type: ignore
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0)  # type: ignore

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})  # type: ignore

        for entry in entries_list:
            assert tags[entry.id] == set(expected_ids.values())

    @pytest.mark.asyncio
    async def test_unexisted_entries_in_queue(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        fake_entries_ids = [new_entry_id() for _ in range(3)]

        await d_domain.push_entries_to_tag(
            fake_entries_processor.id, [entry.id for entry in entries_list] + fake_entries_ids
        )

        assert fake_entries_processor.concurrency >= len(entries) + len(fake_entries_ids)

        with capture_logs() as logs:  # type: ignore
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0, unexisted_entry_in_queue=3)  # type: ignore

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})  # type: ignore

        for entry in entries_list:
            assert tags[entry.id] == set(expected_ids.values())

        records = await d_domain.get_entries_to_tag(processor_id=fake_entries_processor.id, limit=100)

        assert records == []

    @pytest.mark.asyncio
    async def test_separate_entries__unexsisted_entries(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        fake_entries_ids = [new_entry_id() for _ in range(3)]

        entries_ids = [entry.id for entry in entries_list] + fake_entries_ids

        with capture_logs() as logs:  # type: ignore
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,  # type: ignore
            unexisted_entry_in_queue=3,
            entry_without_feeds_in_queue=0,
            proccessor_not_allowed_for_collections=0,
            proccessor_not_allowed_for_users=0,
            proccessor_is_allowed_for_entry=2,
        )

        assert {entry.id for entry in entries_to_process} == {entry.id for entry in entries_list}
        assert set(entries_to_remove) == set(fake_entries_ids)

    @pytest.mark.asyncio
    async def test_separate_entries__entries_without_feeds_in_queue(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        entries = await l_make.n_entries(loaded_feed, 5)
        entries_list = list(entries.values())

        # remove the oldest entries from their only feed to simulate stale queue items
        entries_list.sort(key=_feed_retention_sort_key)
        await l_helpers.unlink_entries_from_feed(loaded_feed.id, [entry.id for entry in entries_list[:2]])

        entries_ids = [entry.id for entry in entries_list]

        with capture_logs() as logs:  # type: ignore
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,  # type: ignore
            unexisted_entry_in_queue=0,
            entry_without_feeds_in_queue=2,
            proccessor_not_allowed_for_collections=0,
            proccessor_not_allowed_for_users=0,
            proccessor_is_allowed_for_entry=3,
        )

        assert {entry.id for entry in entries_to_process} == {entry.id for entry in entries_list[2:]}
        assert set(entries_to_remove) == {entry.id for entry in entries_list[:2]}

    @pytest.mark.asyncio
    async def test_separate_entries__collections_not_allowed(
        self,
        fake_entries_processor: EntriesProcessor,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        entries_1 = await l_make.n_entries(loaded_feed, 3)
        entries_2 = await l_make.n_entries(another_loaded_feed, 2)

        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_list = list(entries_1.values()) + list(entries_2.values())
        entries_list.sort(key=_entry_sort_key)

        entries_ids = [entry.id for entry in entries_list]

        fake_entries_processor._processor_info.allowed_for_collections = False

        with capture_logs() as logs:  # type: ignore
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,  # type: ignore
            unexisted_entry_in_queue=0,
            proccessor_not_allowed_for_collections=2,
            proccessor_not_allowed_for_users=0,
            proccessor_is_allowed_for_entry=3,
        )

        assert {entry.id for entry in entries_to_process} == set(entries_1)
        assert set(entries_to_remove) == set(entries_2)

    @pytest.mark.asyncio
    async def test_separate_entries__collections_not_allowed__entry_is_in_multiple_feeds(
        self,
        fake_entries_processor: EntriesProcessor,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        entries_1 = await l_make.n_entries_list(loaded_feed, 3)
        entries_2 = await l_make.n_entries_list(another_loaded_feed, 2)

        await l_domain.catalog_entries(
            another_loaded_feed.id,
            [entry.collected_entry() for entry in entries_1[:2]],
        )

        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_list = list(entries_1) + list(entries_2)
        entries_list.sort(key=_entry_sort_key)

        entries_ids = [entry.id for entry in entries_list]

        fake_entries_processor._processor_info.allowed_for_collections = False

        with capture_logs() as logs:  # type: ignore
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,  # type: ignore
            unexisted_entry_in_queue=0,
            proccessor_not_allowed_for_collections=4,
            proccessor_not_allowed_for_users=0,
            proccessor_is_allowed_for_entry=1,
        )

        assert {entry.id for entry in entries_to_process} == {entries_1[2].id}
        assert set(entries_to_remove) == {entry.id for entry in entries_1[:2]} | {entry.id for entry in entries_2}

    @pytest.mark.asyncio
    async def test_separate_entries__all_allowed(
        self,
        fake_entries_processor: EntriesProcessor,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        entries_1 = await l_make.n_entries(loaded_feed, 3)
        entries_2 = await l_make.n_entries(another_loaded_feed, 2)

        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_list = list(entries_1.values()) + list(entries_2.values())
        entries_list.sort(key=_entry_sort_key)

        entries_ids = [entry.id for entry in entries_list]

        fake_entries_processor._processor_info.allowed_for_collections = True
        fake_entries_processor._processor_info.allowed_for_users = True

        with capture_logs() as logs:  # type: ignore
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,  # type: ignore
            unexisted_entry_in_queue=0,
            proccessor_not_allowed_for_collections=0,
            proccessor_not_allowed_for_users=0,
            proccessor_is_allowed_for_entry=5,
        )

        assert {entry.id for entry in entries_to_process} == set(entries_1) | set(entries_2)

    @pytest.mark.asyncio
    async def test_separate_entries__users_not_allowed(
        self,
        fake_entries_processor: EntriesProcessor,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        entries_1 = await l_make.n_entries(loaded_feed, 3)
        entries_2 = await l_make.n_entries(another_loaded_feed, 2)

        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_list = list(entries_1.values()) + list(entries_2.values())
        entries_list.sort(key=_entry_sort_key)

        entries_ids = [entry.id for entry in entries_list]

        fake_entries_processor._processor_info.allowed_for_users = False

        with capture_logs() as logs:  # type: ignore
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,  # type: ignore
            unexisted_entry_in_queue=0,
            proccessor_not_allowed_for_collections=0,
            proccessor_not_allowed_for_users=3,
            proccessor_is_allowed_for_entry=2,
        )

        assert {entry.id for entry in entries_to_process} == set(entries_2)
        assert set(entries_to_remove) == set(entries_1)
