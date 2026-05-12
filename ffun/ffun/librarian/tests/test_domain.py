import contextlib
from typing import Generator

import pytest
from pytest_mock import MockerFixture
from structlog.testing import capture_logs

from ffun.core.metrics import Accumulator
from ffun.core.postgresql import execute
from ffun.core.tests.helpers import assert_logs
from ffun.dispatcher import domain as d_domain
from ffun.dispatcher.entities import EntryToProcess, ProcessorRouteId
from ffun.domain.entities import EntryId, ProcessorId
from ffun.librarian import errors, operations
from ffun.librarian.domain import (
    accumulator,
    move_failed_entries_to_processor_queue,
    process_entry,
)
from ffun.librarian.processors.base import (
    AlwaysConstantProcessor,
    AlwaysErrorProcessor,
    AlwaysSkipEntryProcessor,
    AlwaysTemporaryErrorProcessor,
    ProcessorContext,
)
from ffun.librarian.tests import helpers
from ffun.library.entities import Entry
from ffun.ontology import domain as o_domain
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind

TEST_ROUTE_ID = ProcessorRouteId("test-route")


@contextlib.contextmanager
def check_metric_accumulator(
    processor_id: ProcessorId, name: str, count_delta: int, sum_delta: int
) -> Generator[None, None, None]:

    metric = accumulator(name, processor_id)

    old_count = metric.count
    old_sum = metric.sum

    yield

    assert metric.count == old_count + count_delta
    assert metric.sum == old_sum + sum_delta


@contextlib.contextmanager
def check_metric_accumulators(
    mocker: MockerFixture, processor_id: ProcessorId, raw_count: int, raw_sum: int, norm_count: int, norm_sum: int
) -> Generator[None, None, None]:

    raw_tags_metric = accumulator("processor_raw_tags", processor_id)
    normalized_tags_metric = accumulator("processor_normalized_tags", processor_id)

    called_for = []

    def patch_flush(self: Accumulator) -> None:
        called_for.append(self)

    # Disable normalizers to measure calls only of processors' metrics.
    # Attention: we overwrite value imported into the domain module, not the original one.
    mocker.patch("ffun.tags.domain.normalizers", [])

    mocker.patch("ffun.core.metrics.Accumulator.flush_if_time", patch_flush)

    with (
        check_metric_accumulator(processor_id, "processor_raw_tags", raw_count, raw_sum),
        check_metric_accumulator(processor_id, "processor_normalized_tags", norm_count, norm_sum),
    ):
        yield

    assert len(called_for) == 2
    assert raw_tags_metric in called_for
    assert normalized_tags_metric in called_for


class TestProcessEntry:
    @pytest.mark.asyncio
    async def test_success(
        self, fake_processor_id: ProcessorId, cataloged_entry: Entry, mocker: MockerFixture
    ) -> None:
        with capture_logs() as logs, check_metric_accumulators(mocker, fake_processor_id, 1, 3, 1, 2):  # type: ignore
            await process_entry(
                processor_id=fake_processor_id,
                processor=AlwaysConstantProcessor(name="fake-processor", tags=["tag-1", "tag-2", "tag--2"]),
                entry=cataloged_entry,
                context=ProcessorContext(route_id=TEST_ROUTE_ID),
            )

        assert_logs(
            logs,  # type: ignore
            processor_successed=1,
            processor_requested_to_skip_entry=0,
            entry_processed=1,
        )

        tags = await o_domain.get_tags_ids_for_entries([cataloged_entry.id])

        expected_ids = await o_domain.get_ids_by_uids({"tag-1", "tag-2"})  # type: ignore

        assert tags[cataloged_entry.id] == set(expected_ids.values())

        failed_entry_ids = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)
        assert cataloged_entry.id not in failed_entry_ids

    @pytest.mark.asyncio
    async def test_skip_processing(
        self, fake_processor_id: ProcessorId, cataloged_entry: Entry, mocker: MockerFixture
    ) -> None:
        with capture_logs() as logs, check_metric_accumulators(mocker, fake_processor_id, 0, 0, 0, 0):  # type: ignore
            await process_entry(
                processor_id=fake_processor_id,
                processor=AlwaysSkipEntryProcessor(name="fake-processor"),
                entry=cataloged_entry,
                context=ProcessorContext(route_id=TEST_ROUTE_ID),
            )

        assert_logs(
            logs,  # type: ignore
            processor_successed=0,
            processor_requested_to_skip_entry=1,
            entry_processed=1,
            processor_temporary_error=0,
        )

        tags = await o_domain.get_tags_ids_for_entries([cataloged_entry.id])

        assert cataloged_entry.id not in tags

        failed_entry_ids = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)
        assert cataloged_entry.id not in failed_entry_ids

    @pytest.mark.asyncio
    async def test_temporary_error_in_processor(
        self, fake_processor_id: ProcessorId, cataloged_entry: Entry, mocker: MockerFixture
    ) -> None:
        with capture_logs() as logs, check_metric_accumulators(mocker, fake_processor_id, 0, 0, 0, 0):  # type: ignore
            await process_entry(
                processor_id=fake_processor_id,
                processor=AlwaysTemporaryErrorProcessor(name="fake-processor"),
                entry=cataloged_entry,
                context=ProcessorContext(route_id=TEST_ROUTE_ID),
            )

        assert_logs(
            logs,  # type: ignore
            processor_successed=0,
            processor_requested_to_skip_entry=0,
            entry_processed=1,
            processor_temporary_error=1,
        )

        tags = await o_domain.get_tags_ids_for_entries([cataloged_entry.id])

        assert cataloged_entry.id not in tags

        failed_entry_ids = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)
        assert cataloged_entry.id in failed_entry_ids

    @pytest.mark.asyncio
    async def test_unexpected_error(
        self, fake_processor_id: ProcessorId, cataloged_entry: Entry, mocker: MockerFixture
    ) -> None:
        with capture_logs() as logs, check_metric_accumulators(mocker, fake_processor_id, 0, 0, 0, 0):  # type: ignore
            with pytest.raises(errors.UnexpectedErrorInProcessor):
                await process_entry(
                    processor_id=fake_processor_id,
                    processor=AlwaysErrorProcessor(name="fake-processor"),
                    entry=cataloged_entry,
                    context=ProcessorContext(route_id=TEST_ROUTE_ID),
                )

        assert_logs(
            logs,  # type: ignore
            processor_successed=0,
            processor_requested_to_skip_entry=0,
            entry_processed=0,
            processor_temporary_error=0,
        )

        tags = await o_domain.get_tags_ids_for_entries([cataloged_entry.id])

        assert cataloged_entry.id not in tags

        failed_entry_ids = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)
        assert cataloged_entry.id in failed_entry_ids


