import uuid

import pytest
from structlog.testing import capture_logs

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import assert_logs
from ffun.feeds.entities import FeedId
from ffun.feeds_collections import domain as fc_domain
from ffun.librarian import operations
from ffun.librarian.background_processors import EntriesProcessor
from ffun.librarian.tests import make
from ffun.library.tests import make as l_make
from ffun.ontology import domain as o_domain


class TestEntriesProcessors:
    @pytest.mark.asyncio
    async def test_no_entries_to_process(self, fake_entries_processor: EntriesProcessor) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=1)

    @pytest.mark.asyncio
    async def test_entries_more_than_concurrency(
        self, fake_entries_processor: EntriesProcessor, loaded_feed_id: FeedId
    ) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed_id, 9)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        assert fake_entries_processor.concurrency <= len(entries)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0)

        tags = await o_domain.get_tags_for_entries(list(entries))

        for entry in entries_list[: fake_entries_processor.concurrency]:
            assert tags[entry.id] == {"fake-constant-tag-1", "fake-constant-tag-2"}

        for entry in entries_list[fake_entries_processor.concurrency :]:
            assert tags[entry.id] == set()

    @pytest.mark.asyncio
    async def test_entries_less_than_concurrency(
        self, fake_entries_processor: EntriesProcessor, loaded_feed_id: FeedId
    ) -> None:
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
            assert tags[entry.id] == {"fake-constant-tag-1", "fake-constant-tag-2"}

    @pytest.mark.asyncio
    async def test_unexisted_entries_in_queue(
        self, fake_entries_processor: EntriesProcessor, loaded_feed_id: FeedId
    ) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed_id, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        fake_entries_ids = [uuid.uuid4() for _ in range(3)]

        await operations.push_entries_to_processor_queue(
            execute, processor_id=fake_entries_processor.id, entry_ids=fake_entries_ids
        )

        assert fake_entries_processor.concurrency >= len(entries) + len(fake_entries_ids)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0, unexisted_entry_in_queue=3)

        tags = await o_domain.get_tags_for_entries(list(entries))

        for entry in entries_list:
            assert tags[entry.id] == {"fake-constant-tag-1", "fake-constant-tag-2"}

        entities_in_queue = await operations.get_entries_to_process(processor_id=fake_entries_processor.id, limit=100)

        assert entities_in_queue == []

    @pytest.mark.asyncio
    async def test_separate_entries__unexsisted_entries(
        self, fake_entries_processor: EntriesProcessor, loaded_feed_id: FeedId
    ) -> None:
        entries = await l_make.n_entries(loaded_feed_id, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        fake_entries_ids = [uuid.uuid4() for _ in range(3)]

        entries_ids = [entry.id for entry in entries_list] + fake_entries_ids

        with capture_logs() as logs:
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,
            unexisted_entry_in_queue=3,
            proccessor_not_allowed_for_collections=0,
            proccessor_not_allowed_for_users=0,
            proccessor_is_allowed_for_entry=2,
        )

        assert {entry.id for entry in entries_to_process} == {entry.id for entry in entries_list}
        assert set(entries_to_remove) == set(fake_entries_ids)

    @pytest.mark.asyncio
    async def test_separate_entries__collections_not_allowed(
        self, fake_entries_processor: EntriesProcessor, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId
    ) -> None:
        entries_1 = await l_make.n_entries(loaded_feed_id, 3)
        entries_2 = await l_make.n_entries(another_loaded_feed_id, 2)

        fc_domain.add_test_feed_to_collections(another_loaded_feed_id)

        entries_list = list(entries_1.values()) + list(entries_2.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        entries_ids = [entry.id for entry in entries_list]

        fake_entries_processor._processor_info.allowed_for_collections = False

        with capture_logs() as logs:
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,
            unexisted_entry_in_queue=0,
            proccessor_not_allowed_for_collections=2,
            proccessor_not_allowed_for_users=0,
            proccessor_is_allowed_for_entry=3,
        )

        assert {entry.id for entry in entries_to_process} == set(entries_1)
        assert set(entries_to_remove) == set(entries_2)

    @pytest.mark.asyncio
    async def test_separate_entries__all_allowed(
        self, fake_entries_processor: EntriesProcessor, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId
    ) -> None:
        entries_1 = await l_make.n_entries(loaded_feed_id, 3)
        entries_2 = await l_make.n_entries(another_loaded_feed_id, 2)

        fc_domain.add_test_feed_to_collections(another_loaded_feed_id)

        entries_list = list(entries_1.values()) + list(entries_2.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        entries_ids = [entry.id for entry in entries_list]

        fake_entries_processor._processor_info.allowed_for_collections = True
        fake_entries_processor._processor_info.allowed_for_users = True

        with capture_logs() as logs:
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,
            unexisted_entry_in_queue=0,
            proccessor_not_allowed_for_collections=0,
            proccessor_not_allowed_for_users=0,
            proccessor_is_allowed_for_entry=5,
        )

        assert {entry.id for entry in entries_to_process} == set(entries_1) | set(entries_2)

    @pytest.mark.asyncio
    async def test_separate_entries__users_not_allowed(
        self, fake_entries_processor: EntriesProcessor, loaded_feed_id: FeedId, another_loaded_feed_id: FeedId
    ) -> None:
        entries_1 = await l_make.n_entries(loaded_feed_id, 3)
        entries_2 = await l_make.n_entries(another_loaded_feed_id, 2)

        fc_domain.add_test_feed_to_collections(another_loaded_feed_id)

        entries_list = list(entries_1.values()) + list(entries_2.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        entries_ids = [entry.id for entry in entries_list]

        fake_entries_processor._processor_info.allowed_for_users = False

        with capture_logs() as logs:
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,
            unexisted_entry_in_queue=0,
            proccessor_not_allowed_for_collections=0,
            proccessor_not_allowed_for_users=3,
            proccessor_is_allowed_for_entry=2,
        )

        assert {entry.id for entry in entries_to_process} == set(entries_2)
        assert set(entries_to_remove) == set(entries_1)
