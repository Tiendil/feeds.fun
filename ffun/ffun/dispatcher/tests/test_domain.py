from collections.abc import Sequence
from random import choice

import pytest
from pytest_mock import MockerFixture

from ffun.dispatcher import domain
from ffun.dispatcher.entities import (
    DispatchDecision,
    EntryToProcess,
    EntryToTag,
    ProcessorDispatchInfo,
    ProcessorDispatchRoute,
)
from ffun.dispatcher.tests import make
from ffun.domain.domain import new_entry_id
from ffun.domain.entities import EntryId, ProcessorId
from ffun.feeds.entities import Feed
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.llms_framework.entities import LLMApiKeyType
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
    async def test_push_entries_for_processor(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id(), new_entry_id()]
        processor_id = ProcessorId(101)

        await domain.push_entries_to_process(entry_ids, processor_id=processor_id)

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)
        assert {record.item.processor_id for record in records} == {processor_id}


class TestGetEntriesToTag:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        processor_id = ProcessorId(101)

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=processor_id)

        assert await domain.get_entries_to_tag(processor_id=processor_id, limit=10) == []

    @pytest.mark.asyncio
    async def test_get_entries_from_processor_subqueue(self) -> None:
        processor_id = ProcessorId(101)
        another_processor_id = ProcessorId(102)

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=processor_id)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=another_processor_id)

        entry_ids = [new_entry_id(), new_entry_id()]
        another_entry_ids = [new_entry_id()]

        await domain.push_entries_to_tag(processor_id, entry_ids, llm_api_key_type=None)
        await domain.push_entries_to_tag(another_processor_id, another_entry_ids, llm_api_key_type=None)

        records = await domain.get_entries_to_tag(processor_id=processor_id, limit=10)

        assert record_entry_ids(records) == set(entry_ids)


class TestPushEntriesToTag:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        processor_id = ProcessorId(101)

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=processor_id)

        await domain.push_entries_to_tag(processor_id, [], llm_api_key_type=None)

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=processor_id
        )

        assert records == []

    @pytest.mark.parametrize("llm_api_key_type", [None, *LLMApiKeyType])
    @pytest.mark.asyncio
    async def test_push_entries_to_processor_subqueue(self, llm_api_key_type: LLMApiKeyType | None) -> None:
        processor_id = ProcessorId(101)
        another_processor_id = ProcessorId(102)

        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=processor_id)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag, secondary_id=another_processor_id)

        entry_ids = [new_entry_id(), new_entry_id()]

        await domain.push_entries_to_tag(processor_id, entry_ids, llm_api_key_type=llm_api_key_type)

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=processor_id
        )
        another_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=another_processor_id
        )

        assert record_entry_ids(records) == set(entry_ids)
        assert {record.item.llm_api_key_type for record in records} == {llm_api_key_type}
        assert another_records == []


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


