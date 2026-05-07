from collections.abc import Sequence

import pytest

from ffun.dispatcher import domain
from ffun.dispatcher.entities import EntryToProcess
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import EntryId
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


class TestDispatchEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        dispatched = await domain.dispatch_entries(processor_ids=[101], limit=10)

        assert dispatched == 0

    @pytest.mark.asyncio
    async def test_dispatch_to_each_processor_subqueue(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        processor_ids = [101, 102]

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processor_ids=processor_ids, limit=10)

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

        dispatched = await domain.dispatch_entries(processor_ids=[], limit=10)

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

        dispatched = await domain.dispatch_entries(processor_ids=[processor_id], limit=2)

        assert dispatched == 2

        dispatched_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToProcess, secondary_id=processor_id
        )
        remaining_records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert len(dispatched_records) == 2
        assert len(remaining_records) == 1
        assert record_entry_ids(dispatched_records) | record_entry_ids(remaining_records) == set(entry_ids)
