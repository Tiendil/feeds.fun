import datetime
import itertools
from typing import Any, Iterable, cast

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute
from ffun.domain.entities import UserId
from ffun.resources import errors
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

logger = logging.get_module_logger()


async def _update_consumed_statistics(
    execute: ExecuteType,
    reservations: list[ResourceReservation],
    *,
    used: int,
) -> None:
    if not reservations or used == 0:
        return

    sql = """
        INSERT INTO r_statistics (user_id, kind, date, consumed)
        SELECT
            changes.user_id,
            changes.kind,
            (statement_timestamp() AT TIME ZONE 'UTC')::date,
            changes.consumed
        FROM UNNEST(
            %(user_ids)s::uuid[],
            %(kinds)s::integer[],
            %(consumed)s::bigint[]
        ) AS changes(user_id, kind, consumed)
        ON CONFLICT (user_id, kind, date) DO UPDATE
        SET consumed = r_statistics.consumed + EXCLUDED.consumed,
            updated_at = CURRENT_TIMESTAMP
    """

    await execute(
        sql,
        {
            "user_ids": [reservation.user_id for reservation in reservations],
            "kinds": [reservation.kind for reservation in reservations],
            "consumed": [used] * len(reservations),
        },
    )


def row_to_entry(row: dict[str, Any]) -> Resource:
    return Resource(
        user_id=row["user_id"],
        kind=row["kind"],
        interval_started_at=row["interval_started_at"],
        used=row["used"],
        reserved=row["reserved"],
    )


async def initialize_resources(
    execute: ExecuteType,
    resource_identities: Iterable[ResourceIdentity],
) -> None:
    resource_identities = list(dict.fromkeys(resource_identities))

    if not resource_identities:
        return

    sql = """
        INSERT INTO r_resources (user_id, kind, interval_started_at)
        SELECT requested.user_id, requested.kind, requested.interval_started_at
        FROM UNNEST(
            %(user_ids)s::uuid[],
            %(kinds)s::integer[],
            %(interval_started_ats)s::timestamptz[]
        ) AS requested(user_id, kind, interval_started_at)
        ON CONFLICT (user_id, kind, interval_started_at) DO NOTHING
    """

    await execute(
        sql,
        {
            "user_ids": [resource_identity.user_id for resource_identity in resource_identities],
            "kinds": [resource_identity.kind for resource_identity in resource_identities],
            "interval_started_ats": [
                resource_identity.interval_started_at for resource_identity in resource_identities
            ],
        },
    )


async def load_resources(
    resource_identities: Iterable[ResourceIdentity],
) -> dict[ResourceIdentity, Resource]:
    resource_identities = list(dict.fromkeys(resource_identities))

    if not resource_identities:
        return {}

    await initialize_resources(execute, resource_identities)

    sql = """
        SELECT resources.*
        FROM r_resources AS resources
        JOIN UNNEST(
            %(user_ids)s::uuid[],
            %(kinds)s::integer[],
            %(interval_started_ats)s::timestamptz[]
        ) AS requested(user_id, kind, interval_started_at)
        ON resources.user_id = requested.user_id
        AND resources.kind = requested.kind
        AND resources.interval_started_at = requested.interval_started_at
    """

    results = await execute(
        sql,
        {
            "user_ids": [resource_identity.user_id for resource_identity in resource_identities],
            "kinds": [resource_identity.kind for resource_identity in resource_identities],
            "interval_started_ats": [
                resource_identity.interval_started_at for resource_identity in resource_identities
            ],
        },
    )

    return {
        ResourceIdentity(
            user_id=row["user_id"],
            kind=row["kind"],
            interval_started_at=row["interval_started_at"],
        ): row_to_entry(row)
        for row in results
    }


async def try_to_reserve(
    execute: ExecuteType,
    user_limits: list[ResourceReservationLimit],
    kind: int,
    interval_started_at: datetime.datetime,
    amount: int,
) -> list[ResourceReservation]:
    if not user_limits:
        return []

    user_ids = [user_limit.user_id for user_limit in user_limits]
    limits = [user_limit.limit for user_limit in user_limits]

    if len(user_ids) != len(set(user_ids)):
        raise errors.DuplicateReservationUserIds()

    resource_identities = ResourceIdentity.for_resource(
        user_ids,
        ResourceKey(kind=kind, interval_started_at=interval_started_at),
    )
    await initialize_resources(execute, resource_identities)

    sql = """
        UPDATE r_resources AS resources
        SET reserved = resources.reserved + %(amount)s,
            updated_at = NOW()
        FROM UNNEST(%(user_ids)s::uuid[], %(limits)s::bigint[]) AS requested(user_id, resource_limit)
        WHERE resources.user_id = requested.user_id AND
              resources.kind = %(kind)s AND
              resources.interval_started_at = %(interval_started_at)s AND
              resources.used + resources.reserved + %(amount)s <= requested.resource_limit
        RETURNING resources.user_id
    """

    results = await execute(
        sql,
        {
            "user_ids": user_ids,
            "limits": limits,
            "kind": kind,
            "interval_started_at": interval_started_at,
            "amount": amount,
        },
    )

    reserved_user_ids = {row["user_id"] for row in results}

    return [
        ResourceReservation(
            user_id=user_limit.user_id,
            kind=kind,
            interval_started_at=interval_started_at,
            amount=amount,
        )
        for user_limit in user_limits
        if user_limit.user_id in reserved_user_ids
    ]


