import datetime

import pytest

from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import UserId
from ffun.resources import errors
from ffun.resources.domain import load_resource
from ffun.resources.entities import ResourceReservation, ResourceReservationLimit
from ffun.resources.operations import (
    convert_reserved_to_used,
    count_total_resources_per_user,
    initialize_resources,
    load_resource_history,
    load_resources,
    try_to_reserve,
)


@pytest.fixture  # type: ignore
def interval_started_at() -> datetime.datetime:
    return month_interval_start()


_kind = 214
_another_kind = 215


class TestInitializeResources:
    @pytest.mark.asyncio
    async def test_new_records(
        self, internal_user_id: UserId, another_internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        user_ids = [internal_user_id, another_internal_user_id]

        async with TableSizeDelta("r_resources", delta=2):
            await initialize_resources(execute, user_ids=user_ids, kind=_kind, interval_started_at=interval_started_at)

        async with TableSizeNotChanged("r_resources"):
            resources = await load_resources(user_ids=user_ids, kind=_kind, interval_started_at=interval_started_at)

        assert set(resources) == set(user_ids)

        for user_id, resource in resources.items():
            assert resource.user_id == user_id
            assert resource.kind == _kind
            assert resource.interval_started_at == interval_started_at
            assert resource.used == 0
            assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_empty_user_ids(self, interval_started_at: datetime.datetime) -> None:
        async with TableSizeNotChanged("r_resources"):
            await initialize_resources(execute, user_ids=[], kind=_kind, interval_started_at=interval_started_at)

    @pytest.mark.asyncio
    async def test_duplicate_user_ids(self, internal_user_id: UserId, interval_started_at: datetime.datetime) -> None:
        async with TableSizeDelta("r_resources", delta=1):
            await initialize_resources(
                execute,
                user_ids=[internal_user_id, internal_user_id],
                kind=_kind,
                interval_started_at=interval_started_at,
            )

    @pytest.mark.asyncio
    async def test_new_and_existing_user_ids(
        self, internal_user_id: UserId, another_internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        await initialize_resources(
            execute, user_ids=[internal_user_id], kind=_kind, interval_started_at=interval_started_at
        )
        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=1,
        )

        async with TableSizeDelta("r_resources", delta=1):
            await initialize_resources(
                execute,
                user_ids=[internal_user_id, another_internal_user_id],
                kind=_kind,
                interval_started_at=interval_started_at,
            )

        resources = await load_resources(
            user_ids=[internal_user_id, another_internal_user_id],
            kind=_kind,
            interval_started_at=interval_started_at,
        )

        assert resources[internal_user_id].reserved == 1
        assert resources[another_internal_user_id].reserved == 0

    @pytest.mark.asyncio
    async def test_do_not_reinitialized_if_exists(
        self, internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        await initialize_resources(
            execute, user_ids=[internal_user_id], kind=_kind, interval_started_at=interval_started_at
        )

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=1,
        )

        async with TableSizeNotChanged("r_resources"):
            await initialize_resources(
                execute, user_ids=[internal_user_id], kind=_kind, interval_started_at=interval_started_at
            )

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.reserved == 1


class TestLoadResources:
    """Most functionality are tested in other classes."""

    @pytest.mark.asyncio
    async def test_duplicate_user_ids(self, internal_user_id: UserId, interval_started_at: datetime.datetime) -> None:
        async with TableSizeDelta("r_resources", delta=1):
            resources = await load_resources(
                user_ids=[internal_user_id, internal_user_id],
                kind=_kind,
                interval_started_at=interval_started_at,
            )

        assert list(resources) == [internal_user_id]

    @pytest.mark.asyncio
    async def test_initialize_if_not_found(
        self, internal_user_id: UserId, another_internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        await initialize_resources(
            execute, user_ids=[internal_user_id], kind=_kind, interval_started_at=interval_started_at
        )

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )

        async with TableSizeDelta("r_resources", delta=1):
            resources = await load_resources(
                user_ids=[internal_user_id, another_internal_user_id],
                kind=_kind,
                interval_started_at=interval_started_at,
            )

        assert len(resources) == 2

        resource_1 = resources[internal_user_id]

        assert resource_1.user_id == internal_user_id
        assert resource_1.kind == _kind
        assert resource_1.interval_started_at == interval_started_at
        assert resource_1.used == 0
        assert resource_1.reserved == 13

        resource_2 = resources[another_internal_user_id]

        assert resource_2.user_id == another_internal_user_id
        assert resource_2.kind == _kind
        assert resource_2.interval_started_at == interval_started_at
        assert resource_2.used == 0
        assert resource_2.reserved == 0


class TestTryToReserve:
    @pytest.mark.asyncio
    async def test_empty_user_limits(self, interval_started_at: datetime.datetime) -> None:
        async with TableSizeNotChanged("r_resources"):
            result = await try_to_reserve(
                execute,
                user_limits=[],
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=1,
            )

        assert result == []

    @pytest.mark.parametrize("amount", [0, 1, 100])
    @pytest.mark.asyncio
    async def test_for_not_existed_resource(
        self, amount: int, internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        result = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=amount,
        )

        assert result == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=amount,
            )
        ]

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.used == 0
        assert resource.reserved == amount

    @pytest.mark.asyncio
    async def test_for_existed_resource(
        self, internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        result = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=1,
        )

        result = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )

        assert result == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=13,
            )
        ]

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.used == 0
        assert resource.reserved == 14

    @pytest.mark.asyncio
    async def test_not_enough(self, internal_user_id: UserId, interval_started_at: datetime.datetime) -> None:
        result = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=101,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_bulk_reservation_with_per_user_limits(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        result = await try_to_reserve(
            execute,
            user_limits=[
                ResourceReservationLimit(user_id=internal_user_id, limit=13),
                ResourceReservationLimit(user_id=another_internal_user_id, limit=12),
            ],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )

        resources = await load_resources(
            user_ids=[internal_user_id, another_internal_user_id],
            kind=_kind,
            interval_started_at=interval_started_at,
        )

        assert result == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=13,
            )
        ]
        assert resources[internal_user_id].reserved == 13
        assert resources[another_internal_user_id].reserved == 0

    @pytest.mark.asyncio
    async def test_successful_reservations_preserve_input_order(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        result = await try_to_reserve(
            execute,
            user_limits=[
                ResourceReservationLimit(user_id=another_internal_user_id, limit=13),
                ResourceReservationLimit(user_id=internal_user_id, limit=13),
            ],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )

        assert result == [
            ResourceReservation(
                user_id=another_internal_user_id,
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=13,
            ),
            ResourceReservation(
                user_id=internal_user_id,
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=13,
            ),
        ]

    @pytest.mark.asyncio
    async def test_duplicate_user_ids_raise_error(
        self, internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        with pytest.raises(errors.DuplicateReservationUserIds):
            await try_to_reserve(
                execute,
                user_limits=[
                    ResourceReservationLimit(user_id=internal_user_id, limit=12),
                    ResourceReservationLimit(user_id=internal_user_id, limit=13),
                ],
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=13,
            )

        history = await load_resource_history(user_id=internal_user_id, kind=_kind)

        assert history == []


class TestConvertReservedToUsed:
    @pytest.mark.asyncio
    async def test_empty_reservations(self) -> None:
        async with TableSizeNotChanged("r_resources"):
            await convert_reserved_to_used(execute, [], used=9)

    @pytest.mark.asyncio
    async def test_consumes_heterogeneous_reservations(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        another_interval_started_at = interval_started_at + datetime.timedelta(days=1)

        first_reservations = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=13)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )

        second_reservations = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=another_internal_user_id, limit=21)],
            kind=_another_kind,
            interval_started_at=another_interval_started_at,
            amount=21,
        )

        async with transaction() as transaction_execute:
            await convert_reserved_to_used(
                transaction_execute,
                first_reservations + second_reservations,
                used=9,
            )

        first_resource = await load_resource(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
        )
        second_resource = await load_resource(
            user_id=another_internal_user_id,
            kind=_another_kind,
            interval_started_at=another_interval_started_at,
        )

        assert first_resource.used == 9
        assert first_resource.reserved == 0
        assert second_resource.used == 9
        assert second_resource.reserved == 0

    @pytest.mark.asyncio
    async def test_releases_reservations(
        self,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        reservations = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=13)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )

        async with transaction() as transaction_execute:
            await convert_reserved_to_used(
                transaction_execute,
                reservations,
                used=0,
            )

        resource = await load_resource(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
        )

        assert resource.used == 0
        assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_one_failure_rolls_back_all_conversions(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        reservations = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=13)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )
        reservations.append(
            ResourceReservation(
                user_id=another_internal_user_id,
                kind=_another_kind,
                interval_started_at=interval_started_at,
                amount=13,
            )
        )

        with pytest.raises(errors.CanNotConvertReservedToUsed):
            async with transaction() as transaction_execute:
                await convert_reserved_to_used(
                    transaction_execute,
                    reservations,
                    used=9,
                )

        resource = await load_resource(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
        )

        assert resource.used == 0
        assert resource.reserved == 13

    @pytest.mark.asyncio
    async def test_duplicate_user_ids(self, internal_user_id: UserId, interval_started_at: datetime.datetime) -> None:
        reservation = ResourceReservation(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )
        duplicate_reservation = ResourceReservation(
            user_id=internal_user_id,
            kind=_another_kind,
            interval_started_at=interval_started_at + datetime.timedelta(days=1),
            amount=9,
        )

        with pytest.raises(errors.DuplicateReservationUserIds):
            await convert_reserved_to_used(
                execute,
                [reservation, duplicate_reservation],
                used=9,
            )


