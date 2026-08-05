import asyncio
import datetime
import uuid
from collections.abc import Mapping, Sequence
from typing import cast

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from ffun.audit.entities import AuditEntityKind
from ffun.core.tests.helpers import TableSizeNotChanged
from ffun.dispatcher import domain, entries_cache, errors, operations
from ffun.dispatcher.entities import (
    DispatchDecision,
    EntryAuthorization,
    EntryProcessingStatus,
    EntryProcessingStatusUpdate,
    EntryToProcess,
    EntryToTag,
    ProcessorDispatchInfo,
    ProcessorDispatchRoute,
    ProcessorRouteId,
)
from ffun.dispatcher.tests import make
from ffun.dispatcher.tests.helpers import assert_processing_status
from ffun.domain.datetime_intervals import (
    LIFETIME_INTERVAL_END_MARKER,
    LIFETIME_INTERVAL_START_MARKER,
    day_interval_start,
    month_interval_start,
)
from ffun.domain.domain import new_entry_id, new_user_id
from ffun.domain.entities import EntryId, ProcessorId, SerializedId, UserId
from ffun.entitlements import domain as e_domain
from ffun.entitlements.entities import EntitlementKindId, EntitlementTransactionId
from ffun.entitlements.tests import make as e_make
from ffun.feeds.entities import Feed
from ffun.feeds_collections.collections import collections
from ffun.feeds_collections.entities import CollectionId
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.llms_framework.entities import LLMApiKey
from ffun.markers import domain as m_domain
from ffun.markers.entities import Marker
from ffun.product.entities import Resource, UserSetting
from ffun.queues import domain as q_domain
from ffun.queues.entities import QueueItemToPush, QueueKind, QueueRecord, QueueRecordId, QueueSecondaryId
from ffun.resources import domain as r_domain
from ffun.resources.entities import ResourceReservation, ResourceReservationOption, ResourceReservationSpecification
from ffun.resources.tests.helpers import assert_no_resource_record, assert_resource_counters
from ffun.user_settings import domain as us_domain
from ffun.user_settings.entities import SettingKind


def record_entry_ids(records: Sequence[QueueRecord[EntryToProcess] | QueueRecord[EntryToTag]]) -> set[EntryId]:
    return {record.item.entry_id for record in records}


async def save_user_api_key(user_id: UserId) -> None:
    await us_domain.save_setting(
        user_id=user_id,
        kind=SettingKind(int(UserSetting.test_api_key)),
        value=LLMApiKey(uuid.uuid4().hex),
    )


async def grant_tokens(
    user_id: UserId,
    kind_id: EntitlementKindId,
    *,
    value: int = 10,
) -> None:
    await e_domain.grant_source_entitlement(
        e_make.make_source_entitlement(
            user_id=user_id,
            kind_id=kind_id,
            value=value,
            transaction_id=EntitlementTransactionId(uuid.uuid4().hex),
            expires_at=(LIFETIME_INTERVAL_END_MARKER if kind_id == EntitlementKindId.lifetime_tokens else None),
        ),
        actor_kind=AuditEntityKind.admin,
        actor_id=SerializedId("dispatcher-tests"),
    )


def make_entries_cache(
    *,
    entries_in_collections: set[EntryId] | None = None,
    processing_statuses: Mapping[ProcessorId, Mapping[EntryId, EntryProcessingStatus]] | None = None,
) -> entries_cache.EntriesCache:
    return entries_cache.EntriesCache(
        entries_in_collections=entries_in_collections or set(),
        feed_ids_by_entry={},
        user_ids_by_feed={},
        users_with_api_keys=set(),
        processing_statuses=processing_statuses or {},
        entitlements={},
    )


def make_entry_record(entry_id: EntryId) -> QueueRecord[EntryToProcess]:
    created_at = datetime.datetime.now(tz=datetime.UTC)

    return QueueRecord(
        id=QueueRecordId(uuid.uuid4()),
        primary_id=QueueKind.entries_to_process,
        priority=0,
        freezed_till=created_at,
        created_at=created_at,
        item=EntryToProcess(entry_id=entry_id),
    )


def make_status_updates(
    processor_id: ProcessorId,
    entry_ids: Sequence[EntryId],
    status: EntryProcessingStatus,
) -> list[EntryProcessingStatusUpdate]:
    return [
        EntryProcessingStatusUpdate(
            processor_id=processor_id,
            entry_id=entry_id,
            status=status,
        )
        for entry_id in entry_ids
    ]


async def enqueue_entries_to_process(entry_ids: Sequence[EntryId]) -> None:
    await q_domain.push(
        QueueKind.entries_to_process,
        [QueueItemToPush(item=EntryToProcess(entry_id=entry_id)) for entry_id in entry_ids],
    )


class TestGetEntriesDispatchingStatuses:
    def test_reexports_operation(self) -> None:
        assert domain.get_entries_dispatching_statuses is operations.get_entries_dispatching_statuses


class TestSetEntryDispatchingStatuses:
    def test_reexports_operation(self) -> None:
        assert domain.set_entry_dispatching_statuses is operations.set_entry_dispatching_statuses


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


