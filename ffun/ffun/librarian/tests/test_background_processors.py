import datetime
import uuid
from itertools import chain

import pytest
from ffun.core import utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_logs
from ffun.librarian import errors, operations
from ffun.librarian.background_processors import EntriesProcessor
from ffun.librarian.domain import plan_processor_queue, process_entry, push_entries_and_move_pointer
from ffun.librarian.entities import ProcessorPointer
from ffun.librarian.processors.base import AlwaysConstantProcessor, AlwaysErrorProcessor, AlwaysSkipEntryProcessor
from ffun.librarian.tests import make
from ffun.library import operations as l_operations
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make
from ffun.ontology import domain as o_domain
from structlog.testing import capture_logs


class TestEntriesProcessors:

    @pytest.mark.asyncio
    async def test_no_entries_to_process(self, fake_entries_processor: EntriesProcessor) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=1)

    @pytest.mark.asyncio
    async def test_entries_more_than_concurrency(self, fake_entries_processor: EntriesProcessor, loaded_feed_id: int) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed_id, 5)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        assert fake_entries_processor.concurrency < len(entries)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0)

        tags = await o_domain.get_tags_for_entries(list(entries))

        for entry in entries_list[:fake_entries_processor.concurrency]:
            assert tags[entry.id] == {'fake-constant-tag-1', 'fake-constant-tag-2'}

        for entry in entries_list[fake_entries_processor.concurrency:]:
            assert tags[entry.id] == set()

    @pytest.mark.asyncio
    async def test_entries_less_than_concurrency(self, fake_entries_processor: EntriesProcessor, loaded_feed_id: int) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed_id, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        assert fake_entries_processor.concurrency > len(entries)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0)

        tags = await o_domain.get_tags_for_entries(list(entries))

        for entry in entries_list:
            assert tags[entry.id] == {'fake-constant-tag-1', 'fake-constant-tag-2'}