class TestMoveFailedEntriesToProcessorQueue:
    async def get_entries_to_process(self, processor_id: ProcessorId) -> set[EntryId]:
        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        processor_records = [record for record in records if record.item.processor_id == processor_id]
        entries_in_queue = {record.item.entry_id for record in processor_records}

        await d_domain.acknowledge([record.id for record in processor_records if record.id is not None])

        return entries_in_queue

    async def get_failed_entries(self, processor_id: ProcessorId) -> set[EntryId]:
        return set(await operations.get_failed_entries(execute, processor_id, limit=100500))

    @pytest.mark.asyncio
    async def test_no_failed_entries(self, fake_processor_id: ProcessorId) -> None:
        await helpers.clean_failed_storage([fake_processor_id])
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_processor_id)

        await move_failed_entries_to_processor_queue(fake_processor_id, limit=100500)

        assert await self.get_entries_to_process(fake_processor_id) == set()
        assert await self.get_failed_entries(fake_processor_id) == set()

    @pytest.mark.asyncio
    async def test_moved(
        self,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
    ) -> None:
        await helpers.clean_failed_storage([fake_processor_id, another_fake_processor_id])
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_processor_id)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=another_fake_processor_id)

        await operations.add_entries_to_failed_storage(
            fake_processor_id, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )
        await operations.add_entries_to_failed_storage(
            another_fake_processor_id, entry_ids=[another_cataloged_entry.id]
        )

        await move_failed_entries_to_processor_queue(fake_processor_id, limit=100500)

        assert await self.get_entries_to_process(fake_processor_id) == {
            cataloged_entry.id,
            another_cataloged_entry.id,
        }
        assert await self.get_failed_entries(fake_processor_id) == set()

        assert await self.get_entries_to_process(another_fake_processor_id) == set()
        assert await self.get_failed_entries(another_fake_processor_id) == {another_cataloged_entry.id}

        await move_failed_entries_to_processor_queue(another_fake_processor_id, limit=100500)

        assert await self.get_entries_to_process(another_fake_processor_id) == {another_cataloged_entry.id}
        assert await self.get_failed_entries(another_fake_processor_id) == set()

    @pytest.mark.asyncio
    async def test_limit(
        self, fake_processor_id: ProcessorId, cataloged_entry: Entry, another_cataloged_entry: Entry
    ) -> None:
        await helpers.clean_failed_storage([fake_processor_id])
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_processor_id)

        await operations.add_entries_to_failed_storage(
            fake_processor_id, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )

        await move_failed_entries_to_processor_queue(fake_processor_id, limit=1)

        all_entry_ids = {cataloged_entry.id, another_cataloged_entry.id}

        moved_entries = await self.get_entries_to_process(fake_processor_id)

        assert len(moved_entries) == 1
        assert moved_entries <= all_entry_ids

        failed_entries = await self.get_failed_entries(fake_processor_id)

        assert failed_entries == all_entry_ids - moved_entries

        await move_failed_entries_to_processor_queue(fake_processor_id, limit=100500)

        assert await self.get_entries_to_process(fake_processor_id) == failed_entries
        assert await self.get_failed_entries(fake_processor_id) == set()