class TestRemoveEntryDispatchingStatuses:
    def test_reexports_operation(self) -> None:
        assert domain.remove_entry_dispatching_statuses is operations.remove_entry_dispatching_statuses


class TestRemoveEntryProcessingStatuses:
    def test_reexports_operation(self) -> None:
        assert domain.remove_entry_processing_statuses is operations.remove_entry_processing_statuses


class TestEntriesInCollections:
    def test_reexports_entries_cache(self) -> None:
        assert domain.entries_in_collections is entries_cache.entries_in_collections


class TestMoveFailedEntriesToProcessorQueue:
    @pytest_asyncio.fixture(autouse=True)  # type: ignore
    async def prepare_processing_statuses(self) -> None:
        await operations.tech_truncate_entry_processing_statuses()

    async def get_entries_to_process(self, processor_id: ProcessorId) -> set[EntryId]:
        records = await q_domain.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        processor_records = [record for record in records if record.item.processor_id == processor_id]

        return {record.item.entry_id for record in processor_records}

    @pytest.mark.parametrize(
        "status",
        [status for status in EntryProcessingStatus if status != EntryProcessingStatus.failed],
    )
    @pytest.mark.asyncio
    async def test_no_failed_entries(self, fake_processor_id: ProcessorId, status: EntryProcessingStatus) -> None:
        entry_id = new_entry_id()

        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await domain.set_entry_processing_statuses(make_status_updates(fake_processor_id, [entry_id], status))

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

        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await domain.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [failed_entry_id],
                EntryProcessingStatus.failed,
            )
        )
        await domain.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [processed_entry_id],
                EntryProcessingStatus.processed,
            )
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

        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await domain.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                entry_ids,
                EntryProcessingStatus.failed,
            )
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


class TestTokenReservationSpecification:
    def test_builds_ordered_limits(self) -> None:
        user_id = new_user_id()
        entitlements = {
            kind_id: e_make.make_effective_entitlement_interval(
                user_id=user_id,
                kind_id=kind_id,
                value=index,
            )
            for index, kind_id in enumerate(EntitlementKindId, start=10)
        }

        specification = domain._token_reservation_specification(
            user_id,
            entitlements,
        )

        assert specification == ResourceReservationSpecification(
            user_id=user_id,
            limits=(10, 11, 12),
        )

    def test_marks_missing_entitlements_unavailable(self) -> None:
        user_id = new_user_id()

        specification = domain._token_reservation_specification(
            user_id,
            {kind_id: None for kind_id in EntitlementKindId},
        )

        assert specification.limits == (None, None, None)


class TestTokenReservationOptions:
    def test_builds_ordered_options(self) -> None:
        authorization_time = datetime.datetime.now(tz=datetime.UTC)

        options = domain._token_reservation_options(authorization_time)

        assert options == (
            ResourceReservationOption(
                kind=Resource.day_token_usage,
                interval_started_at=day_interval_start(authorization_time),
            ),
            ResourceReservationOption(
                kind=Resource.month_token_usage,
                interval_started_at=month_interval_start(authorization_time),
            ),
            ResourceReservationOption(
                kind=Resource.lifetime_token_usage,
                interval_started_at=LIFETIME_INTERVAL_START_MARKER,
            ),
        )


