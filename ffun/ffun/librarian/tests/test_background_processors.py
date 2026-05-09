import pytest
from pytest_mock import MockerFixture
from structlog.testing import capture_logs

from ffun.core.tests.helpers import assert_logs
from ffun.dispatcher import domain as d_domain
from ffun.dispatcher.entities import EntryToTag, ProcessorDispatchInfo, ProcessorDispatchRoute
from ffun.domain.domain import new_entry_id
from ffun.feeds.entities import Feed
from ffun.librarian import background_processors
from ffun.librarian.background_processors import EntriesProcessor
from ffun.librarian.entities import ProcessorType
from ffun.librarian.processors.base import AlwaysConstantProcessor
from ffun.library.entities import Entry
from ffun.library.tests import helpers as l_helpers
from ffun.library.tests import make as l_make
from ffun.ontology import domain as o_domain
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind


def _entry_sort_key(entry: Entry) -> tuple[object, object]:
    return (entry.created_at, entry.id)


def _feed_retention_sort_key(entry: Entry) -> tuple[object, object]:
    return (entry.published_at, entry.created_at)


class TestProcessorInfo:
    @pytest.mark.parametrize(
        "allowed_for_collections, allowed_for_users",
        [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ],
    )
    def test_disptach_info(
        self,
        allowed_for_collections: bool,
        allowed_for_users: bool,
    ) -> None:
        routes = (
            ProcessorDispatchRoute(
                allowed_for_collections=allowed_for_collections,
                allowed_for_users=allowed_for_users,
            ),
        )

        processor_info = background_processors.ProcessorInfo(
            id=101,
            type=ProcessorType.fake,
            processor=AlwaysConstantProcessor(name="fake_processor", tags=["tag"]),
            concurrency=5,
            routes=routes,
        )

        dispatch_info = processor_info.disptach_info()

        assert dispatch_info == ProcessorDispatchInfo(
            processor_id=101,
            subqueue_id=101,
            routes=routes,
        )


