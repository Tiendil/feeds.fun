from collections.abc import Sequence

import pytest
from pytest_mock import MockerFixture

from ffun.dispatcher import domain
from ffun.dispatcher.entities import EntryToProcess, ProcessorDispatchInfo
from ffun.dispatcher.tests import make
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import EntryId
from ffun.feeds.entities import Feed
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind, QueueRecord


def record_entry_ids(records: Sequence[QueueRecord[EntryToProcess]]) -> set[EntryId]:
    return {record.item.entry_id for record in records}


class TestPushEntriesToProcess:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        await domain.push_entries_to_process([])

        assert await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess) == []

    @pytest.mark.asyncio
    async def test_push_entries(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id(), new_entry_id()]

        await domain.push_entries_to_process(entry_ids)

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)


class TestGetEntriesToTag:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        processor_id = 101

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=processor_id)

        assert await domain.get_entries_to_tag(processor_id=processor_id, limit=10) == []

    @pytest.mark.asyncio
    async def test_get_entries_from_processor_subqueue(self) -> None:
        processor_id = 101
        another_processor_id = 102

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=processor_id)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=another_processor_id)

        entry_ids = [new_entry_id(), new_entry_id()]
        another_entry_ids = [new_entry_id()]

        await domain.push_entries_to_tag(processor_id, entry_ids)
        await domain.push_entries_to_tag(another_processor_id, another_entry_ids)

        records = await domain.get_entries_to_tag(processor_id=processor_id, limit=10)

        assert record_entry_ids(records) == set(entry_ids)


class TestPushEntriesToTag:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        processor_id = 101

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=processor_id)

        await domain.push_entries_to_tag(processor_id, [])

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=processor_id
        )

        assert records == []

    @pytest.mark.asyncio
    async def test_push_entries_to_processor_subqueue(self) -> None:
        processor_id = 101
        another_processor_id = 102

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=processor_id)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=another_processor_id)

        entry_ids = [new_entry_id(), new_entry_id()]

        await domain.push_entries_to_tag(processor_id, entry_ids)

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=processor_id
        )
        another_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=another_processor_id
        )

        assert record_entry_ids(records) == set(entry_ids)
        assert another_records == []


class TestAcknowledge:
    @pytest.mark.asyncio
    async def test_no_records(self) -> None:
        assert await domain.acknowledge([]) == 0

    @pytest.mark.asyncio
    async def test_acknowledge_records(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id(), new_entry_id(), new_entry_id()]

        await domain.push_entries_to_process(entry_ids)

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)
        records_to_acknowledge = records[:2]
        records_to_keep = records[2:]

        assert await domain.acknowledge([record.id for record in records_to_acknowledge if record.id is not None]) == 2

        records_after_acknowledgement = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_process, EntryToProcess
        )

        assert record_entry_ids(records_after_acknowledgement) == record_entry_ids(records_to_keep)


