import pytest
import pytest_asyncio

from ffun.dispatcher import operations
from ffun.dispatcher.entities import EntryProcessingStatus
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import ProcessorId


@pytest_asyncio.fixture(autouse=True)  # type: ignore
async def prepare_processing_statuses() -> None:
    await operations.tech_truncate_entry_processing_statuses()


class TestGetEntriesProcessingStatuses:
    @pytest.mark.asyncio
    async def test_empty_entries_or_processors(self) -> None:
        assert await operations.get_entries_processing_statuses([ProcessorId(101)], []) == {ProcessorId(101): {}}
        assert await operations.get_entries_processing_statuses([], [new_entry_id()]) == {}

    @pytest.mark.asyncio
    async def test_returns_empty_statuses_for_processors_without_statuses(self) -> None:
        processor_id = ProcessorId(101)
        another_processor_id = ProcessorId(102)

        assert await operations.get_entries_processing_statuses(
            [processor_id, another_processor_id], [new_entry_id()]
        ) == {
            processor_id: {},
            another_processor_id: {},
        }

    @pytest.mark.asyncio
    async def test_returns_statuses_grouped_by_processor(self) -> None:
        processor_id = ProcessorId(101)
        another_processor_id = ProcessorId(102)
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            processor_id, [first_entry_id, second_entry_id], EntryProcessingStatus.dispatched
        )
        await operations.set_entry_processing_statuses(
            another_processor_id, [first_entry_id], EntryProcessingStatus.failed
        )

        assert await operations.get_entries_processing_statuses(
            [processor_id, another_processor_id], [first_entry_id, second_entry_id]
        ) == {
            processor_id: {
                first_entry_id: EntryProcessingStatus.dispatched,
                second_entry_id: EntryProcessingStatus.dispatched,
            },
            another_processor_id: {
                first_entry_id: EntryProcessingStatus.failed,
            },
        }


class TestGetEntriesByProcessingStatus:
    @pytest.mark.asyncio
    async def test_returns_entries_for_processor_and_status(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        processor_id = fake_processor_id
        another_processor_id = another_fake_processor_id
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        processed_entry_id = new_entry_id()
        another_processor_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            processor_id, [first_entry_id, second_entry_id], EntryProcessingStatus.dispatched
        )
        await operations.set_entry_processing_statuses(
            processor_id, [processed_entry_id], EntryProcessingStatus.processed
        )
        await operations.set_entry_processing_statuses(
            another_processor_id, [another_processor_entry_id], EntryProcessingStatus.dispatched
        )

        dispatched_entries = await operations.get_entries_by_processing_status(
            processor_id, EntryProcessingStatus.dispatched, limit=100500
        )

        assert set(dispatched_entries) == {first_entry_id, second_entry_id}

        processed_entries = await operations.get_entries_by_processing_status(
            processor_id, EntryProcessingStatus.processed, limit=100500
        )

        assert processed_entries == [processed_entry_id]

        await operations.set_entry_processing_statuses(
            processor_id, [first_entry_id, second_entry_id], EntryProcessingStatus.processed
        )
        await operations.set_entry_processing_statuses(
            another_processor_id, [another_processor_entry_id], EntryProcessingStatus.processed
        )

    @pytest.mark.asyncio
    async def test_limit(self, fake_processor_id: ProcessorId) -> None:
        processor_id = fake_processor_id
        entry_ids = [new_entry_id(), new_entry_id(), new_entry_id()]

        await operations.set_entry_processing_statuses(processor_id, entry_ids, EntryProcessingStatus.dispatched)

        dispatched_entries = await operations.get_entries_by_processing_status(
            processor_id, EntryProcessingStatus.dispatched, limit=2
        )

        assert len(dispatched_entries) == 2
        assert set(dispatched_entries) <= set(entry_ids)

        await operations.set_entry_processing_statuses(processor_id, entry_ids, EntryProcessingStatus.processed)


