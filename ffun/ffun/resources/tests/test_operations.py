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
from ffun.resources.entities import Resource, ResourceReservation, ResourceReservationLimit
from ffun.resources.operations import (
    _update_consumed_statistics,
    convert_reserved_to_used,
    count_total_resources_per_user,
    initialize_resources,
    load_resource_history,
    load_resources,
    row_to_entry,
    try_to_reserve,
)


@pytest.fixture  # type: ignore
def interval_started_at() -> datetime.datetime:
    return month_interval_start()


_kind = 214
_another_kind = 215


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
        statistics_date = datetime.date(2020, 1, 1)
        recorded_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        statistics_arguments: dict[str, UserId | int | datetime.date | datetime.datetime] = {
            "user_id": internal_user_id,
            "kind": _kind,
            "date": statistics_date,
            "consumed": 5,
            "recorded_at": recorded_at,
        }

        await execute(
            """
            INSERT INTO r_statistics (user_id, kind, date, consumed, created_at, updated_at)
            VALUES (%(user_id)s, %(kind)s, %(date)s, %(consumed)s, %(recorded_at)s, %(recorded_at)s)
            """,
            statistics_arguments,
        )

        before = await load_statistics(execute, user_ids=[internal_user_id])

        await _update_consumed_statistics(
            execute,
            [
                ResourceReservation(
                    user_id=internal_user_id,
                    kind=_kind,
                    interval_started_at=interval_started_at,
                    amount=13,
                )
            ],
            used=0,
        )

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
        recorded_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        statistics_arguments: dict[str, UserId | int | datetime.datetime] = {
            "user_id": internal_user_id,
            "kind": _kind,
            "consumed": 5,
            "recorded_at": recorded_at,
        }

        await execute(
            """
            INSERT INTO r_statistics (user_id, kind, date, consumed, created_at, updated_at)
            SELECT
                %(user_id)s,
                %(kind)s,
                (statement_timestamp() AT TIME ZONE 'UTC')::date + requested.day_offset,
                %(consumed)s,
                %(recorded_at)s,
                %(recorded_at)s
            FROM UNNEST(ARRAY[0, 1]) AS requested(day_offset)
            """,
            statistics_arguments,
        )

        await _update_consumed_statistics(
            execute,
            [
                ResourceReservation(
                    user_id=internal_user_id,
                    kind=_kind,
                    interval_started_at=interval_started_at,
                    amount=13,
                )
            ],
            used=7,
        )

        statistics = await load_statistics(execute, user_ids=[internal_user_id])

        assert len(statistics) == 2
        assert {statistic["consumed"] for statistic in statistics} == {5, 12}
        assert {statistic["created_at"] for statistic in statistics} == {recorded_at}
        assert sorted(cast(datetime.datetime, statistic["updated_at"]) > recorded_at for statistic in statistics) == [
            False,
            True,
        ]

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

    @pytest.mark.asyncio
    async def test_dates_are_independent(
        self,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        historical_date = datetime.date(2020, 1, 1)
        statistics_arguments: dict[str, UserId | int | datetime.date] = {
            "user_id": internal_user_id,
            "kind": _kind,
            "date": historical_date,
            "consumed": 5,
        }

        await execute(
            """
            INSERT INTO r_statistics (user_id, kind, date, consumed)
            VALUES (%(user_id)s, %(kind)s, %(date)s, %(consumed)s)
            """,
            statistics_arguments,
        )

        await _update_consumed_statistics(
            execute,
            [
                ResourceReservation(
                    user_id=internal_user_id,
                    kind=_kind,
                    interval_started_at=interval_started_at,
                    amount=13,
                )
            ],
            used=7,
        )

        statistics = await load_statistics(execute, user_ids=[internal_user_id])

        assert len(statistics) == 2
        assert {statistic["consumed"] for statistic in statistics} == {5, 7}
        assert next(statistic for statistic in statistics if statistic["date"] == historical_date)["consumed"] == 5


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

    @pytest.mark.parametrize(("amount", "limit"), [(0, 0), (13, 13), (14, 13)])
    @pytest.mark.asyncio
    async def test_does_not_update_statistics(
        self,
        amount: int,
        limit: int,
        internal_user_id: UserId,
        interval_started_at: datetime.datetime,
    ) -> None:
        recorded_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        statistics_arguments: dict[str, UserId | int | datetime.date | datetime.datetime] = {
            "user_id": internal_user_id,
            "kind": _kind,
            "date": datetime.date(2020, 1, 1),
            "consumed": 5,
            "recorded_at": recorded_at,
        }

        await execute(
            """
            INSERT INTO r_statistics (user_id, kind, date, consumed, created_at, updated_at)
            VALUES (%(user_id)s, %(kind)s, %(date)s, %(consumed)s, %(recorded_at)s, %(recorded_at)s)
            """,
            statistics_arguments,
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
        statistics_arguments: dict[str, UserId | int | datetime.date] = {
            "user_id": internal_user_id,
            "kind": _kind,
            "date": datetime.date(2020, 1, 1),
            "consumed": 5,
        }

        await execute(
            """
            INSERT INTO r_statistics (user_id, kind, date, consumed)
            VALUES (%(user_id)s, %(kind)s, %(date)s, %(consumed)s)
            """,
            statistics_arguments,
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
        statistics_arguments: dict[str, UserId | int] = {
            "user_id": internal_user_id,
            "kind": _kind,
            "consumed": maximum_bigint,
        }

        await execute(
            """
            INSERT INTO r_statistics (user_id, kind, date, consumed)
            SELECT
                %(user_id)s,
                %(kind)s,
                (statement_timestamp() AT TIME ZONE 'UTC')::date + requested.day_offset,
                %(consumed)s
            FROM UNNEST(ARRAY[0, 1]) AS requested(day_offset)
            """,
            statistics_arguments,
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
