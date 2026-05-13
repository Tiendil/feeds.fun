from collections.abc import Sequence

import pytest
import pytest_asyncio

from ffun.core.tests.helpers import TableSizeNotChanged
from ffun.dispatcher import domain, errors, operations
from ffun.dispatcher.entities import (
    DispatchDecision,
    EntryProcessingStatus,
    EntryToProcess,
    EntryToTag,
    ProcessorDispatchRoute,
    ProcessorRouteId,
)
from ffun.dispatcher.tests import make
from ffun.dispatcher.tests.helpers import assert_processing_status
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import EntryId, ProcessorId
from ffun.feeds.entities import Feed
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.markers import domain as m_domain
from ffun.markers.entities import Marker
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind, QueueRecord


def record_entry_ids(records: Sequence[QueueRecord[EntryToProcess] | QueueRecord[EntryToTag]]) -> set[EntryId]:
    return {record.item.entry_id for record in records}


class TestPushEntriesToProcess:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        await domain.push_entries_to_process([])

        assert await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess) == []

    @pytest.mark.asyncio
    async def test_push_entries(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id(), new_entry_id()]

        await domain.push_entries_to_process(entry_ids)

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)
        assert {record.item.processor_id for record in records} == {None}

    @pytest.mark.asyncio
    async def test_push_entries_for_processor(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id(), new_entry_id()]

        await domain.push_entries_to_process(entry_ids, processor_id=fake_processor_id)

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)
        assert {record.item.processor_id for record in records} == {fake_processor_id}


class TestGetEntriesToTag:
    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_processor_id)

        assert await domain.get_entries_to_tag(processor_id=fake_processor_id, limit=10) == []

    @pytest.mark.asyncio
    async def test_get_entries_from_processor_subqueue(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_processor_id)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=another_fake_processor_id)

        entry_ids = [new_entry_id(), new_entry_id()]
        another_entry_ids = [new_entry_id()]

        await domain.push_entries_to_tag(fake_processor_id, entry_ids, route_id=ProcessorRouteId("default"))
        await domain.push_entries_to_tag(
            another_fake_processor_id, another_entry_ids, route_id=ProcessorRouteId("default")
        )

        records = await domain.get_entries_to_tag(processor_id=fake_processor_id, limit=10)

        assert record_entry_ids(records) == set(entry_ids)


class TestPushEntriesToTag:
    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_processor_id)

        await domain.push_entries_to_tag(fake_processor_id, [], route_id=ProcessorRouteId("default"))

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=fake_processor_id
        )

        assert records == []

    @pytest.mark.asyncio
    async def test_push_entries_to_processor_subqueue(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        route_id = ProcessorRouteId("test-route")

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=fake_processor_id)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=another_fake_processor_id)

        entry_ids = [new_entry_id(), new_entry_id()]

        await domain.push_entries_to_tag(fake_processor_id, entry_ids, route_id=route_id)

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=fake_processor_id
        )
        another_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=another_fake_processor_id
        )

        assert record_entry_ids(records) == set(entry_ids)
        assert {record.item.route_id for record in records} == {route_id}
        assert another_records == []


class TestGetEntriesProcessingStatuses:
    def test_reexports_operation(self) -> None:
        assert domain.get_entries_processing_statuses is operations.get_entries_processing_statuses


class TestGetEntriesByProcessingStatus:
    def test_reexports_operation(self) -> None:
        assert domain.get_entries_by_processing_status is operations.get_entries_by_processing_status


class TestCountEntriesByProcessingStatus:
    def test_reexports_operation(self) -> None:
        assert domain.count_entries_by_processing_status is operations.count_entries_by_processing_status


class TestSetEntryProcessingStatuses:
    def test_reexports_operation(self) -> None:
        assert domain.set_entry_processing_statuses is operations.set_entry_processing_statuses


class TestRemoveEntryProcessingStatuses:
    def test_reexports_operation(self) -> None:
        assert domain.remove_entry_processing_statuses is operations.remove_entry_processing_statuses


class TestAcknowledge:
    @pytest.mark.asyncio
    async def test_no_records(self) -> None:
        assert await domain.acknowledge([]) == 0

    @pytest.mark.asyncio
    async def test_acknowledge_records(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id(), new_entry_id(), new_entry_id()]

        await domain.push_entries_to_process(entry_ids)

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)
        records_to_acknowledge = records[:2]
        records_to_keep = records[2:]

        assert await domain.acknowledge([record.id for record in records_to_acknowledge if record.id is not None]) == 2

        records_after_acknowledgement = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_process, EntryToProcess
        )

        assert record_entry_ids(records_after_acknowledgement) == record_entry_ids(records_to_keep)