class TestEntriesProcessor:
    @pytest.mark.asyncio
    async def test_single_run__no_entries_to_process(self, fake_entries_processor: EntriesProcessor) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        with capture_logs() as logs:  # type: ignore
            await fake_entries_processor.single_run()

        assert_logs(
            logs,  # type: ignore
            no_entries_to_process=1,
            unexisted_entry_in_queue=0,
            entry_without_feeds_in_queue=0,
        )

    @pytest.mark.asyncio
    async def test_single_run__entries_more_than_concurrency(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 9)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        await d_domain.push_entries_to_tag(
            fake_entries_processor.id, [entry.id for entry in entries_list], llm_api_key_type=None
        )

        assert fake_entries_processor.concurrency <= len(entries)

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=fake_entries_processor.id
        )
        expected_processed_entries = {record.item.entry_id for record in records[: fake_entries_processor.concurrency]}
        expected_queued_entries = {record.item.entry_id for record in records[fake_entries_processor.concurrency :]}

        with capture_logs() as logs:  # type: ignore
            await fake_entries_processor.single_run()

        assert_logs(
            logs,  # type: ignore
            no_entries_to_process=0,
            unexisted_entry_in_queue=0,
            entry_without_feeds_in_queue=0,
        )

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})  # type: ignore

        assert len(tags) == fake_entries_processor.concurrency
        assert set(tags) == expected_processed_entries

        for tagged_entry_ids in tags.values():
            assert tagged_entry_ids == set(expected_ids.values())

        records = await d_domain.get_entries_to_tag(processor_id=fake_entries_processor.id, limit=100)

        assert {record.item.entry_id for record in records} == expected_queued_entries

        await d_domain.acknowledge([record.id for record in records if record.id is not None])

    @pytest.mark.asyncio
    async def test_single_run__entries_less_than_concurrency(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        await d_domain.push_entries_to_tag(
            fake_entries_processor.id, [entry.id for entry in entries_list], llm_api_key_type=None
        )

        assert fake_entries_processor.concurrency > len(entries)

        with capture_logs() as logs:  # type: ignore
            await fake_entries_processor.single_run()

        assert_logs(
            logs,  # type: ignore
            no_entries_to_process=0,
            unexisted_entry_in_queue=0,
            entry_without_feeds_in_queue=0,
        )

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})  # type: ignore

        for entry in entries_list:
            assert tags[entry.id] == set(expected_ids.values())

    @pytest.mark.asyncio
    async def test_single_run__unexisted_entries_in_queue(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        fake_entries_ids = [new_entry_id() for _ in range(3)]

        await d_domain.push_entries_to_tag(
            fake_entries_processor.id,
            [entry.id for entry in entries_list] + fake_entries_ids,
            llm_api_key_type=None,
        )

        assert fake_entries_processor.concurrency >= len(entries) + len(fake_entries_ids)

        with capture_logs() as logs:  # type: ignore
            await fake_entries_processor.single_run()

        assert_logs(
            logs,  # type: ignore
            no_entries_to_process=0,
            unexisted_entry_in_queue=3,
            entry_without_feeds_in_queue=0,
        )

        tags = await o_domain.get_tags_ids_for_entries(list(entries))

        expected_ids = await o_domain.get_ids_by_uids({"fake-constant-tag-1", "fake-constant-tag-2"})  # type: ignore

        for entry in entries_list:
            assert tags[entry.id] == set(expected_ids.values())

        records = await d_domain.get_entries_to_tag(processor_id=fake_entries_processor.id, limit=100)

        assert records == []

    @pytest.mark.asyncio
    async def test_separate_entries__unexisted_entries(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        entries = await l_make.n_entries(loaded_feed, 2)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        fake_entries_ids = [new_entry_id() for _ in range(3)]

        entries_ids = [entry.id for entry in entries_list] + fake_entries_ids

        with capture_logs() as logs:  # type: ignore
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,  # type: ignore
            no_entries_to_process=0,
            unexisted_entry_in_queue=3,
            entry_without_feeds_in_queue=0,
        )

        assert {entry.id for entry in entries_to_process} == {entry.id for entry in entries_list}
        assert set(entries_to_remove) == set(fake_entries_ids)

    @pytest.mark.asyncio
    async def test_separate_entries__entries_without_feeds_in_queue(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        entries = await l_make.n_entries(loaded_feed, 5)
        entries_list = list(entries.values())

        # remove the oldest entries from their only feed to simulate stale queue items
        entries_list.sort(key=_feed_retention_sort_key)
        await l_helpers.unlink_entries_from_feed(loaded_feed.id, [entry.id for entry in entries_list[:2]])

        entries_ids = [entry.id for entry in entries_list]

        with capture_logs() as logs:  # type: ignore
            entries_to_process, entries_to_remove = await fake_entries_processor.separate_entries(
                entries_ids=entries_ids
            )

        assert_logs(
            logs,  # type: ignore
            no_entries_to_process=0,
            unexisted_entry_in_queue=0,
            entry_without_feeds_in_queue=2,
        )

        assert {entry.id for entry in entries_to_process} == {entry.id for entry in entries_list[2:]}
        assert set(entries_to_remove) == {entry.id for entry in entries_list[:2]}


class TestCreateBackgroundProcessors:
    def test_no_processors(self, mocker: MockerFixture) -> None:
        mocker.patch.object(background_processors, "processors", [])

        assert background_processors.create_background_processors() == []

    def test_success(self, mocker: MockerFixture, fake_processor_info: background_processors.ProcessorInfo) -> None:
        mocker.patch.object(background_processors, "processors", [fake_processor_info])

        tasks = background_processors.create_background_processors()

        assert [task.name for task in tasks] == ["entries_dispatcher", "entries_processor_fake_constant_processor"]
