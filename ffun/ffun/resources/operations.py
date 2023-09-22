import datetime
import uuid
from typing import Any, Iterable

from ffun.core import logging
from ffun.core.postgresql import execute
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


async def initialize_resource(user_id: uuid.UUID, kind: int, interval_started_at: datetime.datetime) -> Resource:
    sql = """
        INSERT INTO r_resources (user_id, kind, interval_started_at)
        VALUES (%(user_id)s, %(kind)s, %(interval_started_at)s)
        ON CONFLICT (user_id, kind, interval_started_at) DO NOTHING
    """

    await execute(sql, {"user_id": user_id, "kind": kind, "interval_started_at": interval_started_at})

    sql = """
    SELECT * FROM r_resources
    WHERE user_id = %(user_id)s AND kind = %(kind)s AND interval_started_at = %(interval_started_at)s
    """

    results = await execute(sql, {"user_id": user_id, "kind": kind, "interval_started_at": interval_started_at})

    return row_to_entry(results[0])


async def load_resources(
    user_ids: Iterable[uuid.UUID], kind: int, interval_started_at: datetime.datetime
) -> dict[uuid.UUID, Resource]:
    sql = """
        SELECT * FROM r_resources
        WHERE user_id = ANY(%(user_ids)s) AND kind = %(kind)s AND interval_started_at = %(interval_started_at)s
    """

    results = await execute(
        sql, {"user_ids": list(user_ids), "kind": kind, "interval_started_at": interval_started_at}
    )

    resources = {}

    for row in results:
        resources[row["user_id"]] = row_to_entry(row)

    for user_id in user_ids:
        if user_id not in resources:
            resources[user_id] = await initialize_resource(user_id, kind, interval_started_at)

    return resources


async def try_to_reserve(
    user_id: uuid.UUID, kind: int, interval_started_at: datetime.datetime, amount: int, limit: int
) -> bool:
    await initialize_resource(user_id, kind, interval_started_at)

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
    user_id: uuid.UUID, kind: int, interval_started_at: datetime.datetime, used: int, reserved: int
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


async def load_resource_history(user_id: uuid.UUID, kind: int) -> list[Resource]:
    sql = """
        SELECT * FROM r_resources
        WHERE user_id = %(user_id)s AND kind = %(kind)s
        ORDER BY interval_started_at DESC
    """

    results = await execute(sql, {"user_id": user_id, "kind": kind})

    return [row_to_entry(row) for row in results]
