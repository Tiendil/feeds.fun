import datetime
from typing import cast

import psycopg
import pytest

from ffun.core.postgresql import ExecuteType, execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import UserId
from ffun.resources import errors
from ffun.resources.domain import load_resource
from ffun.resources.entities import (
    Resource,
    ResourceIdentity,
    ResourceKey,
    ResourceKind,
    ResourceReservation,
    ResourceReservationLimit,
    ResourceStatisticsInterval,
    ResourceStatisticsSeries,
)
from ffun.resources.operations import (
    _update_consumed_statistics,
    convert_reserved_to_used,
    count_total_resources_per_user,
    initialize_resources,
    load_resource_history,
    load_resource_statistics,
    load_resources,
    row_to_entry,
    try_to_reserve,
)
from ffun.resources.tests.helpers import consume_resource


@pytest.fixture  # type: ignore
def interval_started_at() -> datetime.datetime:
    return month_interval_start()


_kind = ResourceKind(214)
_another_kind = ResourceKind(215)


async def load_statistics(run: ExecuteType, *, user_ids: list[UserId]) -> list[dict[str, object]]:
    arguments: dict[str, list[UserId]] = {"user_ids": user_ids}

    return cast(
        list[dict[str, object]],
        await run(
            """
            SELECT user_id, kind, date, consumed, created_at, updated_at
            FROM r_statistics
            WHERE user_id = ANY(%(user_ids)s)
            ORDER BY user_id, kind, date
            """,
            arguments,
        ),
    )


