import pytest
from pytest_mock import MockerFixture
from structlog.testing import capture_logs

from ffun.core.tests.helpers import assert_logs
from ffun.dispatcher import domain as d_domain
from ffun.dispatcher.entities import (
    EntryToProcess,
    EntryToTag,
    ProcessorDispatchInfo,
    ProcessorDispatchRoute,
    ProcessorRouteId,
)
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import ProcessorId
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
    def processor_info(
        self,
        *,
        routes: tuple[ProcessorDispatchRoute, ...],
        processor_id: ProcessorId = ProcessorId(101),
        concurrency: int = 5,
        quality_route_id: ProcessorRouteId | None = None,
    ) -> background_processors.ProcessorInfo:
        return background_processors.ProcessorInfo(
            id=processor_id,
            type=ProcessorType.fake,
            processor=AlwaysConstantProcessor(name="fake_processor", tags=["tag"]),
            concurrency=concurrency,
            routes=routes,
            quality_route_id=quality_route_id,
        )

    @pytest.mark.parametrize(
        "allowed_for_collections, allowed_for_users",
        [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ],
    )
    def test_disptach_info__success(
        self,
        allowed_for_collections: bool,
        allowed_for_users: bool,
    ) -> None:
        expected_routes = (
            ProcessorDispatchRoute(
                id=ProcessorRouteId("default"),
                allowed_for_collections=allowed_for_collections,
                allowed_for_users=allowed_for_users,
            ),
        )

        processor_info = self.processor_info(routes=expected_routes)

        dispatch_info = processor_info.disptach_info()

        assert dispatch_info == ProcessorDispatchInfo(
            processor_id=ProcessorId(101),
            subqueue_id=ProcessorId(101),
            routes=expected_routes,
        )

    def test_init__stores_route_ids(self) -> None:
        processor_info = self.processor_info(
            routes=(
                ProcessorDispatchRoute(
                    id=ProcessorRouteId("default"),
                    allowed_for_collections=True,
                    allowed_for_users=True,
                ),
                ProcessorDispatchRoute(
                    id=ProcessorRouteId("fallback"),
                    allowed_for_collections=False,
                    allowed_for_users=True,
                ),
            ),
        )

        route_ids = processor_info.route_ids

        assert route_ids == {ProcessorRouteId("default"), ProcessorRouteId("fallback")}

    def test_init__stores_quality_route_id(self) -> None:
        processor_info = self.processor_info(
            routes=(
                ProcessorDispatchRoute(
                    id=ProcessorRouteId("default"),
                    allowed_for_collections=True,
                    allowed_for_users=True,
                ),
                ProcessorDispatchRoute(
                    id=ProcessorRouteId("quality-route"),
                    allowed_for_collections=False,
                    allowed_for_users=False,
                ),
            ),
            quality_route_id=ProcessorRouteId("quality-route"),
        )

        assert processor_info.quality_route_id == ProcessorRouteId("quality-route")


class TestEntriesProcessor:
    @pytest.mark.asyncio
    async def test_filter_records_with_known_routes__known_route_returns_records(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 2)
        entries_ids = list(entries)

        await d_domain.push_entries_to_tag(
            fake_entries_processor.id, entries_ids, route_id=ProcessorRouteId("default")
        )

        records = await d_domain.get_entries_to_tag(processor_id=fake_entries_processor.id, limit=100)

        with capture_logs() as logs:  # type: ignore
            records_to_process = await fake_entries_processor.filter_records_with_known_routes(records)

        assert_logs(logs, unknown_processor_route_in_queue=0)  # type: ignore

        process_records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert {record.item.entry_id for record in records_to_process} == set(entries_ids)
        assert process_records == []

        await d_domain.acknowledge([record.id for record in records if record.id is not None])

    @pytest.mark.asyncio
    async def test_filter_records_with_known_routes__mixed_routes_requeues_unknown_records(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 4)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        known_route_entries = entries_list[:2]
        unknown_route_entries = entries_list[2:]

        await d_domain.push_entries_to_tag(
            fake_entries_processor.id,
            [entry.id for entry in known_route_entries],
            route_id=ProcessorRouteId("default"),
        )
        await d_domain.push_entries_to_tag(
            fake_entries_processor.id,
            [entry.id for entry in unknown_route_entries],
            route_id=ProcessorRouteId("unknown-route"),
        )

        records = await d_domain.get_entries_to_tag(processor_id=fake_entries_processor.id, limit=100)

        with capture_logs() as logs:  # type: ignore
            records_to_process = await fake_entries_processor.filter_records_with_known_routes(records)

        assert_logs(logs, unknown_processor_route_in_queue=len(unknown_route_entries))  # type: ignore

        process_records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert {record.item.entry_id for record in records_to_process} == {entry.id for entry in known_route_entries}
        assert {record.item.entry_id for record in process_records} == {entry.id for entry in unknown_route_entries}
        assert {record.item.processor_id for record in process_records} == {fake_entries_processor.id}

        await d_domain.acknowledge([record.id for record in records if record.id is not None])

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
    async def test_single_run__unknown_route_acknowledges_records(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 1)
        entry = next(iter(entries.values()))

        await d_domain.push_entries_to_tag(
            fake_entries_processor.id,
            [entry.id],
            route_id=ProcessorRouteId("unknown-route"),
        )

        await fake_entries_processor.single_run()

        tagged_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=fake_entries_processor.id
        )
        process_records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert tagged_records == []
        assert {record.item.entry_id for record in process_records} == {entry.id}

    @pytest.mark.asyncio
    async def test_single_run__entries_more_than_concurrency(
        self, fake_entries_processor: EntriesProcessor, loaded_feed: Feed
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_entries_processor.id)

        entries = await l_make.n_entries(loaded_feed, 9)
        entries_list = list(entries.values())
        entries_list.sort(key=_entry_sort_key)

        await d_domain.push_entries_to_tag(
            fake_entries_processor.id, [entry.id for entry in entries_list], route_id=ProcessorRouteId("default")
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
            fake_entries_processor.id, [entry.id for entry in entries_list], route_id=ProcessorRouteId("default")
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
            route_id=ProcessorRouteId("default"),
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
