import pytest
import pytest_asyncio

from ffun.dispatcher import errors, operations
from ffun.dispatcher.entities import EntryProcessingStatus, EntryProcessingStatusUpdate
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import EntryId, ProcessorId


@pytest_asyncio.fixture(autouse=True)  # type: ignore
async def prepare_processing_statuses() -> None:
    await operations.tech_truncate_entry_dispatching_statuses()
    await operations.tech_truncate_entry_processing_statuses()


def make_status_updates(
    processor_id: ProcessorId,
    entry_ids: list[EntryId],
    status: EntryProcessingStatus,
) -> list[EntryProcessingStatusUpdate]:
    return [
        EntryProcessingStatusUpdate(
            processor_id=processor_id,
            entry_id=entry_id,
            status=status,
        )
        for entry_id in entry_ids
    ]


class TestGetEntriesDispatchingStatuses:
    @pytest.mark.asyncio
    async def test_empty_entries(self) -> None:
        assert await operations.get_entries_dispatching_statuses([]) == {}

    @pytest.mark.asyncio
    async def test_duplicate_entries(self) -> None:
        entry_id = new_entry_id()
        await operations.set_entry_dispatching_statuses([entry_id], resources_consumed=True)

        assert await operations.get_entries_dispatching_statuses([entry_id, entry_id]) == {entry_id: True}

    @pytest.mark.asyncio
    async def test_returns_statuses_only_for_requested_entries(self) -> None:
        consumed_entry_id = new_entry_id()
        not_consumed_entry_id = new_entry_id()
        another_entry_id = new_entry_id()
        missing_entry_id = new_entry_id()

        await operations.set_entry_dispatching_statuses([consumed_entry_id], resources_consumed=True)
        await operations.set_entry_dispatching_statuses([not_consumed_entry_id], resources_consumed=False)
        await operations.set_entry_dispatching_statuses([another_entry_id], resources_consumed=True)

        assert await operations.get_entries_dispatching_statuses(
            [consumed_entry_id, not_consumed_entry_id, missing_entry_id]
        ) == {
            consumed_entry_id: True,
            not_consumed_entry_id: False,
        }


class TestSetEntryDispatchingStatuses:
    @pytest.mark.asyncio
    async def test_empty_entries(self) -> None:
        entry_id = new_entry_id()
        await operations.set_entry_dispatching_statuses([entry_id], resources_consumed=False)

        await operations.set_entry_dispatching_statuses([], resources_consumed=True)

        assert await operations.get_entries_dispatching_statuses([entry_id]) == {entry_id: False}

    @pytest.mark.asyncio
    async def test_duplicate_entries(self) -> None:
        entry_id = new_entry_id()

        await operations.set_entry_dispatching_statuses([entry_id, entry_id], resources_consumed=True)

        assert await operations.get_entries_dispatching_statuses([entry_id]) == {entry_id: True}

    @pytest.mark.asyncio
    async def test_updates_existing_statuses(self) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()

        await operations.set_entry_dispatching_statuses(
            [first_entry_id, second_entry_id],
            resources_consumed=False,
        )
        await operations.set_entry_dispatching_statuses([second_entry_id], resources_consumed=True)

        assert await operations.get_entries_dispatching_statuses([first_entry_id, second_entry_id]) == {
            first_entry_id: False,
            second_entry_id: True,
        }


class TestRemoveEntryDispatchingStatuses:
    @pytest.mark.asyncio
    async def test_empty_entries(self) -> None:
        await operations.remove_entry_dispatching_statuses([])

    @pytest.mark.asyncio
    async def test_removes_only_requested_entries(self) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        third_entry_id = new_entry_id()

        await operations.set_entry_dispatching_statuses(
            [first_entry_id, second_entry_id],
            resources_consumed=True,
        )
        await operations.set_entry_dispatching_statuses([third_entry_id], resources_consumed=False)

        await operations.remove_entry_dispatching_statuses([first_entry_id, second_entry_id, first_entry_id])

        assert await operations.get_entries_dispatching_statuses(
            [first_entry_id, second_entry_id, third_entry_id]
        ) == {third_entry_id: False}


class TestTechTruncateEntryDispatchingStatuses:
    @pytest.mark.asyncio
    async def test_removes_all_statuses(self) -> None:
        entry_ids = [new_entry_id(), new_entry_id()]
        await operations.set_entry_dispatching_statuses(entry_ids, resources_consumed=True)

        await operations.tech_truncate_entry_dispatching_statuses()

        assert await operations.get_entries_dispatching_statuses(entry_ids) == {}