class TestMoveFailedEntriesToProcessorQueue:
    @pytest_asyncio.fixture(autouse=True)  # type: ignore
    async def prepare_processing_statuses(self) -> None:
        await operations.tech_truncate_entry_processing_statuses()

    async def get_entries_to_process(self, processor_id: ProcessorId) -> set[EntryId]:
        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        processor_records = [record for record in records if record.item.processor_id == processor_id]

        return {record.item.entry_id for record in processor_records}

    @pytest.mark.parametrize(
        "status",
        [status for status in EntryProcessingStatus if status != EntryProcessingStatus.failed],
    )
    @pytest.mark.asyncio
    async def test_no_failed_entries(self, fake_processor_id: ProcessorId, status: EntryProcessingStatus) -> None:
        entry_id = new_entry_id()

        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await domain.set_entry_processing_statuses(fake_processor_id, [entry_id], status)

        await domain.move_failed_entries_to_processor_queue(fake_processor_id, limit=100500)

        assert await self.get_entries_to_process(fake_processor_id) == set()
        assert (
            await domain.get_entries_by_processing_status(
                fake_processor_id, EntryProcessingStatus.failed, limit=100500
            )
            == []
        )
        await assert_processing_status(fake_processor_id, entry_id, status)

    @pytest.mark.asyncio
    async def test_moved(self, fake_processor_id: ProcessorId) -> None:
        failed_entry_id = new_entry_id()
        processed_entry_id = new_entry_id()

        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await domain.set_entry_processing_statuses(
            fake_processor_id,
            [failed_entry_id],
            EntryProcessingStatus.failed,
        )
        await domain.set_entry_processing_statuses(
            fake_processor_id,
            [processed_entry_id],
            EntryProcessingStatus.processed,
        )

        await domain.move_failed_entries_to_processor_queue(fake_processor_id, limit=100500)

        assert await self.get_entries_to_process(fake_processor_id) == {failed_entry_id}
        assert (
            await domain.get_entries_by_processing_status(
                fake_processor_id, EntryProcessingStatus.failed, limit=100500
            )
            == []
        )
        await assert_processing_status(fake_processor_id, failed_entry_id, EntryProcessingStatus.retry_requested)
        await assert_processing_status(fake_processor_id, processed_entry_id, EntryProcessingStatus.processed)

    @pytest.mark.asyncio
    async def test_limit(self, fake_processor_id: ProcessorId) -> None:
        entry_ids = [new_entry_id(), new_entry_id(), new_entry_id(), new_entry_id()]

        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await domain.set_entry_processing_statuses(
            fake_processor_id,
            entry_ids,
            EntryProcessingStatus.failed,
        )

        await domain.move_failed_entries_to_processor_queue(fake_processor_id, limit=2)

        all_entry_ids = set(entry_ids)
        moved_entries = await self.get_entries_to_process(fake_processor_id)

        assert len(moved_entries) == 2
        assert moved_entries <= all_entry_ids

        failed_entries = set(
            await domain.get_entries_by_processing_status(
                fake_processor_id, EntryProcessingStatus.failed, limit=100500
            )
        )

        assert failed_entries == all_entry_ids - moved_entries

        for entry_id in moved_entries:
            await assert_processing_status(fake_processor_id, entry_id, EntryProcessingStatus.retry_requested)

        for entry_id in failed_entries:
            await assert_processing_status(fake_processor_id, entry_id, EntryProcessingStatus.failed)

        await domain.move_failed_entries_to_processor_queue(fake_processor_id, limit=100500)

        assert await self.get_entries_to_process(fake_processor_id) == all_entry_ids
        assert (
            await domain.get_entries_by_processing_status(
                fake_processor_id, EntryProcessingStatus.failed, limit=100500
            )
            == []
        )