class TestCountEntriesByProcessingStatus:
    @pytest.mark.asyncio
    async def test_counts_entries_per_processor_for_status(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        processor_id = fake_processor_id
        another_processor_id = another_fake_processor_id
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        processed_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            processor_id, [first_entry_id, second_entry_id], EntryProcessingStatus.dispatched
        )
        await operations.set_entry_processing_statuses(
            processor_id, [processed_entry_id], EntryProcessingStatus.processed
        )
        await operations.set_entry_processing_statuses(
            another_processor_id, [first_entry_id], EntryProcessingStatus.dispatched
        )

        counts = await operations.count_entries_by_processing_status(EntryProcessingStatus.dispatched)

        assert counts[processor_id] == 2
        assert counts[another_processor_id] == 1

        await operations.set_entry_processing_statuses(
            processor_id, [first_entry_id, second_entry_id], EntryProcessingStatus.processed
        )
        await operations.set_entry_processing_statuses(
            another_processor_id, [first_entry_id], EntryProcessingStatus.processed
        )


class TestSetEntryProcessingStatuses:
    @pytest.mark.asyncio
    async def test_empty_entries(self) -> None:
        await operations.set_entry_processing_statuses(ProcessorId(101), [], EntryProcessingStatus.dispatched)

    @pytest.mark.asyncio
    async def test_updates_existing_statuses(self) -> None:
        processor_id = ProcessorId(101)
        entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(processor_id, [entry_id], EntryProcessingStatus.dispatched)
        await operations.set_entry_processing_statuses(processor_id, [entry_id], EntryProcessingStatus.processed)

        statuses = await operations.get_entries_processing_statuses([processor_id], [entry_id])

        assert statuses.get(processor_id, {}) == {entry_id: EntryProcessingStatus.processed}

    @pytest.mark.asyncio
    async def test_updates_only_requested_processor_entries(self) -> None:
        processor_id = ProcessorId(101)
        another_processor_id = ProcessorId(102)
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        third_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            processor_id, [first_entry_id, second_entry_id], EntryProcessingStatus.dispatched
        )
        await operations.set_entry_processing_statuses(
            another_processor_id, [first_entry_id, second_entry_id], EntryProcessingStatus.failed
        )
        await operations.set_entry_processing_statuses(
            processor_id, [second_entry_id, third_entry_id], EntryProcessingStatus.processed
        )

        assert await operations.get_entries_processing_statuses(
            [processor_id, another_processor_id],
            [first_entry_id, second_entry_id, third_entry_id],
        ) == {
            processor_id: {
                first_entry_id: EntryProcessingStatus.dispatched,
                second_entry_id: EntryProcessingStatus.processed,
                third_entry_id: EntryProcessingStatus.processed,
            },
            another_processor_id: {
                first_entry_id: EntryProcessingStatus.failed,
                second_entry_id: EntryProcessingStatus.failed,
            },
        }


class TestRemoveEntryProcessingStatuses:
    @pytest.mark.asyncio
    async def test_empty_entries(self) -> None:
        await operations.remove_entry_processing_statuses([])

    @pytest.mark.asyncio
    async def test_removes_only_requested_entries(self) -> None:
        processor_id = ProcessorId(101)
        another_processor_id = ProcessorId(102)
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        third_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            processor_id, [first_entry_id, second_entry_id, third_entry_id], EntryProcessingStatus.dispatched
        )
        await operations.set_entry_processing_statuses(
            another_processor_id, [first_entry_id, second_entry_id], EntryProcessingStatus.failed
        )

        await operations.remove_entry_processing_statuses([first_entry_id, second_entry_id])

        assert await operations.get_entries_processing_statuses(
            [processor_id, another_processor_id], [first_entry_id, second_entry_id, third_entry_id]
        ) == {
            processor_id: {
                third_entry_id: EntryProcessingStatus.dispatched,
            },
            another_processor_id: {},
        }