class TestAuthorizeEntry:
    @pytest.mark.asyncio
    async def test_collection_entry(
        self,
        another_loaded_feed: Feed,
        collection_id_for_test_feeds: CollectionId,
    ) -> None:
        user_id = new_user_id()
        entry = next(iter((await l_make.n_entries(another_loaded_feed, 1)).values()))
        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)
        await fl_domain.add_link(user_id, another_loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        item = EntryToProcess(entry_id=entry.id)
        cache = await entries_cache.create_entries_cache(
            [item],
            [],
            entitlement_kind_ids=list(EntitlementKindId),
        )

        authorization = await domain._authorize_entry(item, cache)

        assert authorization == EntryAuthorization(
            entry_id=entry.id,
            globally_visible=True,
            reservations=(),
        )

    @pytest.mark.asyncio
    async def test_linked_user_with_api_key(self, loaded_feed: Feed) -> None:
        user_id = new_user_id()
        entry = next(iter((await l_make.n_entries(loaded_feed, 1)).values()))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)
        item = EntryToProcess(entry_id=entry.id)
        cache = await entries_cache.create_entries_cache(
            [item],
            [],
            entitlement_kind_ids=list(EntitlementKindId),
        )

        authorization = await domain._authorize_entry(item, cache)

        assert authorization == EntryAuthorization(
            entry_id=entry.id,
            globally_visible=True,
            reservations=(),
        )

    @pytest.mark.asyncio
    async def test_reserves_each_entitled_user(self, loaded_feed: Feed) -> None:
        user_ids = [new_user_id() for _ in range(3)]
        entry = next(iter((await l_make.n_entries(loaded_feed, 1)).values()))

        for user_id in user_ids:
            await fl_domain.add_link(user_id, loaded_feed.id)

        await grant_tokens(user_ids[0], EntitlementKindId.day_tokens)
        await grant_tokens(user_ids[1], EntitlementKindId.month_tokens)
        item = EntryToProcess(entry_id=entry.id)
        cache = await entries_cache.create_entries_cache(
            [item],
            [],
            entitlement_kind_ids=list(EntitlementKindId),
        )

        authorization = await domain._authorize_entry(item, cache)

        assert not authorization.globally_visible
        assert {(reservation.user_id, reservation.kind) for reservation in authorization.reservations} == {
            (user_ids[0], Resource.day_token_usage),
            (user_ids[1], Resource.month_token_usage),
        }

    @pytest.mark.asyncio
    async def test_reserves_each_entry_from_the_first_available_pool(self, loaded_feed: Feed) -> None:
        user_id = new_user_id()
        entries = list((await l_make.n_entries(loaded_feed, 2)).values())
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens, value=1)
        await grant_tokens(user_id, EntitlementKindId.month_tokens, value=2)
        items = [EntryToProcess(entry_id=entry.id) for entry in entries]
        cache = await entries_cache.create_entries_cache(
            items,
            [],
            entitlement_kind_ids=list(EntitlementKindId),
        )

        authorizations = [await domain._authorize_entry(item, cache) for item in items]

        assert [authorization.reservations[0].kind for authorization in authorizations] == [
            Resource.day_token_usage,
            Resource.month_token_usage,
        ]

    @pytest.mark.asyncio
    async def test_deduplicates_user_linked_through_multiple_feeds(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
    ) -> None:
        user_id = new_user_id()
        entry = next(iter((await l_make.n_entries(loaded_feed, 1)).values()))
        await l_domain.catalog_entries(another_loaded_feed.id, [entry.collected_entry()])
        await fl_domain.add_link(user_id, loaded_feed.id)
        await fl_domain.add_link(user_id, another_loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.lifetime_tokens)
        item = EntryToProcess(entry_id=entry.id)
        cache = await entries_cache.create_entries_cache(
            [item],
            [],
            entitlement_kind_ids=list(EntitlementKindId),
        )

        authorization = await domain._authorize_entry(item, cache)

        assert [reservation.user_id for reservation in authorization.reservations] == [user_id]

    @pytest.mark.asyncio
    async def test_entry_without_linked_users(self, loaded_feed: Feed) -> None:
        entry = next(iter((await l_make.n_entries(loaded_feed, 1)).values()))
        item = EntryToProcess(entry_id=entry.id)
        cache = await entries_cache.create_entries_cache(
            [item],
            [],
            entitlement_kind_ids=list(EntitlementKindId),
        )

        authorization = await domain._authorize_entry(item, cache)

        assert authorization == EntryAuthorization(
            entry_id=entry.id,
            globally_visible=False,
            reservations=(),
        )


class TestEntryAuthorization:
    @pytest.mark.asyncio
    async def test_consumes_reservations_on_success(self, mocker: MockerFixture) -> None:
        item = EntryToProcess(entry_id=new_entry_id())
        cache = make_entries_cache()
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=False, reservations=())
        authorize_entry = mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")

        async with domain._entry_authorization(item, cache) as yielded_authorization:
            assert yielded_authorization == authorization

        authorize_entry.assert_awaited_once_with(item, cache)
        convert_reservations.assert_awaited_once_with(
            list[ResourceReservation](),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
        )

    @pytest.mark.asyncio
    async def test_releases_reservations_on_failure(self, mocker: MockerFixture) -> None:
        item = EntryToProcess(entry_id=new_entry_id())
        cache = make_entries_cache()
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=False, reservations=())
        authorize_entry = mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")

        with pytest.raises(RuntimeError, match="dispatch failed"):
            async with domain._entry_authorization(item, cache):
                raise RuntimeError("dispatch failed")

        authorize_entry.assert_awaited_once_with(item, cache)
        convert_reservations.assert_awaited_once_with(list[ResourceReservation](), used=0)


class TestMarkEntryTagsVisible:
    @pytest.mark.asyncio
    async def test_global_visibility(self) -> None:
        entry_id = new_entry_id()
        authorization = EntryAuthorization(entry_id=entry_id, globally_visible=True, reservations=())

        await domain._mark_entry_tags_visible(authorization, [])

        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}

    @pytest.mark.asyncio
    async def test_user_visibility(self) -> None:
        entry_id = new_entry_id()
        user_ids = {new_user_id(), new_user_id()}
        authorization = EntryAuthorization(entry_id=entry_id, globally_visible=False, reservations=())

        await domain._mark_entry_tags_visible(authorization, user_ids)

        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {}

        for user_id in user_ids:
            assert await m_domain.get_markers(user_id=user_id, entries_ids=[entry_id]) == {
                entry_id: {Marker.can_see_tags}
            }

    @pytest.mark.asyncio
    async def test_no_authorized_users(self) -> None:
        entry_id = new_entry_id()
        authorization = EntryAuthorization(entry_id=entry_id, globally_visible=False, reservations=())

        async with TableSizeNotChanged("m_markers"):
            await domain._mark_entry_tags_visible(authorization, [])


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