class TestUpdateConsumedStatistics:
    @pytest.mark.asyncio
    async def test_empty_reservations(self) -> None:
        async with TableSizeNotChanged("r_statistics"):
            await _update_consumed_statistics(execute, [], used=9)

    @pytest.mark.asyncio
    async def test_zero_used_preserves_existing_statistics(
        self,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        reservation = ResourceReservation(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )
        await _update_consumed_statistics(execute, [reservation], used=5)

        before = await load_statistics(execute, user_ids=[internal_user_id])

        await _update_consumed_statistics(execute, [reservation], used=0)

        after = await load_statistics(execute, user_ids=[internal_user_id])

        assert after == before

    @pytest.mark.asyncio
    async def test_bulk_users_use_database_utc_date(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        reservations = [
            ResourceReservation(
                user_id=internal_user_id,
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=13,
            ),
            ResourceReservation(
                user_id=another_internal_user_id,
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=21,
            ),
        ]

        async with transaction() as transaction_execute:
            utc_hour_result = cast(
                list[dict[str, int]],
                await transaction_execute(
                    "SELECT EXTRACT(HOUR FROM statement_timestamp() AT TIME ZONE 'UTC')::integer AS hour"
                ),
            )
            timezone = "Etc/GMT+12" if utc_hour_result[0]["hour"] < 10 else "Etc/GMT-14"
            timezone_arguments: dict[str, str] = {"timezone": timezone}
            statistics_arguments: dict[str, list[UserId]] = {"user_ids": [internal_user_id, another_internal_user_id]}

            await transaction_execute(
                "SELECT set_config('TimeZone', %(timezone)s, true)",
                timezone_arguments,
            )
            await _update_consumed_statistics(transaction_execute, reservations, used=9)

            statistics = cast(
                list[dict[str, UserId | bool | int]],
                await transaction_execute(
                    """
                    SELECT
                        user_id,
                        kind,
                        consumed,
                        date = (statement_timestamp() AT TIME ZONE 'UTC')::date AS uses_utc_date,
                        date = statement_timestamp()::date AS uses_session_date
                    FROM r_statistics
                    WHERE user_id = ANY(%(user_ids)s)
                    ORDER BY user_id
                    """,
                    statistics_arguments,
                ),
            )

        assert len(statistics) == 2

        for statistic in statistics:
            assert statistic["kind"] == _kind
            assert statistic["consumed"] == 9
            assert statistic["uses_utc_date"]
            assert not statistic["uses_session_date"]

        assert {statistic["user_id"] for statistic in statistics} == {
            internal_user_id,
            another_internal_user_id,
        }

    @pytest.mark.asyncio
    async def test_accumulates_existing_statistics(
        self,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        reservation = ResourceReservation(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )
        await _update_consumed_statistics(execute, [reservation], used=5)

        before = await load_statistics(execute, user_ids=[internal_user_id])

        await _update_consumed_statistics(execute, [reservation], used=7)

        statistics = await load_statistics(execute, user_ids=[internal_user_id])

        assert len(statistics) == 1
        assert statistics[0]["consumed"] == 12
        assert statistics[0]["created_at"] == before[0]["created_at"]
        assert cast(datetime.datetime, statistics[0]["updated_at"]) > cast(
            datetime.datetime,
            before[0]["updated_at"],
        )

    @pytest.mark.asyncio
    async def test_kinds_are_independent(
        self,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        for kind, used in ((_kind, 5), (_another_kind, 7)):
            await _update_consumed_statistics(
                execute,
                [
                    ResourceReservation(
                        user_id=internal_user_id,
                        kind=kind,
                        interval_started_at=interval_started_at,
                        amount=13,
                    )
                ],
                used=used,
            )

        statistics = await load_statistics(execute, user_ids=[internal_user_id])

        assert {statistic["kind"]: statistic["consumed"] for statistic in statistics} == {
            _kind: 5,
            _another_kind: 7,
        }


class TestRowToEntry:
    def test_converts_row(self, internal_user_id: UserId, interval_started_at: datetime.datetime) -> None:
        row = {
            "user_id": internal_user_id,
            "kind": _kind,
            "interval_started_at": interval_started_at,
            "used": 13,
            "reserved": 7,
        }

        assert row_to_entry(row) == Resource(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
            used=13,
            reserved=7,
        )


class TestInitializeResources:
    @pytest.mark.asyncio
    async def test_new_records(
        self, internal_user_id: UserId, another_internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        resource_identities = ResourceIdentity.cartesian_product(
            [internal_user_id, another_internal_user_id],
            [
                ResourceKey(kind=_kind, interval_started_at=interval_started_at),
                ResourceKey(
                    kind=ResourceKind(_kind + 1),
                    interval_started_at=interval_started_at + datetime.timedelta(days=1),
                ),
            ],
        )

        async with TableSizeDelta("r_resources", delta=4):
            await initialize_resources(execute, resource_identities)

        async with TableSizeNotChanged("r_resources"):
            resources = await load_resources(resource_identities)

        assert set(resources) == set(resource_identities)

        for resource_identity, resource in resources.items():
            assert resource.user_id == resource_identity.user_id
            assert resource.kind == resource_identity.kind
            assert resource.interval_started_at == resource_identity.interval_started_at
            assert resource.used == 0
            assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_empty_resource_identities(self) -> None:
        async with TableSizeNotChanged("r_resources"):
            await initialize_resources(execute, [])

    @pytest.mark.asyncio
    async def test_duplicate_resource_identities(
        self, internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        resource_key = ResourceKey(kind=_kind, interval_started_at=interval_started_at)
        resource_identity = ResourceIdentity.single(internal_user_id, resource_key)[0]

        async with TableSizeDelta("r_resources", delta=1):
            await initialize_resources(execute, [resource_identity, resource_identity])

    @pytest.mark.asyncio
    async def test_new_and_existing_resource_identities(
        self, internal_user_id: UserId, another_internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        resource_key = ResourceKey(kind=_kind, interval_started_at=interval_started_at)
        resource_identities = ResourceIdentity.for_resource(
            [internal_user_id, another_internal_user_id],
            resource_key,
        )

        await initialize_resources(execute, [resource_identities[0]])
        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=1,
        )

        async with TableSizeDelta("r_resources", delta=1):
            await initialize_resources(execute, resource_identities)

        resources = await load_resources(resource_identities)

        assert resources[resource_identities[0]].reserved == 1
        assert resources[resource_identities[1]].reserved == 0

    @pytest.mark.asyncio
    async def test_do_not_reinitialized_if_exists(
        self, internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        resource_key = ResourceKey(kind=_kind, interval_started_at=interval_started_at)
        resource_identity = ResourceIdentity.single(internal_user_id, resource_key)[0]

        await initialize_resources(execute, [resource_identity])

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=1,
        )

        async with TableSizeNotChanged("r_resources"):
            await initialize_resources(execute, [resource_identity])

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.reserved == 1


class TestLoadResources:
    @pytest.mark.asyncio
    async def test_empty_resource_identities(self) -> None:
        assert await load_resources([]) == {}

    @pytest.mark.asyncio
    async def test_duplicate_resource_identities(
        self, internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        resource_key = ResourceKey(kind=_kind, interval_started_at=interval_started_at)
        resource_identity = ResourceIdentity.single(internal_user_id, resource_key)[0]

        async with TableSizeDelta("r_resources", delta=1):
            resources = await load_resources([resource_identity, resource_identity])

        assert list(resources) == [resource_identity]

    @pytest.mark.asyncio
    async def test_initialize_requested_identities_if_not_found(
        self, internal_user_id: UserId, another_internal_user_id: UserId, interval_started_at: datetime.datetime
    ) -> None:
        first_resource_key = ResourceKey(kind=_kind, interval_started_at=interval_started_at)
        second_resource_key = ResourceKey(
            kind=ResourceKind(_kind + 1),
            interval_started_at=interval_started_at + datetime.timedelta(days=1),
        )
        first_resource_identity = ResourceIdentity.single(internal_user_id, first_resource_key)[0]
        second_resource_identity = ResourceIdentity.single(another_internal_user_id, second_resource_key)[0]

        await initialize_resources(execute, [first_resource_identity])

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )

        async with TableSizeDelta("r_resources", delta=1):
            resources = await load_resources([first_resource_identity, second_resource_identity])

        assert len(resources) == 2
        assert set(resources) == {first_resource_identity, second_resource_identity}

        resource_1 = resources[first_resource_identity]

        assert resource_1.user_id == internal_user_id
        assert resource_1.kind == _kind
        assert resource_1.interval_started_at == interval_started_at
        assert resource_1.used == 0
        assert resource_1.reserved == 13

        resource_2 = resources[second_resource_identity]

        assert resource_2.user_id == another_internal_user_id
        assert resource_2.kind == second_resource_key.kind
        assert resource_2.interval_started_at == second_resource_key.interval_started_at
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

    @pytest.mark.parametrize(("amount", "limit"), [(0, 0), (13, 13), (14, 13)])
    @pytest.mark.asyncio
    async def test_does_not_update_statistics(
        self,
        amount: int,
        limit: int,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        await consume_resource(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at - datetime.timedelta(days=1),
            reserved=5,
            used=5,
        )

        before = await load_statistics(execute, user_ids=[internal_user_id])

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=limit)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=amount,
        )

        after = await load_statistics(execute, user_ids=[internal_user_id])

        assert after == before

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

        resource_key = ResourceKey(kind=_kind, interval_started_at=interval_started_at)
        resource_identities = ResourceIdentity.for_resource(
            [internal_user_id, another_internal_user_id],
            resource_key,
        )
        resources = await load_resources(resource_identities)

        assert result == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=_kind,
                interval_started_at=interval_started_at,
                amount=13,
            )
        ]
        assert resources[resource_identities[0]].reserved == 13
        assert resources[resource_identities[1]].reserved == 0

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
        async with TableSizeNotChanged("r_resources"), TableSizeNotChanged("r_statistics"):
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

        statistics = await load_statistics(
            execute,
            user_ids=[internal_user_id, another_internal_user_id],
        )

        assert {(statistic["user_id"], statistic["kind"]): statistic["consumed"] for statistic in statistics} == {
            (internal_user_id, _kind): 9,
            (another_internal_user_id, _another_kind): 9,
        }

    @pytest.mark.asyncio
    async def test_updates_daily_statistics(
        self,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        another_interval_started_at = interval_started_at + datetime.timedelta(days=1)
        statistics_arguments: dict[str, UserId | int] = {"user_id": internal_user_id, "kind": _kind}

        first_reservations = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=13)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )
        second_reservations = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=7)],
            kind=_kind,
            interval_started_at=another_interval_started_at,
            amount=7,
        )

        async with transaction() as transaction_execute:
            await convert_reserved_to_used(
                transaction_execute,
                first_reservations,
                used=9,
            )
            await convert_reserved_to_used(
                transaction_execute,
                second_reservations,
                used=7,
            )

            statistics = cast(
                list[dict[str, bool | int]],
                await transaction_execute(
                    """
                    SELECT
                        date = (statement_timestamp() AT TIME ZONE 'UTC')::date AS is_today,
                        consumed
                    FROM r_statistics
                    WHERE user_id = %(user_id)s AND kind = %(kind)s
                    """,
                    statistics_arguments,
                ),
            )

        assert statistics == [{"is_today": True, "consumed": 16}]

    @pytest.mark.asyncio
    async def test_releases_reservations(
        self,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        statistics_arguments: dict[str, UserId | int] = {"user_id": internal_user_id, "kind": _kind}

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

        statistics = cast(
            list[dict[str, int]],
            await execute(
                "SELECT consumed FROM r_statistics WHERE user_id = %(user_id)s AND kind = %(kind)s",
                statistics_arguments,
            ),
        )

        assert statistics == []

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
        await consume_resource(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at - datetime.timedelta(days=1),
            reserved=5,
            used=5,
        )

        before_statistics = await load_statistics(
            execute,
            user_ids=[internal_user_id, another_internal_user_id],
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

        after_statistics = await load_statistics(
            execute,
            user_ids=[internal_user_id, another_internal_user_id],
        )

        assert after_statistics == before_statistics

    @pytest.mark.asyncio
    async def test_statistics_failure_rolls_back_resource_conversion(
        self,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        reservations = await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=1)],
            kind=_kind,
            interval_started_at=interval_started_at,
            amount=1,
        )
        maximum_bigint = 2**63 - 1
        await consume_resource(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at - datetime.timedelta(days=1),
            reserved=maximum_bigint,
            used=maximum_bigint,
        )

        before_statistics = await load_statistics(execute, user_ids=[internal_user_id])

        with pytest.raises(psycopg.errors.NumericValueOutOfRange):  # type: ignore[misc]
            async with transaction() as transaction_execute:
                await convert_reserved_to_used(
                    transaction_execute,
                    reservations,
                    used=1,
                )

        resource = await load_resource(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
        )
        after_statistics = await load_statistics(execute, user_ids=[internal_user_id])

        assert resource.used == 0
        assert resource.reserved == 1
        assert after_statistics == before_statistics

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


