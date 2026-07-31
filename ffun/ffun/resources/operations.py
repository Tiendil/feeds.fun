import datetime
from typing import Any, Iterable

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute
from ffun.domain.entities import UserId
from ffun.resources import errors
from ffun.resources.entities import Resource, ResourceReservation, ResourceReservationLimit

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
    execute: ExecuteType, user_ids: list[UserId], kind: int, interval_started_at: datetime.datetime
) -> None:
    if not user_ids:
        return

    sql = """
        INSERT INTO r_resources (user_id, kind, interval_started_at)
        SELECT requested.user_id, %(kind)s, %(interval_started_at)s
        FROM UNNEST(%(user_ids)s::uuid[]) AS requested(user_id)
        ON CONFLICT (user_id, kind, interval_started_at) DO NOTHING
    """

    await execute(sql, {"user_ids": user_ids, "kind": kind, "interval_started_at": interval_started_at})


async def load_resources(
    user_ids: Iterable[UserId], kind: int, interval_started_at: datetime.datetime
) -> dict[UserId, Resource]:
    user_ids = list(dict.fromkeys(user_ids))

    await initialize_resources(execute, user_ids, kind, interval_started_at)

    sql = """
        SELECT * FROM r_resources
        WHERE user_id = ANY(%(user_ids)s) AND kind = %(kind)s AND interval_started_at = %(interval_started_at)s
    """

    results = await execute(sql, {"user_ids": user_ids, "kind": kind, "interval_started_at": interval_started_at})

    return {row["user_id"]: row_to_entry(row) for row in results}


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

    await initialize_resources(execute, user_ids, kind, interval_started_at)

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


async def count_total_resources_per_user(kind: int) -> dict[UserId, int]:
    sql = """
        SELECT user_id, SUM(used) AS count
        FROM r_resources
        WHERE kind = %(kind)s
        GROUP BY user_id
    """

    results = await execute(sql, {"kind": kind})

    return {row["user_id"]: row["count"] for row in results}