class TestProcessorsForItem:
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

    def test_no_processors(self) -> None:
        item = EntryToProcess(entry_id=new_entry_id())

        assert domain._processors_for_item(item, [], make_entries_cache()) == []

    def test_untargeted_item(
        self,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
    ) -> None:
        item = EntryToProcess(entry_id=new_entry_id())
        processors = [
            make.processor_dispatch_info(fake_processor_id),
            make.processor_dispatch_info(another_fake_processor_id),
        ]

        assert domain._processors_for_item(item, processors, make_entries_cache()) == processors

    def test_targeted_item(
        self,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
    ) -> None:
        item = EntryToProcess(entry_id=new_entry_id(), processor_id=fake_processor_id)
        processor = make.processor_dispatch_info(fake_processor_id)
        another_processor = make.processor_dispatch_info(another_fake_processor_id)

        assert domain._processors_for_item(
            item,
            [processor, another_processor],
            make_entries_cache(),
        ) == [processor]

    @pytest.mark.parametrize(
        "status",
        [
            EntryProcessingStatus.skipped_by_processor,
            EntryProcessingStatus.skipped_by_dispatcher,
            EntryProcessingStatus.retry_requested,
        ],
    )
    def test_allows_processor_with_redispatch_status(
        self,
        status: EntryProcessingStatus,
        fake_processor_id: ProcessorId,
    ) -> None:
        entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)
        processor = make.processor_dispatch_info(fake_processor_id)
        cache = make_entries_cache(
            processing_statuses={processor.processor_id: {entry_id: status}},
        )

        assert domain._processors_for_item(item, [processor], cache) == [processor]

    @pytest.mark.parametrize(
        "status",
        [
            EntryProcessingStatus.dispatched,
            EntryProcessingStatus.processed,
            EntryProcessingStatus.failed,
        ],
    )
    def test_skips_processor_blocked_by_status(
        self,
        status: EntryProcessingStatus,
        fake_processor_id: ProcessorId,
    ) -> None:
        entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)
        processor = make.processor_dispatch_info(fake_processor_id)
        cache = make_entries_cache(
            processing_statuses={processor.processor_id: {entry_id: status}},
        )

        assert domain._processors_for_item(item, [processor], cache) == []


class TestDispatchEntryToProcessors:
    @pytest_asyncio.fixture(autouse=True)  # type: ignore
    async def prepare_processing_statuses(self) -> None:
        await operations.tech_truncate_entry_processing_statuses()

    @pytest.mark.asyncio
    async def test_dispatches_item_to_processor_subqueues(
        self,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
        mocker: MockerFixture,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        push = mocker.spy(domain.q_domain, "push")

        entry_id = new_entry_id()
        processors = [
            make.processor_dispatch_info(
                fake_processor_id,
                subqueue_id=another_fake_processor_id,
                routes=[
                    make.processor_dispatch_route(
                        id="first-route",
                        allowed_for_collections=True,
                        allowed_for_users=True,
                    )
                ],
            ),
            make.processor_dispatch_info(
                another_fake_processor_id,
                subqueue_id=fake_processor_id,
                routes=[
                    make.processor_dispatch_route(
                        id="second-route",
                        allowed_for_collections=True,
                        allowed_for_users=True,
                    )
                ],
            ),
        ]

        await domain._dispatch_entry_to_processors(
            processors=processors,
            item=EntryToProcess(entry_id=entry_id),
            cache=make_entries_cache(),
        )

        for processor in processors:
            records = await q_domain.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=processor.subqueue_id,
            )

            assert record_entry_ids(records) == {entry_id}
            assert {record.item.route_id for record in records} == {processor.routes[0].id}

        processor_ids = [processor.processor_id for processor in processors]
        processing_statuses = await domain.get_entries_processing_statuses(processor_ids, [entry_id])

        assert processing_statuses == {
            processor_id: {entry_id: EntryProcessingStatus.dispatched} for processor_id in processor_ids
        }
        push.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_marks_entries_without_allowed_route_as_skipped_by_dispatcher(
        self, fake_processor_id: ProcessorId
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)

        entry_id = new_entry_id()
        processor = make.processor_dispatch_info(
            fake_processor_id, allowed_for_collections=True, allowed_for_users=False
        )

        await domain._dispatch_entry_to_processors(
            processors=[processor],
            item=EntryToProcess(entry_id=entry_id),
            cache=make_entries_cache(),
        )

        assert (
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_tag, EntryToTag, secondary_id=processor.subqueue_id
            )
            == []
        )
        await assert_processing_status(processor.processor_id, entry_id, EntryProcessingStatus.skipped_by_dispatcher)