class TestEntriesInCollections:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        assert await domain._entries_in_collections([]) == {}

    @pytest.mark.asyncio
    async def test_returns_collection_membership(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        user_entries = await l_make.n_entries(loaded_feed, 2)
        collection_entries = await l_make.n_entries(another_loaded_feed, 3)

        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_in_collections = await domain._entries_in_collections(list(user_entries) + list(collection_entries))

        assert entries_in_collections == {
            **{entry_id: False for entry_id in user_entries},
            **{entry_id: True for entry_id in collection_entries},
        }

    @pytest.mark.asyncio
    async def test_returns_collection_membership_for_entries_linked_to_multiple_feeds(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed, 3)

        await l_domain.catalog_entries(
            another_loaded_feed.id,
            [entry.collected_entry() for entry in entries[:2]],
        )
        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entries_in_collections = await domain._entries_in_collections([entry.id for entry in entries])

        assert entries_in_collections == {
            entries[0].id: True,
            entries[1].id: True,
            entries[2].id: False,
        }

    @pytest.mark.asyncio
    async def test_skips_entries_without_feed_links(self) -> None:
        entry_id = new_entry_id()

        assert await domain._entries_in_collections([entry_id]) == {}


class TestMarkEntryTagsVisible:
    @pytest.mark.asyncio
    async def test_collection_entry(self) -> None:
        entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)

        await domain._mark_entry_tags_visible(item, in_collection=True)

        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}

    @pytest.mark.asyncio
    async def test_user_entry_temporary_global_marker(self) -> None:
        entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)

        await domain._mark_entry_tags_visible(item, in_collection=False)

        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}


class TestMarkEntriesTagsVisible:
    @pytest.mark.asyncio
    async def test_no_items(self) -> None:
        async with TableSizeNotChanged("m_markers"):
            await domain._mark_entries_tags_visible([], {})

    @pytest.mark.asyncio
    async def test_marks_items_with_explicit_and_default_collection_flags(self) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        third_entry_id = new_entry_id()
        items = [
            EntryToProcess(entry_id=first_entry_id),
            EntryToProcess(entry_id=second_entry_id),
            EntryToProcess(entry_id=third_entry_id),
        ]

        await domain._mark_entries_tags_visible(
            items,
            {
                first_entry_id: True,
                second_entry_id: False,
            },
        )

        assert await m_domain.get_markers(
            user_id=None, entries_ids=[first_entry_id, second_entry_id, third_entry_id]
        ) == {
            first_entry_id: {Marker.can_see_tags},
            second_entry_id: {Marker.can_see_tags},
            third_entry_id: {Marker.can_see_tags},
        }


class TestProcessorDispatchRoute:
    @pytest.mark.parametrize(
        "in_collection, routes, expected_route_index",
        [
            (
                True,
                [
                    make.processor_dispatch_route(
                        id="user-route",
                        allowed_for_collections=False,
                        allowed_for_users=True,
                    ),
                    make.processor_dispatch_route(
                        id="shared-route",
                        allowed_for_collections=True,
                        allowed_for_users=True,
                    ),
                ],
                1,
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        id="collection-route",
                        allowed_for_collections=True,
                        allowed_for_users=False,
                    ),
                    make.processor_dispatch_route(
                        id="shared-route",
                        allowed_for_collections=True,
                        allowed_for_users=True,
                    ),
                ],
                1,
            ),
            (
                True,
                [
                    make.processor_dispatch_route(
                        id="user-route",
                        allowed_for_collections=False,
                        allowed_for_users=True,
                    )
                ],
                None,
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        id="collection-route",
                        allowed_for_collections=True,
                        allowed_for_users=False,
                    )
                ],
                None,
            ),
        ],
    )
    def test_selects_first_route_allowed_for_entry_source(
        self,
        in_collection: bool,
        routes: list[ProcessorDispatchRoute],
        expected_route_index: int | None,
    ) -> None:
        processor = make.processor_dispatch_info(101, routes=routes)

        route = domain._processor_dispatch_route(processor, in_collection=in_collection)

        if expected_route_index is None:
            assert route is None
            return

        assert route == routes[expected_route_index]