class TestProcessorDispatchRoute:
    @pytest.mark.parametrize(
        "in_collection, routes, expected_route_index",
        [
            (
                True,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=False,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.user,
                    ),
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.general,
                    ),
                ],
                1,
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=False,
                        llm_api_key_type=LLMApiKeyType.collection,
                    ),
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.general,
                    ),
                ],
                1,
            ),
            (
                True,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=False,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.user,
                    )
                ],
                None,
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=False,
                        llm_api_key_type=LLMApiKeyType.collection,
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
        "in_collection, routes, expected_key_type",
        [
            (
                True,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=False,
                        llm_api_key_type=LLMApiKeyType.collection,
                    )
                ],
                LLMApiKeyType.collection,
            ),
            (
                True,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=False,
                        llm_api_key_type=LLMApiKeyType.collection,
                    ),
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.general,
                    ),
                ],
                LLMApiKeyType.collection,
            ),
            (
                True,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.general,
                    )
                ],
                LLMApiKeyType.general,
            ),
            (
                True,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=False,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.user,
                    )
                ],
                None,
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=False,
                        llm_api_key_type=LLMApiKeyType.collection,
                    ),
                    make.processor_dispatch_route(
                        allowed_for_collections=False,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.user,
                    ),
                ],
                LLMApiKeyType.user,
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=True,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.general,
                    ),
                    make.processor_dispatch_route(
                        allowed_for_collections=False,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.user,
                    ),
                ],
                LLMApiKeyType.general,
            ),
            (
                False,
                [
                    make.processor_dispatch_route(
                        allowed_for_collections=False,
                        allowed_for_users=True,
                        llm_api_key_type=LLMApiKeyType.user,
                    )
                ],
                LLMApiKeyType.user,
            ),
        ],
    )
    def test_llm_key_type_selection(
        self,
        in_collection: bool,
        routes: list[ProcessorDispatchRoute],
        expected_key_type: LLMApiKeyType | None,
    ) -> None:
        item = EntryToProcess(entry_id=new_entry_id())
        processor = make.processor_dispatch_info(
            101,
            routes=routes,
        )

        decision = domain._processor_dispatch_decision(processor, item, in_collection=in_collection)

        if expected_key_type is None:
            assert decision is None
            return

        assert decision is not None
        assert decision.llm_api_key_type == expected_key_type

    def test_non_llm_processor_has_no_key_type(self) -> None:
        item = EntryToProcess(entry_id=new_entry_id())
        processor = make.processor_dispatch_info(101)

        assert processor.routes[0].llm_api_key_type is None

        decision = domain._processor_dispatch_decision(processor, item, in_collection=False)

        assert decision == DispatchDecision(llm_api_key_type=None)