class TestProcessEntry:
    @pytest.mark.asyncio
    async def test_authorized_entry(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        item: EntryToProcess = record.item
        cache = make_entries_cache()
        processor = make.processor_dispatch_info(fake_processor_id)
        processors: list[ProcessorDispatchInfo] = [processor]
        entry_ids: list[EntryId] = [item.entry_id]
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=True, reservations=())
        settled_user_ids: set[UserId] = set()
        mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")
        dispatch_to_processors = mocker.patch.object(domain, "_dispatch_entry_to_processors")
        mark_tags_visible = mocker.patch.object(domain, "_mark_entry_tags_visible")
        set_dispatching_statuses = mocker.patch.object(domain.operations, "set_entry_dispatching_statuses")

        await domain._process_entry(record, processors, cache)

        dispatch_to_processors.assert_awaited_once_with(
            processors,
            item,
            cache,
        )
        mark_tags_visible.assert_awaited_once_with(authorization, settled_user_ids)
        convert_reservations.assert_awaited_once_with(
            list[ResourceReservation](),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
        )
        set_dispatching_statuses.assert_awaited_once_with(
            entry_ids,
            resources_consumed=False,
        )

    @pytest.mark.asyncio
    async def test_unauthorized_entry(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        item: EntryToProcess = record.item
        cache = make_entries_cache()
        processor = make.processor_dispatch_info(fake_processor_id)
        processors: list[ProcessorDispatchInfo] = [processor]
        status_updates = make_status_updates(
            processor.processor_id,
            [item.entry_id],
            EntryProcessingStatus.skipped_by_dispatcher,
        )
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=False, reservations=())
        mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")
        dispatch_to_processors = mocker.patch.object(domain, "_dispatch_entry_to_processors")
        set_processing_statuses = mocker.patch.object(domain, "set_entry_processing_statuses")
        mark_tags_visible = mocker.patch.object(domain, "_mark_entry_tags_visible")
        set_dispatching_statuses = mocker.patch.object(domain.operations, "set_entry_dispatching_statuses")

        await domain._process_entry(record, processors, cache)

        dispatch_to_processors.assert_not_awaited()
        set_processing_statuses.assert_awaited_once_with(status_updates)
        mark_tags_visible.assert_not_awaited()
        convert_reservations.assert_awaited_once_with(
            list[ResourceReservation](),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
        )
        set_dispatching_statuses.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dispatch_failure(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        item: EntryToProcess = record.item
        cache = make_entries_cache()
        processor = make.processor_dispatch_info(fake_processor_id)
        processors: list[ProcessorDispatchInfo] = [processor]
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=True, reservations=())
        mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")
        mocker.patch.object(
            domain,
            "_dispatch_entry_to_processors",
            side_effect=RuntimeError("dispatch failed"),
        )
        mark_tags_visible = mocker.patch.object(domain, "_mark_entry_tags_visible")
        set_dispatching_statuses = mocker.patch.object(domain.operations, "set_entry_dispatching_statuses")

        with pytest.raises(RuntimeError, match="dispatch failed"):
            await domain._process_entry(record, processors, cache)

        mark_tags_visible.assert_not_awaited()
        convert_reservations.assert_awaited_once_with(list[ResourceReservation](), used=0)
        set_dispatching_statuses.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dispatching_status_failure(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        item: EntryToProcess = record.item
        cache = make_entries_cache()
        processor = make.processor_dispatch_info(fake_processor_id)
        processors: list[ProcessorDispatchInfo] = [processor]
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=True, reservations=())
        mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")
        dispatch_to_processors = mocker.patch.object(domain, "_dispatch_entry_to_processors")
        mark_tags_visible = mocker.patch.object(domain, "_mark_entry_tags_visible")
        mocker.patch.object(
            domain.operations,
            "set_entry_dispatching_statuses",
            side_effect=RuntimeError("status write failed"),
        )

        with pytest.raises(RuntimeError, match="status write failed"):
            await domain._process_entry(record, processors, cache)

        dispatch_to_processors.assert_awaited_once_with(processors, item, cache)
        mark_tags_visible.assert_awaited_once_with(authorization, set[UserId]())
        convert_reservations.assert_awaited_once_with(list[ResourceReservation](), used=0)