class TestGetEntriesProcessingStatuses:
    @pytest.mark.asyncio
    async def test_empty_entries_or_processors(self, fake_processor_id: ProcessorId) -> None:
        assert await operations.get_entries_processing_statuses([fake_processor_id], []) == {fake_processor_id: {}}
        assert await operations.get_entries_processing_statuses([], [new_entry_id()]) == {}

    @pytest.mark.asyncio
    async def test_returns_empty_statuses_for_processors_without_statuses(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        assert await operations.get_entries_processing_statuses(
            [fake_processor_id, another_fake_processor_id], [new_entry_id()]
        ) == {
            fake_processor_id: {},
            another_fake_processor_id: {},
        }

    @pytest.mark.asyncio
    async def test_returns_statuses_grouped_by_processor(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [first_entry_id, second_entry_id],
                EntryProcessingStatus.dispatched,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                another_fake_processor_id,
                [first_entry_id],
                EntryProcessingStatus.failed,
            )
        )

        assert await operations.get_entries_processing_statuses(
            [fake_processor_id, another_fake_processor_id], [first_entry_id, second_entry_id]
        ) == {
            fake_processor_id: {
                first_entry_id: EntryProcessingStatus.dispatched,
                second_entry_id: EntryProcessingStatus.dispatched,
            },
            another_fake_processor_id: {
                first_entry_id: EntryProcessingStatus.failed,
            },
        }


class TestGetEntriesByProcessingStatus:
    @pytest.mark.asyncio
    async def test_returns_entries_for_processor_and_status(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        processed_entry_id = new_entry_id()
        another_processor_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [first_entry_id, second_entry_id],
                EntryProcessingStatus.dispatched,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [processed_entry_id],
                EntryProcessingStatus.processed,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                another_fake_processor_id,
                [another_processor_entry_id],
                EntryProcessingStatus.dispatched,
            )
        )

        dispatched_entries = await operations.get_entries_by_processing_status(
            fake_processor_id, EntryProcessingStatus.dispatched, limit=100500
        )

        assert set(dispatched_entries) == {first_entry_id, second_entry_id}

        processed_entries = await operations.get_entries_by_processing_status(
            fake_processor_id, EntryProcessingStatus.processed, limit=100500
        )

        assert processed_entries == [processed_entry_id]

        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [first_entry_id, second_entry_id],
                EntryProcessingStatus.processed,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                another_fake_processor_id,
                [another_processor_entry_id],
                EntryProcessingStatus.processed,
            )
        )

    @pytest.mark.asyncio
    async def test_limit(self, fake_processor_id: ProcessorId) -> None:
        entry_ids = [new_entry_id(), new_entry_id(), new_entry_id()]

        await operations.set_entry_processing_statuses(
            make_status_updates(fake_processor_id, entry_ids, EntryProcessingStatus.dispatched)
        )

        dispatched_entries = await operations.get_entries_by_processing_status(
            fake_processor_id, EntryProcessingStatus.dispatched, limit=2
        )

        assert len(dispatched_entries) == 2
        assert set(dispatched_entries) <= set(entry_ids)

        await operations.set_entry_processing_statuses(
            make_status_updates(fake_processor_id, entry_ids, EntryProcessingStatus.processed)
        )


class TestCountEntriesByProcessingStatus:
    @pytest.mark.asyncio
    async def test_counts_entries_per_processor_for_status(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        processed_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [first_entry_id, second_entry_id],
                EntryProcessingStatus.dispatched,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [processed_entry_id],
                EntryProcessingStatus.processed,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                another_fake_processor_id,
                [first_entry_id],
                EntryProcessingStatus.dispatched,
            )
        )

        counts = await operations.count_entries_by_processing_status(EntryProcessingStatus.dispatched)

        assert counts[fake_processor_id] == 2
        assert counts[another_fake_processor_id] == 1

        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [first_entry_id, second_entry_id],
                EntryProcessingStatus.processed,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                another_fake_processor_id,
                [first_entry_id],
                EntryProcessingStatus.processed,
            )
        )