class TestProcessorDispatchDecision:
    @pytest.mark.parametrize(
        "in_collection, routes, expected_route_id",
        [
            (
                True,
                [
                    make.processor_dispatch_route(
                        id="collection-route",
                        allowed_for_collections=True,
                        allowed_for_users=False,
                    )
                ],
                ProcessorRouteId("collection-route"),
            ),
            (
                True,
                [
                    make.processor_dispatch_route(
                        id="collection-route",
                        allowed_for_collections=True,
                        allowed_for_users=False,
                    ),
                    make.processor_dispatch_route(
                        id="shared-route",
                        allowed_for_collections=True,
                        allowed_for_users=True,
                    ),
                ],
                ProcessorRouteId("collection-route"),
            ),
            (
                True,
                [
                    make.processor_dispatch_route(
                        id="shared-route",
                        allowed_for_collections=True,
                        allowed_for_users=True,
                    )
                ],
                ProcessorRouteId("shared-route"),
            ),
            (
                True,
                [
                    make.processor_dispatch_route(
                        id="user-route",
                        allowed_for_collections=False,
                        allowed_for_users=True,
                    )
                ],
                None,
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        id="collection-route",
                        allowed_for_collections=True,
                        allowed_for_users=False,
                    ),
                    make.processor_dispatch_route(
                        id="user-route",
                        allowed_for_collections=False,
                        allowed_for_users=True,
                    ),
                ],
                ProcessorRouteId("user-route"),
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        id="shared-route",
                        allowed_for_collections=True,
                        allowed_for_users=True,
                    ),
                    make.processor_dispatch_route(
                        id="user-route",
                        allowed_for_collections=False,
                        allowed_for_users=True,
                    ),
                ],
                ProcessorRouteId("shared-route"),
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        id="user-route",
                        allowed_for_collections=False,
                        allowed_for_users=True,
                    )
                ],
                ProcessorRouteId("user-route"),
            ),
        ],
    )
    def test_route_id_selection(
        self,
        in_collection: bool,
        routes: list[ProcessorDispatchRoute],
        expected_route_id: ProcessorRouteId | None,
        fake_processor_id: ProcessorId,
    ) -> None:
        item = EntryToProcess(entry_id=new_entry_id())
        processor = make.processor_dispatch_info(
            fake_processor_id,
            routes=routes,
        )

        decision = domain._processor_dispatch_decision(processor, item, in_collection=in_collection)

        if expected_route_id is None:
            assert decision is None
            return

        assert decision is not None
        assert decision.route_id == expected_route_id

    def test_processor_dispatch_uses_route_id(self, fake_processor_id: ProcessorId) -> None:
        item = EntryToProcess(entry_id=new_entry_id())
        processor = make.processor_dispatch_info(fake_processor_id)

        assert processor.routes[0].id == ProcessorRouteId("default")

        decision = domain._processor_dispatch_decision(processor, item, in_collection=False)

        assert decision == DispatchDecision(route_id=ProcessorRouteId("default"))


class TestProcessorItemsToTag:
    def test_keeps_allowed_items_and_skips_rejected_items(self, fake_processor_id: ProcessorId) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        third_entry_id = new_entry_id()
        processor = make.processor_dispatch_info(
            fake_processor_id,
            routes=[
                make.processor_dispatch_route(
                    id="user-route",
                    allowed_for_collections=False,
                    allowed_for_users=True,
                )
            ],
        )
        items = [
            EntryToProcess(entry_id=first_entry_id),
            EntryToProcess(entry_id=second_entry_id),
            EntryToProcess(entry_id=third_entry_id),
        ]
        entries_in_collections = {
            first_entry_id: False,
            second_entry_id: True,
        }

        items_to_tag, skipped_entry_ids = domain._processor_items_to_tag(processor, items, entries_in_collections)

        assert items_to_tag == [
            EntryToTag(entry_id=first_entry_id, route_id=ProcessorRouteId("user-route")),
            EntryToTag(entry_id=third_entry_id, route_id=ProcessorRouteId("user-route")),
        ]
        assert skipped_entry_ids == [second_entry_id]