class TestProcessRetryEntry:
    @pytest.mark.asyncio
    async def test_success(
        self,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
        mocker: MockerFixture,
    ) -> None:
        record = make_entry_record(new_entry_id())
        item: EntryToProcess = record.item
        cache = make_entries_cache()
        processors = [
            make.processor_dispatch_info(fake_processor_id),
            make.processor_dispatch_info(another_fake_processor_id),
        ]
        authorize_entry = mocker.patch.object(domain, "_authorize_entry")
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")
        dispatch_to_processors = mocker.patch.object(domain, "_dispatch_entry_to_processors")
        mark_tags_visible = mocker.patch.object(domain, "_mark_entry_tags_visible")
        set_dispatching_statuses = mocker.patch.object(domain.operations, "set_entry_dispatching_statuses")

        await domain._process_retry_entry(record, processors, cache)

        dispatch_to_processors.assert_awaited_once_with(processors, item, cache)
        authorize_entry.assert_not_awaited()
        convert_reservations.assert_not_awaited()
        mark_tags_visible.assert_not_awaited()
        set_dispatching_statuses.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dispatch_failure(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        cache = make_entries_cache()
        processor = make.processor_dispatch_info(fake_processor_id)
        mocker.patch.object(
            domain,
            "_dispatch_entry_to_processors",
            side_effect=RuntimeError("dispatch failed"),
        )

        with pytest.raises(RuntimeError, match="dispatch failed"):
            await domain._process_retry_entry(record, [processor], cache)


class TestValidateDispatchEntries:
    def test_success(
        self,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
    ) -> None:
        domain._validate_dispatch_entries(
            [
                make.processor_dispatch_info(fake_processor_id),
                make.processor_dispatch_info(another_fake_processor_id),
            ],
            concurrency=1,
        )

    def test_duplicated_processors(self, fake_processor_id: ProcessorId) -> None:
        processor = make.processor_dispatch_info(fake_processor_id)

        with pytest.raises(errors.DuplicatedProcessors):
            domain._validate_dispatch_entries([processor, processor], concurrency=1)

    def test_non_positive_concurrency(self, fake_processor_id: ProcessorId) -> None:
        with pytest.raises(errors.InvalidConcurrency):
            domain._validate_dispatch_entries(
                [make.processor_dispatch_info(fake_processor_id)],
                concurrency=0,
            )


class TestDispatchRecord:
    @pytest.mark.asyncio
    async def test_first_time_entry(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        processors = [make.processor_dispatch_info(fake_processor_id)]
        cache = make_entries_cache()
        process_entry = mocker.patch.object(domain, "_process_entry")
        process_retry_entry = mocker.patch.object(domain, "_process_retry_entry")

        dispatched = await domain._dispatch_record(
            record,
            processors=processors,
            cache=cache,
            dispatching_statuses={},
        )

        assert dispatched
        process_entry.assert_awaited_once_with(record, processors, cache)
        process_retry_entry.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retry_entry(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        processors = [make.processor_dispatch_info(fake_processor_id)]
        cache = make_entries_cache()
        process_entry = mocker.patch.object(domain, "_process_entry")
        process_retry_entry = mocker.patch.object(domain, "_process_retry_entry")

        dispatched = await domain._dispatch_record(
            record,
            processors=processors,
            cache=cache,
            dispatching_statuses={record.item.entry_id: False},
        )

        assert dispatched
        process_entry.assert_not_awaited()
        process_retry_entry.assert_awaited_once_with(record, processors, cache)

    @pytest.mark.asyncio
    async def test_failure(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        cache = make_entries_cache()
        mocker.patch.object(domain, "_process_entry", side_effect=RuntimeError("dispatch failed"))
        log_exception = mocker.patch.object(domain.logger, "exception")

        dispatched = await domain._dispatch_record(
            record,
            processors=[make.processor_dispatch_info(fake_processor_id)],
            cache=cache,
            dispatching_statuses={},
        )

        assert not dispatched
        log_exception.assert_called_once_with("entry_dispatch_failed", entry_id=record.item.entry_id)


class TestDispatchEntries:
    @pytest_asyncio.fixture(autouse=True)  # type: ignore
    async def prepare_processing_statuses(self) -> None:
        await operations.tech_truncate_entry_processing_statuses()

    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: ProcessorId) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 0

    @pytest.mark.asyncio
    async def test_concurrency(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        records = [make_entry_record(new_entry_id()) for _ in range(5)]
        cache = make_entries_cache()
        mocker.patch.object(domain.q_domain, "pull", return_value=records)
        mocker.patch.object(domain.entries_cache, "create_entries_cache", return_value=cache)

        active_tasks = 0
        max_active_tasks = 0

        async def process_entry(
            _record: QueueRecord[EntryToProcess],
            _processors: Sequence[ProcessorDispatchInfo],
            _cache: entries_cache.EntriesCache,
        ) -> None:
            nonlocal active_tasks, max_active_tasks

            active_tasks += 1
            max_active_tasks = max(max_active_tasks, active_tasks)
            await asyncio.sleep(0)
            active_tasks -= 1

        mocker.patch.object(domain, "_process_entry", new=process_entry)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=len(records),
            concurrency=2,
        )

        assert dispatched == len(records)
        assert max_active_tasks == 2

    @pytest.mark.asyncio
    async def test_processes_first_time_and_retry_entries(
        self,
        fake_processor_id: ProcessorId,
        mocker: MockerFixture,
    ) -> None:
        first_time_record = make_entry_record(new_entry_id())
        consumed_retry_record = make_entry_record(new_entry_id())
        free_retry_record = make_entry_record(new_entry_id())
        records = [first_time_record, consumed_retry_record, free_retry_record]
        cache = make_entries_cache()
        dispatching_statuses: dict[EntryId, bool] = {
            consumed_retry_record.item.entry_id: True,
            free_retry_record.item.entry_id: False,
        }
        mocker.patch.object(domain.q_domain, "pull", return_value=records)
        mocker.patch.object(domain.entries_cache, "create_entries_cache", return_value=cache)
        get_dispatching_statuses = mocker.patch.object(
            domain.operations,
            "get_entries_dispatching_statuses",
            return_value=dispatching_statuses,
        )
        process_entry = mocker.patch.object(domain, "_process_entry", return_value=None)
        process_retry_entry = mocker.patch.object(domain, "_process_retry_entry", return_value=None)
        acknowledge = mocker.patch.object(domain.q_domain, "acknowledge")
        processor = make.processor_dispatch_info(fake_processor_id)
        processors: list[ProcessorDispatchInfo] = [processor]
        entry_ids: list[EntryId] = [record.item.entry_id for record in records]

        dispatched = await domain.dispatch_entries(
            processors=processors,
            batch_size=len(records),
            concurrency=len(records),
        )

        assert dispatched == len(records)
        get_dispatching_statuses.assert_awaited_once_with(entry_ids)
        process_entry.assert_awaited_once_with(first_time_record, processors, cache)
        assert cast(int, process_retry_entry.await_count) == 2
        process_retry_entry.assert_any_await(consumed_retry_record, processors, cache)
        process_retry_entry.assert_any_await(free_retry_record, processors, cache)
        record_ids: list[QueueRecordId] = []

        for record in records:
            assert record.id is not None
            record_ids.append(record.id)

        acknowledge.assert_awaited_once_with(record_ids)

    @pytest.mark.asyncio
    async def test_non_positive_concurrency(self, fake_processor_id: ProcessorId) -> None:
        with pytest.raises(errors.InvalidConcurrency):
            await domain.dispatch_entries(
                processors=[make.processor_dispatch_info(fake_processor_id)],
                batch_size=10,
                concurrency=0,
            )

    @pytest.mark.asyncio
    async def test_dispatch_to_each_processor_subqueue(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)

        user_id = new_user_id()
        entry_ids = list(await l_make.n_entries(loaded_feed, 2))
        processor_ids = [fake_processor_id, another_fake_processor_id]
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)

        await enqueue_entries_to_process(entry_ids)

        processors = [make.processor_dispatch_info(processor_id) for processor_id in processor_ids]
        dispatched = await domain.dispatch_entries(processors=processors, batch_size=10, concurrency=10)

        assert dispatched == len(entry_ids)
        assert await q_domain.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess) == []

        for processor_id in processor_ids:
            records = await q_domain.tech_get_queue_records(
                QueueKind.entries_to_tag, EntryToTag, secondary_id=QueueSecondaryId(processor_id)
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
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)

        user_entry_ids = await l_make.n_entries(loaded_feed, 2)
        collection_entry_ids = await l_make.n_entries(another_loaded_feed, 2)
        await collections.add_test_feed_to_collections(collection_id_for_test_feeds, another_loaded_feed.id)
        user_id = new_user_id()
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)

        entry_ids = [*user_entry_ids, *collection_entry_ids]

        await enqueue_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == len(entry_ids)
        assert await m_domain.get_markers(user_id=None, entries_ids=entry_ids) == {
            entry_id: {Marker.can_see_tags} for entry_id in entry_ids
        }

    @pytest.mark.asyncio
    async def test_skips_entry_without_authorized_users(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))

        await enqueue_entries_to_process([entry_id])

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 1
        assert (
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_process,
                EntryToProcess,
            )
            == []
        )
        assert (
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=QueueSecondaryId(fake_processor_id),
            )
            == []
        )
        await assert_processing_status(
            fake_processor_id,
            entry_id,
            EntryProcessingStatus.skipped_by_dispatcher,
        )
        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {}
        assert await operations.get_entries_dispatching_statuses([entry_id]) == {}

    @pytest.mark.asyncio
    async def test_consumes_entitlement_and_grants_user_visibility(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        await enqueue_entries_to_process([entry_id])

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 1
        assert record_entry_ids(
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=QueueSecondaryId(fake_processor_id),
            )
        ) == {entry_id}
        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {}
        assert await m_domain.get_markers(user_id=user_id, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}
        await assert_resource_counters(
            user_id=user_id,
            kind=Resource.day_token_usage,
            interval_started_at=day_interval_start(),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
            reserved=0,
        )
        assert await operations.get_entries_dispatching_statuses([entry_id]) == {entry_id: True}

    @pytest.mark.asyncio
    async def test_api_key_user_grants_global_visibility_without_consuming_entitlements(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        api_key_user_id = new_user_id()
        entitled_user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(api_key_user_id, loaded_feed.id)
        await fl_domain.add_link(entitled_user_id, loaded_feed.id)
        await save_user_api_key(api_key_user_id)
        await grant_tokens(entitled_user_id, EntitlementKindId.day_tokens)
        await enqueue_entries_to_process([entry_id])

        await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}
        await assert_no_resource_record(
            user_id=entitled_user_id,
            kind=Resource.day_token_usage,
            interval_started_at=day_interval_start(),
        )
        assert await operations.get_entries_dispatching_statuses([entry_id]) == {entry_id: False}

    @pytest.mark.asyncio
    async def test_retry_does_not_consume_resources(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens, value=2)
        processor = make.processor_dispatch_info(fake_processor_id)
        await enqueue_entries_to_process([entry_id])

        first_dispatch_count = await domain.dispatch_entries(
            processors=[processor],
            batch_size=10,
            concurrency=10,
        )

        assert first_dispatch_count == 1
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        await domain.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [entry_id],
                EntryProcessingStatus.failed,
            )
        )
        await domain.move_failed_entries_to_processor_queue(fake_processor_id, limit=10)

        retry_dispatch_count = await domain.dispatch_entries(
            processors=[processor],
            batch_size=10,
            concurrency=10,
        )

        assert retry_dispatch_count == 1
        assert record_entry_ids(
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=QueueSecondaryId(fake_processor_id),
            )
        ) == {entry_id}
        await assert_resource_counters(
            user_id=user_id,
            kind=Resource.day_token_usage,
            interval_started_at=day_interval_start(),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
            reserved=0,
        )
        assert await operations.get_entries_dispatching_statuses([entry_id]) == {entry_id: True}

    @pytest.mark.asyncio
    async def test_consumes_once_when_dispatching_to_multiple_processors(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        await enqueue_entries_to_process([entry_id])
        processors = [
            make.processor_dispatch_info(fake_processor_id),
            make.processor_dispatch_info(another_fake_processor_id),
        ]

        await domain.dispatch_entries(processors=processors, batch_size=10, concurrency=10)

        for processor in processors:
            assert record_entry_ids(
                await q_domain.tech_get_queue_records(
                    QueueKind.entries_to_tag,
                    EntryToTag,
                    secondary_id=processor.subqueue_id,
                )
            ) == {entry_id}

        await assert_resource_counters(
            user_id=user_id,
            kind=Resource.day_token_usage,
            interval_started_at=day_interval_start(),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
            reserved=0,
        )

    @pytest.mark.asyncio
    async def test_processor_filtering_does_not_change_consumption(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        await domain.set_entry_processing_statuses(
            make_status_updates(
                fake_processor_id,
                [entry_id],
                EntryProcessingStatus.processed,
            )
        )
        await enqueue_entries_to_process([entry_id])

        await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert (
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=QueueSecondaryId(fake_processor_id),
            )
            == []
        )
        await assert_resource_counters(
            user_id=user_id,
            kind=Resource.day_token_usage,
            interval_started_at=day_interval_start(),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
            reserved=0,
        )
        assert await m_domain.get_markers(user_id=user_id, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}

    @pytest.mark.asyncio
    async def test_releases_entitlement_when_processor_fanout_fails(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
        mocker: MockerFixture,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        await enqueue_entries_to_process([entry_id])
        mocker.patch.object(
            domain,
            "_dispatch_entry_to_processors",
            side_effect=RuntimeError("processor fanout failed"),
        )
        log_exception = mocker.patch.object(domain.logger, "exception")

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 0
        log_exception.assert_called_once_with("entry_dispatch_failed", entry_id=entry_id)
        await assert_resource_counters(
            user_id=user_id,
            kind=Resource.day_token_usage,
            interval_started_at=day_interval_start(),
            used=0,
            reserved=0,
        )
        assert await m_domain.get_markers(user_id=user_id, entries_ids=[entry_id]) == {}
        assert (
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_process,
                EntryToProcess,
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_entry_failure_does_not_interrupt_siblings(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
        mocker: MockerFixture,
    ) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        failed_entry_id, dispatched_entry_id = list(await l_make.n_entries(loaded_feed, 2))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)
        await enqueue_entries_to_process([failed_entry_id, dispatched_entry_id])
        original_dispatch = domain._dispatch_entry_to_processors

        async def dispatch_to_processors(
            processors: Sequence[ProcessorDispatchInfo],
            item: EntryToProcess,
            cache: entries_cache.EntriesCache,
        ) -> None:
            if item.entry_id == failed_entry_id:
                raise RuntimeError("processor fanout failed")

            await original_dispatch(
                processors,
                item,
                cache,
            )

        mocker.patch.object(domain, "_dispatch_entry_to_processors", new=dispatch_to_processors)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 1
        assert (
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_process,
                EntryToProcess,
            )
            == []
        )
        assert record_entry_ids(
            await q_domain.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=QueueSecondaryId(fake_processor_id),
            )
        ) == {dispatched_entry_id}
        assert await m_domain.get_markers(
            user_id=None,
            entries_ids=[failed_entry_id, dispatched_entry_id],
        ) == {dispatched_entry_id: {Marker.can_see_tags}}

    @pytest.mark.asyncio
    async def test_no_processors(self) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id()]

        await enqueue_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[], batch_size=10, concurrency=10)

        assert dispatched == 0

        records = await q_domain.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_duplicated_processors(self, fake_processor_id: ProcessorId) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id()]
        processor = make.processor_dispatch_info(fake_processor_id)

        await enqueue_entries_to_process(entry_ids)

        with pytest.raises(errors.DuplicatedProcessors):
            await domain.dispatch_entries(
                processors=[processor, processor],
                batch_size=10,
                concurrency=10,
            )

        records = await q_domain.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_batch_size(self, loaded_feed: Feed, fake_processor_id: ProcessorId) -> None:
        await q_domain.tech_clear_queue(QueueKind.entries_to_process)
        await q_domain.tech_clear_queue(QueueKind.entries_to_tag)

        user_id = new_user_id()
        entry_ids = list(await l_make.n_entries(loaded_feed, 3))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)

        await enqueue_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=2,
            concurrency=10,
        )

        assert dispatched == 2

        dispatched_records = await q_domain.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=QueueSecondaryId(fake_processor_id)
        )
        remaining_records = await q_domain.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert len(dispatched_records) == 2
        assert len(remaining_records) == 1
        assert record_entry_ids(dispatched_records) | record_entry_ids(remaining_records) == set(entry_ids)