class TestSetEntryProcessingStatuses:
    @pytest.mark.asyncio
    async def test_empty_updates(self, fake_processor_id: ProcessorId) -> None:
        entry_id = new_entry_id()
        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [entry_id],
                EntryProcessingStatus.dispatched,
            )
        )

        await operations.set_entry_processing_statuses([])

        assert await operations.get_entries_processing_statuses([fake_processor_id], [entry_id]) == {
            fake_processor_id: {entry_id: EntryProcessingStatus.dispatched}
        }

    @pytest.mark.asyncio
    async def test_sets_each_requested_processor_entry_status(
        self,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
    ) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            [
                EntryProcessingStatusUpdate(
                    processor_id=fake_processor_id,
                    entry_id=first_entry_id,
                    status=EntryProcessingStatus.dispatched,
                ),
                EntryProcessingStatusUpdate(
                    processor_id=fake_processor_id,
                    entry_id=second_entry_id,
                    status=EntryProcessingStatus.processed,
                ),
                EntryProcessingStatusUpdate(
                    processor_id=another_fake_processor_id,
                    entry_id=first_entry_id,
                    status=EntryProcessingStatus.failed,
                ),
            ]
        )

        assert await operations.get_entries_processing_statuses(
            [fake_processor_id, another_fake_processor_id],
            [first_entry_id, second_entry_id],
        ) == {
            fake_processor_id: {
                first_entry_id: EntryProcessingStatus.dispatched,
                second_entry_id: EntryProcessingStatus.processed,
            },
            another_fake_processor_id: {
                first_entry_id: EntryProcessingStatus.failed,
            },
        }

    @pytest.mark.asyncio
    async def test_duplicate_processor_entry_pairs_raise_error(self, fake_processor_id: ProcessorId) -> None:
        entry_id = new_entry_id()

        with pytest.raises(errors.DuplicateEntryProcessingStatusUpdates):
            await operations.set_entry_processing_statuses(
                [
                    EntryProcessingStatusUpdate(
                        processor_id=fake_processor_id,
                        entry_id=entry_id,
                        status=EntryProcessingStatus.dispatched,
                    ),
                    EntryProcessingStatusUpdate(
                        processor_id=fake_processor_id,
                        entry_id=entry_id,
                        status=EntryProcessingStatus.processed,
                    ),
                ]
            )

        assert await operations.get_entries_processing_statuses([fake_processor_id], [entry_id]) == {
            fake_processor_id: {}
        }

    @pytest.mark.asyncio
    async def test_updates_existing_statuses(self, fake_processor_id: ProcessorId) -> None:
        entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [entry_id],
                EntryProcessingStatus.dispatched,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [entry_id],
                EntryProcessingStatus.processed,
            )
        )

        statuses = await operations.get_entries_processing_statuses([fake_processor_id], [entry_id])

        assert statuses.get(fake_processor_id, {}) == {entry_id: EntryProcessingStatus.processed}

    @pytest.mark.asyncio
    async def test_updates_only_requested_processor_entries(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        third_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [first_entry_id, second_entry_id],
                EntryProcessingStatus.dispatched,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                another_fake_processor_id,
                [first_entry_id, second_entry_id],
                EntryProcessingStatus.failed,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [second_entry_id, third_entry_id],
                EntryProcessingStatus.processed,
            )
        )

        assert await operations.get_entries_processing_statuses(
            [fake_processor_id, another_fake_processor_id],
            [first_entry_id, second_entry_id, third_entry_id],
        ) == {
            fake_processor_id: {
                first_entry_id: EntryProcessingStatus.dispatched,
                second_entry_id: EntryProcessingStatus.processed,
                third_entry_id: EntryProcessingStatus.processed,
            },
            another_fake_processor_id: {
                first_entry_id: EntryProcessingStatus.failed,
                second_entry_id: EntryProcessingStatus.failed,
            },
        }


class TestRemoveEntryProcessingStatuses:
    @pytest.mark.asyncio
    async def test_empty_entries(self) -> None:
        await operations.remove_entry_processing_statuses([])

    @pytest.mark.asyncio
    async def test_removes_only_requested_entries(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        third_entry_id = new_entry_id()

        await operations.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [first_entry_id, second_entry_id, third_entry_id],
                EntryProcessingStatus.dispatched,
            )
        )
        await operations.set_entry_processing_statuses(
            make_status_updates(
                another_fake_processor_id,
                [first_entry_id, second_entry_id],
                EntryProcessingStatus.failed,
            )
        )

        await operations.remove_entry_processing_statuses([first_entry_id, second_entry_id])

        assert await operations.get_entries_processing_statuses(
            [fake_processor_id, another_fake_processor_id], [first_entry_id, second_entry_id, third_entry_id]
        ) == {
            fake_processor_id: {
                third_entry_id: EntryProcessingStatus.dispatched,
            },
            another_fake_processor_id: {},
        }