class TestProcessorItemsTargetedToProcessor:
    def test_no_items(self, fake_processor_id: ProcessorId) -> None:
        processor = make.processor_dispatch_info(fake_processor_id)

        assert domain._processor_items_targeted_to_processor(processor, []) == []

    def test_keeps_only_items_targeted_to_processor(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        processor = make.processor_dispatch_info(fake_processor_id)
        target_entry_id = new_entry_id()
        other_entry_id = new_entry_id()
        common_entry_id = new_entry_id()

        items = [
            EntryToProcess(entry_id=target_entry_id, processor_id=processor.processor_id),
            EntryToProcess(entry_id=other_entry_id, processor_id=another_fake_processor_id),
            EntryToProcess(entry_id=common_entry_id, processor_id=None),
        ]

        processor_items = domain._processor_items_targeted_to_processor(processor, items)

        assert processor_items == [
            EntryToProcess(entry_id=target_entry_id, processor_id=processor.processor_id),
            EntryToProcess(entry_id=common_entry_id, processor_id=None),
        ]


class TestProcessorItemsAllowedByStatus:
    def test_all_processing_statuses_are_classified(self) -> None:
        allowed_statuses = {
            EntryProcessingStatus.skipped_by_processor,
            EntryProcessingStatus.skipped_by_dispatcher,
            EntryProcessingStatus.retry_requested,
        }
        blocked_statuses = {
            EntryProcessingStatus.dispatched,
            EntryProcessingStatus.processed,
            EntryProcessingStatus.failed,
        }

        assert set(EntryProcessingStatus) == allowed_statuses | blocked_statuses

    def test_no_items(self) -> None:
        assert domain._processor_items_allowed_by_status([], {}) == []

    def test_allows_items_without_status(self) -> None:
        entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)

        assert domain._processor_items_allowed_by_status([item], {}) == [item]

    @pytest.mark.parametrize(
        "status",
        [
            EntryProcessingStatus.skipped_by_processor,
            EntryProcessingStatus.skipped_by_dispatcher,
            EntryProcessingStatus.retry_requested,
        ],
    )
    def test_allows_items_with_status_that_requires_redispatch(self, status: EntryProcessingStatus) -> None:
        entry_id = new_entry_id()
        blocked_entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)
        blocked_item = EntryToProcess(entry_id=blocked_entry_id)

        assert domain._processor_items_allowed_by_status(
            [item, blocked_item],
            {
                entry_id: status,
                blocked_entry_id: EntryProcessingStatus.dispatched,
            },
        ) == [item]

    @pytest.mark.parametrize(
        "status",
        [
            EntryProcessingStatus.dispatched,
            EntryProcessingStatus.processed,
            EntryProcessingStatus.failed,
        ],
    )
    def test_skips_items_with_final_or_in_progress_status(self, status: EntryProcessingStatus) -> None:
        entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)

        assert domain._processor_items_allowed_by_status([item], {entry_id: status}) == []


class TestDispatchEntriesToProcessor:
    @pytest_asyncio.fixture(autouse=True)  # type: ignore
    async def prepare_processing_statuses(self) -> None:
        await operations.tech_truncate_entry_processing_statuses()

    @pytest.mark.asyncio
    async def test_no_items(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        processor = make.processor_dispatch_info(fake_processor_id)

        await domain._dispatch_entries_to_processor(
            processor=processor,
            items=[],
            entries_in_collections={},
            statuses={},
        )

        assert (
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.subqueue_id
            )
            == []
        )
        assert await domain.get_entries_processing_statuses([processor.processor_id], []) == {
            processor.processor_id: {}
        }

    @pytest.mark.asyncio
    async def test_dispatches_items_to_processor_subqueue(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        route_id = ProcessorRouteId("custom-route")
        processor = make.processor_dispatch_info(
            fake_processor_id,
            subqueue_id=another_fake_processor_id,
            routes=[
                make.processor_dispatch_route(
                    id=route_id,
                    allowed_for_collections=True,
                    allowed_for_users=True,
                )
            ],
        )

        await domain._dispatch_entries_to_processor(
            processor=processor,
            items=[EntryToProcess(entry_id=entry_id) for entry_id in entry_ids],
            entries_in_collections={},
            statuses={},
        )

        assert (
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.processor_id
            )
            == []
        )

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.subqueue_id
        )

        assert record_entry_ids(records) == set(entry_ids)
        assert {record.item.route_id for record in records} == {route_id}

        processing_statuses = await domain.get_entries_processing_statuses([processor.processor_id], entry_ids)

        assert processing_statuses.get(processor.processor_id, {}) == {
            entry_id: EntryProcessingStatus.dispatched for entry_id in entry_ids
        }

    @pytest.mark.asyncio
    async def test_marks_entries_without_allowed_route_as_skipped_by_dispatcher(
        self, fake_processor_id: ProcessorId
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_id = new_entry_id()
        processor = make.processor_dispatch_info(
            fake_processor_id, allowed_for_collections=True, allowed_for_users=False
        )

        await domain._dispatch_entries_to_processor(
            processor=processor,
            items=[EntryToProcess(entry_id=entry_id)],
            entries_in_collections={},
            statuses={},
        )

        assert (
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.subqueue_id
            )
            == []
        )
        await assert_processing_status(processor.processor_id, entry_id, EntryProcessingStatus.skipped_by_dispatcher)

    @pytest.mark.asyncio
    async def test_ignores_entries_targeted_elsewhere(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        target_entry_id = new_entry_id()
        common_entry_id = new_entry_id()
        other_processor_entry_id = new_entry_id()
        processor = make.processor_dispatch_info(fake_processor_id)

        await domain._dispatch_entries_to_processor(
            processor=processor,
            items=[
                EntryToProcess(entry_id=target_entry_id, processor_id=processor.processor_id),
                EntryToProcess(entry_id=common_entry_id),
                EntryToProcess(entry_id=other_processor_entry_id, processor_id=another_fake_processor_id),
            ],
            entries_in_collections={},
            statuses={},
        )

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.subqueue_id
        )

        assert record_entry_ids(records) == {target_entry_id, common_entry_id}

        processing_statuses = await domain.get_entries_processing_statuses(
            [processor.processor_id],
            [target_entry_id, common_entry_id, other_processor_entry_id],
        )

        assert processing_statuses.get(processor.processor_id, {}) == {
            target_entry_id: EntryProcessingStatus.dispatched,
            common_entry_id: EntryProcessingStatus.dispatched,
        }

    @pytest.mark.asyncio
    async def test_ignores_entries_blocked_by_status(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        allowed_entry_id = new_entry_id()
        failed_entry_id = new_entry_id()
        processor = make.processor_dispatch_info(fake_processor_id)
        statuses = {
            failed_entry_id: EntryProcessingStatus.failed,
        }

        await domain.set_entry_processing_statuses(
            processor.processor_id, [failed_entry_id], EntryProcessingStatus.failed
        )

        await domain._dispatch_entries_to_processor(
            processor=processor,
            items=[
                EntryToProcess(entry_id=allowed_entry_id),
                EntryToProcess(entry_id=failed_entry_id),
            ],
            entries_in_collections={},
            statuses=statuses,
        )

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.subqueue_id
        )

        assert record_entry_ids(records) == {allowed_entry_id}

        processing_statuses = await domain.get_entries_processing_statuses(
            [processor.processor_id],
            [allowed_entry_id, failed_entry_id],
        )

        assert processing_statuses.get(processor.processor_id, {}) == {
            allowed_entry_id: EntryProcessingStatus.dispatched,
            failed_entry_id: EntryProcessingStatus.failed,
        }


