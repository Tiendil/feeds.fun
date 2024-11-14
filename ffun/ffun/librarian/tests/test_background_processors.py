import pytest
from structlog.testing import capture_logs

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import assert_logs
from ffun.domain.domain import new_entry_id
from ffun.feeds.entities import Feed
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.librarian import operations
from ffun.librarian.background_processors import EntriesProcessor
from ffun.librarian.tests import make
from ffun.library import domain as l_domain
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
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 9)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        assert fake_entries_processor.concurrency <= len(entries)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0)

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})

        for entry in entries_list[: fake_entries_processor.concurrency]:
            assert tags[entry.id] == set(expected_ids.values())

        for entry in entries_list[fake_entries_processor.concurrency :]:
            assert entry.id not in tags

    @pytest.mark.asyncio
    async def test_entries_less_than_concurrency(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        assert fake_entries_processor.concurrency > len(entries)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0)

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})

        for entry in entries_list:
            assert tags[entry.id] == set(expected_ids.values())

    @pytest.mark.asyncio
    async def test_unexisted_entries_in_queue(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await operations.clear_processor_queue(fake_entries_processor.id)
        await make.end_processor_pointer(fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        fake_entries_ids = [new_entry_id() for _ in range(3)]

        await operations.push_entries_to_processor_queue(
            execute, processor_id=fake_entries_processor.id, entry_ids=fake_entries_ids
        )

        assert fake_entries_processor.concurrency >= len(entries) + len(fake_entries_ids)

        with capture_logs() as logs:
            await fake_entries_processor.single_run()

        assert_logs(logs, no_entries_to_process=0, unexisted_entry_in_queue=3)

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})

        for entry in entries_list:
            assert tags[entry.id] == set(expected_ids.values())

        entities_in_queue = await operations.get_entries_to_process(processor_id=fake_entries_processor.id, limit=100)

        assert entities_in_queue == []

    @pytest.mark.asyncio
    async def test_separate_entries__unexsisted_entries(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=lambda entry: (entry.cataloged_at, entry.id))

        fake_entries_ids = [new_entry_id() for _ in range(3)]

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
    async def test_separate_entries__collections_not_allowed__entry_is_in_multiple_feeds(
        self,
        fake_entries_processor: EntriesProcessor,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        entries_1 = await l_make.n_entries_list(loaded_feed, 3)
        entries_2 = await l_make.n_entries_list(another_loaded_feed, 2)

        await l_domain.catalog_entries(another_loaded_feed.id, entries_1[:2])

        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_list = list(entries_1) + list(entries_2)
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