class TestProcessorItemsToTag:
    def test_keeps_allowed_items_and_skips_rejected_items(self) -> None:
        first_entry_id = new_entry_id()
        second_entry_id = new_entry_id()
        third_entry_id = new_entry_id()
        processor = make.processor_dispatch_info(
            101,
            routes=[
                make.processor_dispatch_route(
                    allowed_for_collections=False,
                    allowed_for_users=True,
                    llm_api_key_type=LLMApiKeyType.user,
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

        items_to_tag = domain._processor_items_to_tag(processor, items, entries_in_collections)

        assert items_to_tag == [
            EntryToTag(entry_id=first_entry_id, llm_api_key_type=LLMApiKeyType.user),
            EntryToTag(entry_id=third_entry_id, llm_api_key_type=LLMApiKeyType.user),
        ]

    def test_keeps_only_items_targeted_to_processor(self) -> None:
        processor = make.processor_dispatch_info(101)
        target_entry_id = new_entry_id()
        other_entry_id = new_entry_id()
        common_entry_id = new_entry_id()

        items = [
            EntryToProcess(entry_id=target_entry_id, processor_id=processor.processor_id),
            EntryToProcess(entry_id=other_entry_id, processor_id=ProcessorId(processor.processor_id + 1)),
            EntryToProcess(entry_id=common_entry_id, processor_id=None),
        ]

        items_to_tag = domain._processor_items_to_tag(processor, items, entries_in_collections={})

        assert items_to_tag == [
            EntryToTag(entry_id=target_entry_id, llm_api_key_type=None),
            EntryToTag(entry_id=common_entry_id, llm_api_key_type=None),
        ]


class TestDispatchEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        dispatched = await domain.dispatch_entries(processors=[make.processor_dispatch_info(101)], limit=10)

        assert dispatched == 0

    @pytest.mark.asyncio
    async def test_dispatch_to_each_processor_subqueue(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        processor_ids = [101, 102]

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
    async def test_dispatch_to_target_processor_subqueue(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        llm_api_key_type = choice(list(LLMApiKeyType))
        target_processor = make.processor_dispatch_info(
            101,
            routes=[
                make.processor_dispatch_route(
                    allowed_for_collections=True,
                    allowed_for_users=True,
                    llm_api_key_type=llm_api_key_type,
                )
            ],
        )
        other_processor = make.processor_dispatch_info(102)

        await domain.push_entries_to_process(entry_ids, processor_id=target_processor.processor_id)

        dispatched = await domain.dispatch_entries(processors=[target_processor, other_processor], limit=10)

        assert dispatched == len(entry_ids)

        target_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=target_processor.subqueue_id
        )
        other_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=other_processor.subqueue_id
        )

        assert record_entry_ids(target_records) == set(entry_ids)
        assert {record.item.llm_api_key_type for record in target_records} == {llm_api_key_type}
        assert other_records == []

    @pytest.mark.asyncio
    async def test_targeted_dispatch_respects_processor_routes(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        user_entry_ids = await l_make.n_entries(loaded_feed, 2)
        collection_entry_ids = await l_make.n_entries(another_loaded_feed, 2)
        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)

        entry_ids = [*user_entry_ids, *collection_entry_ids]
        processor = make.processor_dispatch_info(
            101,
            routes=[
                make.processor_dispatch_route(
                    allowed_for_collections=True,
                    allowed_for_users=False,
                    llm_api_key_type=None,
                )
            ],
        )

        await domain.push_entries_to_process(entry_ids, processor_id=processor.processor_id)

        dispatched = await domain.dispatch_entries(processors=[processor], limit=10)

        assert dispatched == len(entry_ids)
        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.subqueue_id
        )

        assert record_entry_ids(records) == set(collection_entry_ids)

    @pytest.mark.asyncio
    async def test_dispatch_saves_llm_api_key_type(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        llm_api_key_type = choice(list(LLMApiKeyType))
        processor = make.processor_dispatch_info(
            101,
            routes=[
                make.processor_dispatch_route(
                    allowed_for_collections=True,
                    allowed_for_users=True,
                    llm_api_key_type=llm_api_key_type,
                )
            ],
        )

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[processor], limit=10)

        assert dispatched == len(entry_ids)

        records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.subqueue_id
        )

        assert record_entry_ids(records) == set(entry_ids)
        assert {record.item.llm_api_key_type for record in records} == {llm_api_key_type}

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
    async def test_limit(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id(), new_entry_id()]
        processor_id = ProcessorId(101)

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[make.processor_dispatch_info(processor_id)], limit=2)

        assert dispatched == 2

        dispatched_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=processor_id
        )
        remaining_records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert len(dispatched_records) == 2
        assert len(remaining_records) == 1
        assert record_entry_ids(dispatched_records) | record_entry_ids(remaining_records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_uses_processor_dispatch_decision(self, mocker: MockerFixture) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id() for _ in range(5)]
        first_processor = make.processor_dispatch_info(101)
        second_processor = make.processor_dispatch_info(102)
        processors = [first_processor, second_processor]

        allowed = {
            (first_processor.processor_id, entry_ids[0]),
            (first_processor.processor_id, entry_ids[2]),
            (second_processor.processor_id, entry_ids[2]),
            (second_processor.processor_id, entry_ids[1]),
        }
        calls: list[tuple[ProcessorId, EntryId]] = []

        def dispatch_decision(
            processor: ProcessorDispatchInfo, item: EntryToProcess, *, in_collection: bool
        ) -> DispatchDecision | None:
            processor_id = processor.processor_id
            calls.append((processor_id, item.entry_id))

            if (processor_id, item.entry_id) not in allowed:
                return None

            return DispatchDecision()

        mocker.patch.object(domain, "_processor_dispatch_decision", side_effect=dispatch_decision)

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=processors, limit=10)

        assert dispatched == len(entry_ids)
        assert set(calls) == {(processor.processor_id, entry_id) for processor in processors for entry_id in entry_ids}

        first_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=first_processor.subqueue_id
        )
        second_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=second_processor.subqueue_id
        )

        assert record_entry_ids(first_records) == {entry_ids[0], entry_ids[2]}
        assert record_entry_ids(second_records) == {entry_ids[1], entry_ids[2]}

    @pytest.mark.asyncio
    async def test_dispatch_uses_processor_subqueue_id(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        entry_ids = [new_entry_id(), new_entry_id()]
        processor = make.processor_dispatch_info(101, subqueue_id=201)

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[processor], limit=10)

        assert dispatched == len(entry_ids)
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
