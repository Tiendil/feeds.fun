import pytest
from structlog.testing import capture_logs

from ffun.core import utils
from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_logs
from ffun.feeds.entities import Feed
from ffun.librarian import errors, operations
from ffun.librarian.domain import (
    move_failed_entries_to_processor_queue,
    plan_processor_queue,
    process_entry,
    push_entries_and_move_pointer,
)
from ffun.librarian.entities import ProcessorPointer
from ffun.librarian.processors.base import AlwaysConstantProcessor, AlwaysErrorProcessor, AlwaysSkipEntryProcessor
from ffun.librarian.tests import helpers, make
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make
from ffun.ontology import domain as o_domain


class TestPushEntriesAndMovePointer:
    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: int) -> None:
        pointer = await operations.get_or_create_pointer(fake_processor_id)

        async with TableSizeNotChanged("ln_processors_queue"):
            await push_entries_and_move_pointer(pointer, [])

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == pointer

    @pytest.mark.asyncio
    async def test_push_entries(
        self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry
    ) -> None:
        original_pointer = await operations.get_or_create_pointer(fake_processor_id)

        entries = [cataloged_entry, another_cataloged_entry]
        entries.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        last_entry = entries[-1]

        next_pointer = ProcessorPointer(
            processor_id=fake_processor_id, pointer_created_at=last_entry.cataloged_at, pointer_entry_id=last_entry.id
        )

        async with TableSizeDelta("ln_processors_queue", delta=2):
            await push_entries_and_move_pointer(next_pointer, [cataloged_entry.id, another_cataloged_entry.id])

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == next_pointer
        assert loaded_pointer != original_pointer

    @pytest.mark.asyncio
    async def test_no_new_entries(self, fake_processor_id: int) -> None:
        pointer = await make.end_processor_pointer(fake_processor_id)

        next_pointer = pointer.replace(pointer_created_at=utils.now())

        async with TableSizeNotChanged("ln_processors_queue"):
            await push_entries_and_move_pointer(next_pointer, [])

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == next_pointer

    @pytest.mark.asyncio
    async def test_entries_found_and_moved(
        self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry
    ) -> None:
        entries = [cataloged_entry, another_cataloged_entry]
        entries.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        pointer = await make.end_processor_pointer(fake_processor_id)

        async with TableSizeDelta("ln_processors_queue", delta=2):
            await push_entries_and_move_pointer(pointer, [cataloged_entry.id, another_cataloged_entry.id])

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == pointer


class TestPlanProcessorQueue:
    @pytest.mark.asyncio
    async def test_no_new_entries(self, fake_processor_id: int, cataloged_entry: Entry) -> None:
        pointer = await make.end_processor_pointer(fake_processor_id)

        async with TableSizeNotChanged("ln_processors_queue"):
            await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=100)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == pointer

    @pytest.mark.asyncio
    async def test_move_pointer_to_the_end(self, loaded_feed: Feed, fake_processor_id: int) -> None:
        await make.end_processor_pointer(1)

        entries = await l_make.n_entries(loaded_feed, 3)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        async with TableSizeDelta("ln_processors_queue", delta=3):
            await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=100)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == ProcessorPointer(
            processor_id=fake_processor_id,
            pointer_created_at=entries_list[-1].cataloged_at,
            pointer_entry_id=entries_list[-1].id,
        )

    @pytest.mark.asyncio
    async def test_move_pointer_to_not_the_end(self, loaded_feed: Feed, fake_processor_id: int) -> None:
        await make.end_processor_pointer(1)

        entries = await l_make.n_entries(loaded_feed, 3)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        async with TableSizeDelta("ln_processors_queue", delta=2):
            await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=2)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == ProcessorPointer(
            processor_id=fake_processor_id,
            pointer_created_at=entries_list[-2].cataloged_at,
            pointer_entry_id=entries_list[-2].id,
        )

    @pytest.mark.asyncio
    async def test_chunk_limit(self, loaded_feed: Feed, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        await make.end_processor_pointer(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed, 5)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        async with TableSizeDelta("ln_processors_queue", delta=3):
            await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=3)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == ProcessorPointer(
            processor_id=fake_processor_id,
            pointer_created_at=entries_list[2].cataloged_at,
            pointer_entry_id=entries_list[2].id,
        )

    @pytest.mark.asyncio
    async def test_do_not_push_if_there_are_enough_entries(self, loaded_feed: Feed, fake_processor_id: int) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        await make.end_processor_pointer(fake_processor_id)

        entries = await l_make.n_entries(loaded_feed, 5)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        await plan_processor_queue(fake_processor_id, fill_when_below=100500, chunk=3)

        async with TableSizeNotChanged("ln_processors_queue"):
            await plan_processor_queue(fake_processor_id, fill_when_below=3, chunk=2)

        loaded_pointer = await operations.get_or_create_pointer(fake_processor_id)

        assert loaded_pointer == ProcessorPointer(
            processor_id=fake_processor_id,
            pointer_created_at=entries_list[2].cataloged_at,
            pointer_entry_id=entries_list[2].id,
        )


