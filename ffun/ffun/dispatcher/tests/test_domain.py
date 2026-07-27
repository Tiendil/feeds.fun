import asyncio
import datetime
import uuid
from collections.abc import Mapping, Sequence

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
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind, QueueRecord, QueueRecordId
from ffun.resources import domain as r_domain
from ffun.resources.entities import Resource as ResourceRecord
from ffun.resources.entities import ResourceReservation, ResourceReservationOption, ResourceReservationSpecification
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


async def get_resource(user_id: UserId, kind: Resource, interval_started_at: datetime.datetime) -> ResourceRecord:
    return await r_domain.load_resource(
        user_id=user_id,
        kind=kind,
        interval_started_at=interval_started_at,
    )


def make_entries_cache(
    *,
    entries_in_collections: Mapping[EntryId, bool] | None = None,
    processing_statuses: Mapping[ProcessorId, Mapping[EntryId, EntryProcessingStatus]] | None = None,
) -> entries_cache.EntriesCache:
    return entries_cache.EntriesCache(
        entries_in_collections=entries_in_collections or {},
        feed_ids_by_entry={},
        user_ids_by_feed={},
        users_with_api_keys=set(),
        processing_statuses=processing_statuses or {},
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


class TestEntriesInCollections:
    def test_reexports_entries_cache(self) -> None:
        assert domain.entries_in_collections is entries_cache.entries_in_collections


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
        cache = await entries_cache.create_entries_cache([item], [])

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
        cache = await entries_cache.create_entries_cache([item], [])

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
        cache = await entries_cache.create_entries_cache([item], [])

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
        cache = await entries_cache.create_entries_cache(items, [])

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
        cache = await entries_cache.create_entries_cache([item], [])

        authorization = await domain._authorize_entry(item, cache)

        assert [reservation.user_id for reservation in authorization.reservations] == [user_id]

    @pytest.mark.asyncio
    async def test_entry_without_linked_users(self, loaded_feed: Feed) -> None:
        entry = next(iter((await l_make.n_entries(loaded_feed, 1)).values()))
        item = EntryToProcess(entry_id=entry.id)
        cache = await entries_cache.create_entries_cache([item], [])

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
        cache = make_entries_cache(
            entries_in_collections={
                first_entry_id: False,
                second_entry_id: True,
            }
        )

        items_to_tag, skipped_entry_ids = domain._processor_items_to_tag(processor, items, cache)

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

    def test_no_items(self, fake_processor_id: ProcessorId) -> None:
        processor = make.processor_dispatch_info(fake_processor_id)

        assert domain._processor_items_allowed_by_status(processor, [], make_entries_cache()) == []

    def test_allows_items_without_status(self, fake_processor_id: ProcessorId) -> None:
        entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)
        processor = make.processor_dispatch_info(fake_processor_id)

        assert domain._processor_items_allowed_by_status(processor, [item], make_entries_cache()) == [item]

    @pytest.mark.parametrize(
        "status",
        [
            EntryProcessingStatus.skipped_by_processor,
            EntryProcessingStatus.skipped_by_dispatcher,
            EntryProcessingStatus.retry_requested,
        ],
    )
    def test_allows_items_with_status_that_requires_redispatch(
        self,
        status: EntryProcessingStatus,
        fake_processor_id: ProcessorId,
    ) -> None:
        entry_id = new_entry_id()
        blocked_entry_id = new_entry_id()
        item = EntryToProcess(entry_id=entry_id)
        blocked_item = EntryToProcess(entry_id=blocked_entry_id)
        processor = make.processor_dispatch_info(fake_processor_id)
        cache = make_entries_cache(
            processing_statuses={
                processor.processor_id: {
                    entry_id: status,
                    blocked_entry_id: EntryProcessingStatus.dispatched,
                }
            }
        )

        assert domain._processor_items_allowed_by_status(
            processor,
            [item, blocked_item],
            cache,
        ) == [item]

    @pytest.mark.parametrize(
        "status",
        [
            EntryProcessingStatus.dispatched,
            EntryProcessingStatus.processed,
            EntryProcessingStatus.failed,
        ],
    )
    def test_skips_items_with_final_or_in_progress_status(
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

        assert domain._processor_items_allowed_by_status(processor, [item], cache) == []


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
            cache=make_entries_cache(),
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
            cache=make_entries_cache(),
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
            cache=make_entries_cache(),
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
            cache=make_entries_cache(),
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
        cache = make_entries_cache(
            processing_statuses={
                processor.processor_id: {
                    failed_entry_id: EntryProcessingStatus.failed,
                }
            }
        )

        await domain.set_entry_processing_statuses(
            processor.processor_id, [failed_entry_id], EntryProcessingStatus.failed
        )

        await domain._dispatch_entries_to_processor(
            processor=processor,
            items=[
                EntryToProcess(entry_id=allowed_entry_id),
                EntryToProcess(entry_id=failed_entry_id),
            ],
            cache=cache,
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


class TestProcessEntry:
    @pytest.mark.asyncio
    async def test_authorized_entry(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        item: EntryToProcess = record.item
        record_id: QueueRecordId | None = record.id
        assert record_id is not None
        items: list[EntryToProcess] = [item]
        record_ids: list[QueueRecordId] = [record_id]
        cache = make_entries_cache()
        processor = make.processor_dispatch_info(fake_processor_id)
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=True, reservations=())
        settled_user_ids: set[UserId] = set()
        mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")
        dispatch_to_processor = mocker.patch.object(domain, "_dispatch_entries_to_processor")
        mark_tags_visible = mocker.patch.object(domain, "_mark_entry_tags_visible")
        acknowledge = mocker.patch.object(domain, "acknowledge")

        processed = await domain._process_entry(record, [processor], cache)

        assert processed
        dispatch_to_processor.assert_awaited_once_with(
            processor,
            items,
            cache,
            dispatch_allowed=True,
        )
        mark_tags_visible.assert_awaited_once_with(authorization, settled_user_ids)
        convert_reservations.assert_awaited_once_with(
            list[ResourceReservation](),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
        )
        acknowledge.assert_awaited_once_with(record_ids)

    @pytest.mark.asyncio
    async def test_unauthorized_entry(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        item: EntryToProcess = record.item
        record_id: QueueRecordId | None = record.id
        assert record_id is not None
        items: list[EntryToProcess] = [item]
        record_ids: list[QueueRecordId] = [record_id]
        cache = make_entries_cache()
        processor = make.processor_dispatch_info(fake_processor_id)
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=False, reservations=())
        mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")
        dispatch_to_processor = mocker.patch.object(domain, "_dispatch_entries_to_processor")
        mark_tags_visible = mocker.patch.object(domain, "_mark_entry_tags_visible")
        acknowledge = mocker.patch.object(domain, "acknowledge")

        processed = await domain._process_entry(record, [processor], cache)

        assert processed
        dispatch_to_processor.assert_awaited_once_with(
            processor,
            items,
            cache,
            dispatch_allowed=False,
        )
        mark_tags_visible.assert_not_awaited()
        convert_reservations.assert_awaited_once_with(
            list[ResourceReservation](),
            used=domain.SAAS_TOKENS_PER_USER_ENTRY,
        )
        acknowledge.assert_awaited_once_with(record_ids)

    @pytest.mark.asyncio
    async def test_dispatch_failure(self, fake_processor_id: ProcessorId, mocker: MockerFixture) -> None:
        record = make_entry_record(new_entry_id())
        item: EntryToProcess = record.item
        cache = make_entries_cache()
        processor = make.processor_dispatch_info(fake_processor_id)
        authorization = EntryAuthorization(entry_id=item.entry_id, globally_visible=True, reservations=())
        mocker.patch.object(domain, "_authorize_entry", return_value=authorization)
        convert_reservations = mocker.patch.object(r_domain, "convert_reserved_to_used")
        mocker.patch.object(
            domain,
            "_dispatch_entries_to_processor",
            side_effect=RuntimeError("dispatch failed"),
        )
        mark_tags_visible = mocker.patch.object(domain, "_mark_entry_tags_visible")
        acknowledge = mocker.patch.object(domain, "acknowledge")
        log_exception = mocker.patch.object(domain.logger, "exception")

        processed = await domain._process_entry(record, [processor], cache)

        assert not processed
        mark_tags_visible.assert_not_awaited()
        convert_reservations.assert_awaited_once_with(list[ResourceReservation](), used=0)
        acknowledge.assert_not_awaited()
        log_exception.assert_called_once_with("entry_dispatch_failed", entry_id=item.entry_id)


class TestDispatchEntries:
    @pytest_asyncio.fixture(autouse=True)  # type: ignore
    async def prepare_processing_statuses(self) -> None:
        await operations.tech_truncate_entry_processing_statuses()

    @pytest.mark.asyncio
    async def test_no_entries(self, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

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
        ) -> bool:
            nonlocal active_tasks, max_active_tasks

            active_tasks += 1
            max_active_tasks = max(max_active_tasks, active_tasks)
            await asyncio.sleep(0)
            active_tasks -= 1

            return True

        mocker.patch.object(domain, "_process_entry", new=process_entry)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=len(records),
            concurrency=2,
        )

        assert dispatched == len(records)
        assert max_active_tasks == 2

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
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        user_id = new_user_id()
        entry_ids = list(await l_make.n_entries(loaded_feed, 2))
        processor_ids = [fake_processor_id, another_fake_processor_id]
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)

        await domain.push_entries_to_process(entry_ids)

        processors = [make.processor_dispatch_info(processor_id) for processor_id in processor_ids]
        dispatched = await domain.dispatch_entries(processors=processors, batch_size=10, concurrency=10)

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
        user_id = new_user_id()
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)

        entry_ids = [*user_entry_ids, *collection_entry_ids]

        await domain.push_entries_to_process(entry_ids)

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
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))

        await domain.push_entries_to_process([entry_id])

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 1
        assert (
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_process,
                EntryToProcess,
            )
            == []
        )
        assert (
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=fake_processor_id,
            )
            == []
        )
        await assert_processing_status(
            fake_processor_id,
            entry_id,
            EntryProcessingStatus.skipped_by_dispatcher,
        )
        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {}

    @pytest.mark.asyncio
    async def test_consumes_entitlement_and_grants_user_visibility(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        await domain.push_entries_to_process([entry_id])

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 1
        assert record_entry_ids(
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=fake_processor_id,
            )
        ) == {entry_id}
        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {}
        assert await m_domain.get_markers(user_id=user_id, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}
        resource = await get_resource(user_id, Resource.day_token_usage, day_interval_start())
        assert resource.used == domain.SAAS_TOKENS_PER_USER_ENTRY
        assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_api_key_user_grants_global_visibility_without_consuming_entitlements(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)
        api_key_user_id = new_user_id()
        entitled_user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(api_key_user_id, loaded_feed.id)
        await fl_domain.add_link(entitled_user_id, loaded_feed.id)
        await save_user_api_key(api_key_user_id)
        await grant_tokens(entitled_user_id, EntitlementKindId.day_tokens)
        await domain.push_entries_to_process([entry_id])

        await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert await m_domain.get_markers(user_id=None, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}
        resource = await get_resource(
            entitled_user_id,
            Resource.day_token_usage,
            day_interval_start(),
        )
        assert resource.used == 0
        assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_consumes_once_when_dispatching_to_multiple_processors(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
        another_fake_processor_id: ProcessorId,
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        await domain.push_entries_to_process([entry_id])
        processors = [
            make.processor_dispatch_info(fake_processor_id),
            make.processor_dispatch_info(another_fake_processor_id),
        ]

        await domain.dispatch_entries(processors=processors, batch_size=10, concurrency=10)

        for processor in processors:
            assert record_entry_ids(
                await q_operations.tech_get_queue_records(
                    QueueKind.entries_to_tag,
                    EntryToTag,
                    secondary_id=processor.subqueue_id,
                )
            ) == {entry_id}

        resource = await get_resource(user_id, Resource.day_token_usage, day_interval_start())
        assert resource.used == domain.SAAS_TOKENS_PER_USER_ENTRY
        assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_processor_filtering_does_not_change_consumption(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        await domain.set_entry_processing_statuses(
            fake_processor_id,
            [entry_id],
            EntryProcessingStatus.processed,
        )
        await domain.push_entries_to_process([entry_id])

        await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert (
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=fake_processor_id,
            )
            == []
        )
        resource = await get_resource(user_id, Resource.day_token_usage, day_interval_start())
        assert resource.used == domain.SAAS_TOKENS_PER_USER_ENTRY
        assert resource.reserved == 0
        assert await m_domain.get_markers(user_id=user_id, entries_ids=[entry_id]) == {entry_id: {Marker.can_see_tags}}

    @pytest.mark.asyncio
    async def test_releases_entitlement_when_processor_fanout_fails(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
        mocker: MockerFixture,
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        entry_id = next(iter(await l_make.n_entries(loaded_feed, 1)))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await grant_tokens(user_id, EntitlementKindId.day_tokens)
        await domain.push_entries_to_process([entry_id])
        mocker.patch.object(
            domain,
            "_dispatch_entries_to_processor",
            side_effect=RuntimeError("processor fanout failed"),
        )

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 0
        resource = await get_resource(user_id, Resource.day_token_usage, day_interval_start())
        assert resource.used == 0
        assert resource.reserved == 0
        assert await m_domain.get_markers(user_id=user_id, entries_ids=[entry_id]) == {}
        assert record_entry_ids(
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_process,
                EntryToProcess,
            )
        ) == {entry_id}

    @pytest.mark.asyncio
    async def test_entry_failure_does_not_interrupt_siblings(
        self,
        loaded_feed: Feed,
        fake_processor_id: ProcessorId,
        mocker: MockerFixture,
    ) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)
        user_id = new_user_id()
        failed_entry_id, dispatched_entry_id = list(await l_make.n_entries(loaded_feed, 2))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)
        await domain.push_entries_to_process([failed_entry_id, dispatched_entry_id])
        original_dispatch = domain._dispatch_entries_to_processor

        async def dispatch_to_processor(
            processor: ProcessorDispatchInfo,
            items: Sequence[EntryToProcess],
            cache: entries_cache.EntriesCache,
            *,
            dispatch_allowed: bool = True,
        ) -> None:
            if items[0].entry_id == failed_entry_id:
                raise RuntimeError("processor fanout failed")

            await original_dispatch(
                processor,
                items,
                cache,
                dispatch_allowed=dispatch_allowed,
            )

        mocker.patch.object(domain, "_dispatch_entries_to_processor", new=dispatch_to_processor)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=10,
            concurrency=10,
        )

        assert dispatched == 1
        assert record_entry_ids(
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_process,
                EntryToProcess,
            )
        ) == {failed_entry_id}
        assert record_entry_ids(
            await q_operations.tech_get_queue_records(
                QueueKind.entries_to_tag,
                EntryToTag,
                secondary_id=fake_processor_id,
            )
        ) == {dispatched_entry_id}
        assert await m_domain.get_markers(
            user_id=None,
            entries_ids=[failed_entry_id, dispatched_entry_id],
        ) == {dispatched_entry_id: {Marker.can_see_tags}}

    @pytest.mark.asyncio
    async def test_no_processors(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)

        entry_ids = [new_entry_id()]

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(processors=[], batch_size=10, concurrency=10)

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
            await domain.dispatch_entries(
                processors=[processor, processor],
                batch_size=10,
                concurrency=10,
            )

        records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert record_entry_ids(records) == set(entry_ids)

    @pytest.mark.asyncio
    async def test_batch_size(self, loaded_feed: Feed, fake_processor_id: ProcessorId) -> None:
        await q_operations.tech_clear_queue(QueueKind.entries_to_process)
        await q_operations.tech_clear_queue(QueueKind.entries_to_tag)

        user_id = new_user_id()
        entry_ids = list(await l_make.n_entries(loaded_feed, 3))
        await fl_domain.add_link(user_id, loaded_feed.id)
        await save_user_api_key(user_id)

        await domain.push_entries_to_process(entry_ids)

        dispatched = await domain.dispatch_entries(
            processors=[make.processor_dispatch_info(fake_processor_id)],
            batch_size=2,
            concurrency=10,
        )

        assert dispatched == 2

        dispatched_records = await q_operations.tech_get_queue_records(
            QueueKind.entries_to_tag, EntryToTag, secondary_id=fake_processor_id
        )
        remaining_records = await q_operations.tech_get_queue_records(QueueKind.entries_to_process, EntryToProcess)

        assert len(dispatched_records) == 2
        assert len(remaining_records) == 1
        assert record_entry_ids(dispatched_records) | record_entry_ids(remaining_records) == set(entry_ids)