class TestEntriesInCollections:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        assert await domain._entries_in_collections([]) == {}

    @pytest.mark.asyncio
    async def test_returns_collection_membership(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        user_entries = await l_make.n_entries(loaded_feed, 2)
        collection_entries = await l_make.n_entries(another_loaded_feed, 3)

        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_in_collections = await domain._entries_in_collections(list(user_entries) + list(collection_entries))

        assert entries_in_collections == {
            **{entry_id: False for entry_id in user_entries},
            **{entry_id: True for entry_id in collection_entries},
        }

    @pytest.mark.asyncio
    async def test_returns_collection_membership_for_entries_linked_to_multiple_feeds(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed, 3)

        await l_domain.catalog_entries(
            another_loaded_feed.id,
            [entry.collected_entry() for entry in entries[:2]],
        )
        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_in_collections = await domain._entries_in_collections([entry.id for entry in entries])

        assert entries_in_collections == {
            entries[0].id: True,
            entries[1].id: True,
            entries[2].id: False,
        }

    @pytest.mark.asyncio
    async def test_skips_entries_without_feed_links(self) -> None:
        entry_id = new_entry_id()

        assert await domain._entries_in_collections([entry_id]) == {}


class TestProcessorIsAllowed:
    @pytest.mark.parametrize(
        "case",
        [
            (False, False, False, False),
            (False, False, True, True),
            (False, True, False, False),
            (False, True, True, True),
            (True, False, False, False),
            (True, False, True, False),
            (True, True, False, True),
            (True, True, True, True),
        ],
    )
    def test_all_permission_combinations(
        self,
        case: tuple[bool, bool, bool, bool],
    ) -> None:
        (
            in_collection,
            allowed_for_collections,
            allowed_for_users,
            expected_allowed,
        ) = case

        item = EntryToProcess(entry_id=new_entry_id())
        processor = make.processor_dispatch_info(
            101,
            allowed_for_collections=allowed_for_collections,
            allowed_for_users=allowed_for_users,
        )

        allowed = domain._processor_is_allowed(processor, item, in_collection=in_collection)

        assert allowed == expected_allowed


class TestDispatchEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        dispatched = await domain.dispatch_entries(processors=[make.processor_dispatch_info(101)], limit=10)

        assert dispatched == 0

    @pytest.mark.asyncio
    async def test_dispatch_to_each_processor_subqueue(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        processor_ids = [101, 102]

        await domain.push_entries_to_process(entry_ids)

        processors = [make.processor_dispatch_info(processor_id) for processor_id in processor_ids]
        dispatched = await domain.dispatch_entries(processors=processors, limit=10)

        assert dispatched == len(entry_ids)
        assert await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess) == []

        for processor_id in processor_ids:
            records = await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag, EntryToProcess, secondary_id=processor_id
            )

            assert record_entry_ids(records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_no_processors(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id()]

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[], limit=10)

        assert dispatched == 0

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_limit(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id(), new_entry_id()]
        processor_id = 101

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[make.processor_dispatch_info(processor_id)], limit=2)

        assert dispatched == 2

        dispatched_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=processor_id
        )
        remaining_records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert len(dispatched_records) == 2
        assert len(remaining_records) == 1
        assert record_entry_ids(dispatched_records) | record_entry_ids(remaining_records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_uses_processor_allowance_result(self, mocker: MockerFixture) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id() for _ in range(5)]
        first_processor = make.processor_dispatch_info(101)
        second_processor = make.processor_dispatch_info(102)
        processors = [first_processor, second_processor]

        allowed = {
            (first_processor.processor_id, entry_ids[0]),
            (first_processor.processor_id, entry_ids[2]),
            (second_processor.processor_id, entry_ids[2]),
            (second_processor.processor_id, entry_ids[1]),
        }
        calls: list[tuple[int, EntryId]] = []

        def is_allowed(processor: ProcessorDispatchInfo, item: EntryToProcess, *, in_collection: bool) -> bool:
            processor_id = processor.processor_id
            calls.append((processor_id, item.entry_id))
            return (processor_id, item.entry_id) in allowed

        mocker.patch.object(domain, "_processor_is_allowed", side_effect=is_allowed)

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=processors, limit=10)

        assert dispatched == len(entry_ids)
        assert set(calls) == {(processor.processor_id, entry_id) for processor in processors for entry_id in entry_ids}

        first_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=first_processor.subqueue_id
        )
        second_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=second_processor.subqueue_id
        )

        assert record_entry_ids(first_records) == {entry_ids[0], entry_ids[2]}
        assert record_entry_ids(second_records) == {entry_ids[1], entry_ids[2]}

    @pytest.mark.asyncio
    async def test_dispatch_uses_processor_subqueue_id(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        processor = make.processor_dispatch_info(101, subqueue_id=201)

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[processor], limit=10)

        assert dispatched == len(entry_ids)
        assert (
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag, EntryToProcess, secondary_id=processor.processor_id
            )
            == []
        )

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=processor.subqueue_id
        )

        assert record_entry_ids(records) == set(entry_ids)
