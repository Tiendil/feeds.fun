import contextlib
from typing import Generator

import pytest
from pytest_mock import MockerFixture
from structlog.testing import capture_logs

from ffun.core.metrics import Accumulator
from ffun.core.tests.helpers import assert_logs
from ffun.dispatcher.entities import EntryProcessingStatus, ProcessorRouteId
from ffun.dispatcher.tests.helpers import assert_processing_status
from ffun.domain.entities import ProcessorId
from ffun.librarian import errors
from ffun.librarian.domain import (
    accumulator,
    process_entry,
)
from ffun.librarian.processors.base import (
    AlwaysConstantProcessor,
    AlwaysErrorProcessor,
    AlwaysSkipEntryProcessor,
    AlwaysTemporaryErrorProcessor,
    ProcessorContext,
)
from ffun.library.entities import Entry
from ffun.ontology import domain as o_domain

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

        await assert_processing_status(fake_processor_id, cataloged_entry.id, EntryProcessingStatus.processed)

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

        await assert_processing_status(fake_processor_id, cataloged_entry.id, EntryProcessingStatus.skipped)

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

        await assert_processing_status(fake_processor_id, cataloged_entry.id, EntryProcessingStatus.failed)

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

        await assert_processing_status(fake_processor_id, cataloged_entry.id, EntryProcessingStatus.failed)
