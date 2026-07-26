import datetime
from typing import Any, Iterable

from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute
from ffun.domain.entities import UserId
from ffun.resources import errors
from ffun.resources.entities import Resource

logger = logging.get_module_logger()


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
    user_id: UserId,
    kind: int,
    interval_started_at: datetime.datetime,
    amount: int,
    limit: int,
) -> bool:
    await initialize_resources(execute, [user_id], kind, interval_started_at)

    sql = """
        UPDATE r_resources
        SET reserved = reserved + %(amount)s,
            updated_at = NOW()
        WHERE user_id = %(user_id)s AND
              kind = %(kind)s AND
              interval_started_at = %(interval_started_at)s AND
              used + reserved + %(amount)s <= %(limit)s
        RETURNING *
    """

    results = await execute(
        sql,
        {
            "user_id": user_id,
            "kind": kind,
            "interval_started_at": interval_started_at,
            "amount": amount,
            "limit": limit,
        },
    )

    return len(results) > 0


async def convert_reserved_to_used(
    user_id: UserId, kind: int, interval_started_at: datetime.datetime, used: int, reserved: int
) -> None:
    sql = """
        UPDATE r_resources
        SET used = used + %(used)s,
            reserved = reserved - %(reserved)s,
            updated_at = NOW()
        WHERE user_id = %(user_id)s AND
              kind = %(kind)s AND
              interval_started_at = %(interval_started_at)s AND
              reserved >= %(reserved)s
        RETURNING *
    """

    result = await execute(
        sql,
        {
            "user_id": user_id,
            "kind": kind,
            "interval_started_at": interval_started_at,
            "used": used,
            "reserved": reserved,
        },
    )

    if not result:
        raise errors.CanNotConvertReservedToUsed()


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