class TestDispatchEntries:
    @pytest_asyncio.fixture(autouse=True)  # type: ignore
    async def prepare_processing_statuses(self) -> None:
        await operations.tech_truncate_entry_processing_statuses()

    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)], limit=10
        )

        assert dispatched == 0

    @pytest.mark.asyncio
    async def test_dispatch_to_each_processor_subqueue(
        self, fake_processor_id: ProcessorId, another_fake_processor_id: ProcessorId
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        processor_ids = [fake_processor_id, another_fake_processor_id]

        await domain.push_entries_to_process(entry_ids)

        processors = [make.processor_dispatch_info(processor_id) for processor_id in processor_ids]
        dispatched = await domain.dispatch_entries(processors=processors, limit=10)

        assert dispatched == len(entry_ids)
        assert await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess) == []

        for processor_id in processor_ids:
            records = await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag, EntryToTag, secondary_id=processor_id
            )

            assert record_entry_ids(records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_dispatch_marks_entries_tags_visible(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        user_entry_ids = await l_make.n_entries(loaded_feed, 2)
        collection_entry_ids = await l_make.n_entries(another_loaded_feed, 2)
        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entry_ids = [*user_entry_ids, *collection_entry_ids]

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)], limit=10
        )

        assert dispatched == len(entry_ids)
        assert await m_domain.get_markers(user_id=None, entries_ids=entry_ids) == {
            entry_id: {Marker.can_see_tags} for entry_id in entry_ids
        }

    @pytest.mark.asyncio
    async def test_no_processors(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id()]

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[], limit=10)

        assert dispatched == 0

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_duplicated_processors(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id()]
        processor = make.processor_dispatch_info(fake_processor_id)

        await domain.push_entries_to_process(entry_ids)

        with pytest.raises(errors.DuplicatedProcessors):
            await domain.dispatch_entries(processors=[processor, processor], limit=10)

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_limit(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id(), new_entry_id()]

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)], limit=2
        )

        assert dispatched == 2

        dispatched_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=fake_processor_id
        )
        remaining_records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert len(dispatched_records) == 2
        assert len(remaining_records) == 1
        assert record_entry_ids(dispatched_records) | record_entry_ids(remaining_records) == set(entry_ids)