async def convert_reserved_to_used(
    execute: ExecuteType,
    reservations: list[ResourceReservation],
    *,
    used: int,
) -> None:
    if not reservations:
        return

    user_ids = [reservation.user_id for reservation in reservations]

    if len(user_ids) != len(set(user_ids)):
        raise errors.DuplicateReservationUserIds()

    sql = """
        UPDATE r_resources AS resources
        SET used = resources.used + %(used)s,
            reserved = resources.reserved - requested.amount,
            updated_at = NOW()
        FROM UNNEST(
            %(user_ids)s::uuid[],
            %(kinds)s::integer[],
            %(interval_started_ats)s::timestamptz[],
            %(amounts)s::bigint[]
        ) AS requested(user_id, kind, interval_started_at, amount)
        WHERE resources.user_id = requested.user_id AND
              resources.kind = requested.kind AND
              resources.interval_started_at = requested.interval_started_at AND
              resources.reserved >= requested.amount
        RETURNING resources.user_id
    """

    results = await execute(
        sql,
        {
            "user_ids": [reservation.user_id for reservation in reservations],
            "kinds": [reservation.kind for reservation in reservations],
            "interval_started_ats": [reservation.interval_started_at for reservation in reservations],
            "amounts": [reservation.amount for reservation in reservations],
            "used": used,
        },
    )

    converted_user_ids = {row["user_id"] for row in results}

    if converted_user_ids != set(user_ids):
        raise errors.CanNotConvertReservedToUsed()

    # Statistics are currently attributed to the UTC date when this conversion is persisted, not to the date
    # when the resource-consuming operation happened or its reservation was created. A delayed retry can therefore
    # move consumption into a later day or month and make statistics diverge from the resource interval whose
    # reservation authorized that usage. Fixing this requires carrying a durable logical consumption time, or a
    # durable reservation/consumption record, through retries. The reservation's interval start cannot substitute
    # for that time because month and lifetime resource intervals do not identify the actual consumption day.
    await _update_consumed_statistics(execute, reservations, used=used)


async def load_resource_history(user_id: UserId, kind: int) -> list[Resource]:
    sql = """
        SELECT * FROM r_resources
        WHERE user_id = %(user_id)s AND kind = %(kind)s
        ORDER BY interval_started_at DESC
    """

    results = await execute(sql, {"user_id": user_id, "kind": kind})

    return [row_to_entry(row) for row in results]


async def load_resource_statistics(
    user_id: UserId,
    kinds: Iterable[ResourceKind],
    interval: ResourceStatisticsInterval,
) -> dict[ResourceKind, ResourceStatisticsSeries]:
    requested_kinds = list(dict.fromkeys(kinds))

    if not requested_kinds:
        return {}

    sql = """
        SELECT
            kind,
            DATE_TRUNC(%(interval)s, date::timestamp)::date AS interval_started_at,
            SUM(consumed) AS consumed
        FROM r_statistics
        WHERE user_id = %(user_id)s AND kind = ANY(%(kinds)s)
        GROUP BY kind, DATE_TRUNC(%(interval)s, date::timestamp)::date
        ORDER BY kind ASC, interval_started_at ASC
    """

    results = await execute(
        sql,
        {
            "user_id": user_id,
            "kinds": requested_kinds,
            "interval": interval.value,
        },
    )

    current_date = datetime.datetime.now(tz=datetime.UTC).date()
    statistics = {
        kind: ResourceStatisticsSeries.from_sorted_values(
            interval,
            (),
            current_date=current_date,
        )
        for kind in requested_kinds
    }

    for kind, rows in itertools.groupby(results, key=lambda row: ResourceKind(cast(int, row["kind"]))):
        statistics[kind] = ResourceStatisticsSeries.from_sorted_values(
            interval,
            (
                (
                    cast(datetime.date, row["interval_started_at"]),
                    cast(int, row["consumed"]),
                )
                for row in rows
            ),
            current_date=current_date,
        )

    return statistics


async def count_total_resources_per_user(kind: int) -> dict[UserId, int]:
    sql = """
        SELECT user_id, SUM(used) AS count
        FROM r_resources
        WHERE kind = %(kind)s
        GROUP BY user_id
    """

    results = await execute(sql, {"kind": kind})

    return {row["user_id"]: row["count"] for row in results}