class TestProcessEntry:
    @pytest.mark.asyncio
    async def test_success(
        self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry
    ) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        await operations.push_entries_to_processor_queue(
            execute, processor_id=fake_processor_id, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )

        with capture_logs() as logs:
            await process_entry(
                processor_id=fake_processor_id,
                processor=AlwaysConstantProcessor(name="fake-processor", tags=["tag-1", "tag-2"]),
                entry=cataloged_entry,
            )

        assert_logs(logs, processor_successed=1, processor_requested_to_skip_entry=0, entry_processed=1)

        tags = await o_domain.get_tags_ids_for_entries([cataloged_entry.id])

        expected_ids = await o_domain.get_ids_by_uids({"tag-1", "tag-2"})

        assert tags[cataloged_entry.id] == set(expected_ids.values())

        entries_in_queue = await operations.get_entries_to_process(processor_id=fake_processor_id, limit=100500)

        assert set(entries_in_queue) == {another_cataloged_entry.id}

        failed_entry_ids = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)
        assert cataloged_entry.id not in failed_entry_ids

    @pytest.mark.asyncio
    async def test_skip_processing(
        self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry
    ) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        await operations.push_entries_to_processor_queue(
            execute, processor_id=fake_processor_id, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )

        with capture_logs() as logs:
            await process_entry(
                processor_id=fake_processor_id,
                processor=AlwaysSkipEntryProcessor(name="fake-processor"),
                entry=cataloged_entry,
            )

        assert_logs(logs, processor_successed=0, processor_requested_to_skip_entry=1, entry_processed=1)

        tags = await o_domain.get_tags_ids_for_entries([cataloged_entry.id])

        assert cataloged_entry.id not in tags

        entries_in_queue = await operations.get_entries_to_process(processor_id=fake_processor_id, limit=100500)

        assert set(entries_in_queue) == {another_cataloged_entry.id}

        failed_entry_ids = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)
        assert cataloged_entry.id not in failed_entry_ids

    @pytest.mark.asyncio
    async def test_unexpected_error(
        self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry
    ) -> None:
        await operations.clear_processor_queue(fake_processor_id)

        await operations.push_entries_to_processor_queue(
            execute, processor_id=fake_processor_id, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )

        with capture_logs() as logs:
            with pytest.raises(errors.UnexpectedErrorInProcessor):
                await process_entry(
                    processor_id=fake_processor_id,
                    processor=AlwaysErrorProcessor(name="fake-processor"),
                    entry=cataloged_entry,
                )

        assert_logs(logs, processor_successed=0, processor_requested_to_skip_entry=0, entry_processed=0)

        tags = await o_domain.get_tags_ids_for_entries([cataloged_entry.id])

        assert cataloged_entry.id not in tags

        entries_in_queue = await operations.get_entries_to_process(processor_id=fake_processor_id, limit=100500)

        assert set(entries_in_queue) == {another_cataloged_entry.id}

        failed_entry_ids = await operations.get_failed_entries(execute, fake_processor_id, limit=100500)
        assert cataloged_entry.id in failed_entry_ids


class TestMoveFailedEntriesToProcessorQueue:
    @pytest.mark.asyncio
    async def test_moved(
        self,
        fake_processor_id: int,
        another_fake_processor_id: int,
        cataloged_entry: Entry,
        another_cataloged_entry: Entry,
    ) -> None:
        await helpers.clean_failed_storage([fake_processor_id, another_fake_processor_id])
        await operations.clear_processor_queue(fake_processor_id)
        await operations.clear_processor_queue(another_fake_processor_id)

        await operations.add_entries_to_failed_storage(
            fake_processor_id, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )
        await operations.add_entries_to_failed_storage(
            another_fake_processor_id, entry_ids=[another_cataloged_entry.id]
        )

        async with TableSizeDelta("ln_processors_queue", delta=2):
            await move_failed_entries_to_processor_queue(fake_processor_id, limit=100500)

        entries_in_queue = await operations.get_entries_to_process(processor_id=fake_processor_id, limit=100500)

        assert set(entries_in_queue) == {cataloged_entry.id, another_cataloged_entry.id}

        async with TableSizeDelta("ln_processors_queue", delta=1):
            await move_failed_entries_to_processor_queue(another_fake_processor_id, limit=100500)

        entries_in_queue = await operations.get_entries_to_process(
            processor_id=another_fake_processor_id, limit=100500
        )

        assert set(entries_in_queue) == {another_cataloged_entry.id}

    @pytest.mark.asyncio
    async def test_limit(self, fake_processor_id: int, cataloged_entry: Entry, another_cataloged_entry: Entry) -> None:
        await helpers.clean_failed_storage([fake_processor_id])
        await operations.clear_processor_queue(fake_processor_id)

        await operations.add_entries_to_failed_storage(
            fake_processor_id, entry_ids=[cataloged_entry.id, another_cataloged_entry.id]
        )

        async with TableSizeDelta("ln_processors_queue", delta=1):
            await move_failed_entries_to_processor_queue(fake_processor_id, limit=1)

        entries_in_queue = await operations.get_entries_to_process(processor_id=fake_processor_id, limit=100500)

        assert set(entries_in_queue) == {cataloged_entry.id}