class TestLoadResourceHistory:
    @pytest.mark.asyncio
    async def test_no_history(self, internal_user_id: UserId) -> None:
        history = await load_resource_history(user_id=internal_user_id, kind=_kind)

        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_with_history(self, internal_user_id: UserId, another_internal_user_id: UserId) -> None:
        internal_1 = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        internal_2 = datetime.datetime(2020, 2, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        internal_3 = datetime.datetime(2020, 3, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=internal_1,
            amount=13,
        )

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=internal_3,
            amount=14,
        )

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=another_internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=internal_2,
            amount=15,
        )

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_another_kind,
            interval_started_at=internal_3,
            amount=16,
        )

        history = await load_resource_history(user_id=internal_user_id, kind=_kind)

        assert len(history) == 2

        assert history[0].user_id == internal_user_id
        assert history[0].interval_started_at == internal_3
        assert history[0].reserved == 14

        assert history[1].user_id == internal_user_id
        assert history[1].interval_started_at == internal_1
        assert history[1].reserved == 13

        history = await load_resource_history(user_id=another_internal_user_id, kind=_kind)

        assert len(history) == 1

        assert history[0].user_id == another_internal_user_id
        assert history[0].interval_started_at == internal_2
        assert history[0].reserved == 15


async def reserve_and_convert(
    *,
    user_id: UserId,
    kind: int,
    interval_started_at: datetime.datetime,
    reserved: int,
    converted: int,
) -> None:
    await try_to_reserve(
        execute,
        user_limits=[ResourceReservationLimit(user_id=user_id, limit=100)],
        kind=kind,
        interval_started_at=interval_started_at,
        amount=reserved,
    )

    async with transaction() as transaction_execute:
        await convert_reserved_to_used(
            transaction_execute,
            [
                ResourceReservation(
                    user_id=user_id,
                    kind=kind,
                    interval_started_at=interval_started_at,
                    amount=converted,
                )
            ],
            used=converted,
        )


class TestCountTotalResourcesPerUser:

    @pytest.mark.asyncio
    async def test(self, internal_user_id: UserId, another_internal_user_id: UserId) -> None:
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            reserved=13,
            converted=10,
        )
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2020, 3, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            reserved=14,
            converted=14,
        )
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_another_kind,
            interval_started_at=datetime.datetime(2020, 3, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            reserved=6,
            converted=6,
        )
        await reserve_and_convert(
            user_id=another_internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2020, 2, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            reserved=15,
            converted=14,
        )
        await reserve_and_convert(
            user_id=another_internal_user_id,
            kind=_another_kind,
            interval_started_at=datetime.datetime(2020, 2, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            reserved=6,
            converted=6,
        )

        numbers = await count_total_resources_per_user(kind=_kind)

        assert numbers[internal_user_id] == 24
        assert numbers[another_internal_user_id] == 14