class TestLoadResourceStatistics:
    @pytest.mark.asyncio
    async def test_empty_kinds(self, internal_user_id: UserId) -> None:
        statistics = await load_resource_statistics(
            user_id=internal_user_id,
            kinds=[],
            interval=ResourceStatisticsInterval.day,
        )

        assert statistics == {}

    @pytest.mark.asyncio
    async def test_kind_without_history(self, internal_user_id: UserId) -> None:
        statistics = await load_resource_statistics(
            user_id=internal_user_id,
            kinds=[_kind],
            interval=ResourceStatisticsInterval.day,
        )

        assert statistics == {
            _kind: ResourceStatisticsSeries(
                first_date=datetime.datetime.now(tz=datetime.UTC).date(),
                values=(0,),
            )
        }

    @pytest.mark.asyncio
    async def test_day_interval_filters_and_groups_results(
        self, internal_user_id: UserId, another_internal_user_id: UserId
    ) -> None:
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
            reserved=2,
            converted=2,
        )
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2024, 1, 3, tzinfo=datetime.UTC),
            reserved=4,
            converted=4,
        )
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_another_kind,
            interval_started_at=datetime.datetime(2024, 1, 2, tzinfo=datetime.UTC),
            reserved=5,
            converted=5,
        )
        await reserve_and_convert(
            user_id=another_internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
            reserved=99,
            converted=99,
        )

        statistics = await load_resource_statistics(
            user_id=internal_user_id,
            kinds=[_another_kind, _kind, _kind],
            interval=ResourceStatisticsInterval.day,
        )
        current_date = datetime.datetime.now(tz=datetime.UTC).date()

        assert statistics == {
            _another_kind: ResourceStatisticsSeries(
                first_date=current_date,
                values=(5,),
            ),
            _kind: ResourceStatisticsSeries(
                first_date=current_date,
                values=(6,),
            ),
        }

    @pytest.mark.asyncio
    async def test_month_interval(self, internal_user_id: UserId) -> None:
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
            reserved=2,
            converted=2,
        )
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2024, 1, 31, tzinfo=datetime.UTC),
            reserved=3,
            converted=3,
        )
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2024, 2, 1, tzinfo=datetime.UTC),
            reserved=4,
            converted=4,
        )

        statistics = await load_resource_statistics(
            user_id=internal_user_id,
            kinds=[_kind],
            interval=ResourceStatisticsInterval.month,
        )
        current_date = datetime.datetime.now(tz=datetime.UTC).date()

        assert statistics == {
            _kind: ResourceStatisticsSeries(
                first_date=ResourceStatisticsInterval.month.start_date(current_date),
                values=(9,),
            )
        }

    @pytest.mark.asyncio
    async def test_year_interval(self, internal_user_id: UserId) -> None:
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
            reserved=2,
            converted=2,
        )
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2024, 12, 31, tzinfo=datetime.UTC),
            reserved=3,
            converted=3,
        )
        await reserve_and_convert(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
            reserved=4,
            converted=4,
        )

        statistics = await load_resource_statistics(
            user_id=internal_user_id,
            kinds=[_kind],
            interval=ResourceStatisticsInterval.year,
        )
        current_date = datetime.datetime.now(tz=datetime.UTC).date()

        assert statistics == {
            _kind: ResourceStatisticsSeries(
                first_date=ResourceStatisticsInterval.year.start_date(current_date),
                values=(9,),
            )
        }


async def reserve_and_convert(
    *,
    user_id: UserId,
    kind: int,
    interval_started_at: datetime.datetime,
    reserved: int,
    converted: int,
) -> None:
    await consume_resource(
        user_id=user_id,
        kind=kind,
        interval_started_at=interval_started_at,
        reserved=reserved,
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
