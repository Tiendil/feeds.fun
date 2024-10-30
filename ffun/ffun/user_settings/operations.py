from typing import Iterable

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.domain.entities import UserId
from ffun.user_settings.entities import UserSettings

logger = logging.get_module_logger()


async def save_setting(user_id: UserId, kind: int, value: str) -> None:
    sql = """
        INSERT INTO us_settings (user_id, kind, value)
        VALUES (%(user_id)s, %(kind)s, %(value)s)
        ON CONFLICT (user_id, kind)
        DO UPDATE SET value = %(value)s,
                      updated_at = NOW()
        RETURNING created_at, updated_at
    """

    results = await execute(sql, {"user_id": user_id, "kind": kind, "value": value})

    first_set = results[0]["created_at"] == results[0]["updated_at"]

    logger.business_event("setting_updated", user_id=user_id, kind=kind, first_set=first_set)


async def load_settings_for_users(user_ids: Iterable[UserId], kinds: Iterable[int]) -> dict[UserId, UserSettings]:
    sql = """
        SELECT *
        FROM us_settings
        WHERE user_id = ANY(%(user_ids)s)
        AND kind = ANY(%(kinds)s)
    """

    result = await execute(sql, {"user_ids": list(user_ids), "kinds": list(kinds)})

    values: dict[UserId, UserSettings] = {user_id: {} for user_id in user_ids}

    for row in result:
        user_id = row["user_id"]
        kind = row["kind"]
        value = row["value"]

        values[user_id][kind] = value

    return values


async def get_users_with_setting(kind: int, value: str) -> set[UserId]:
    sql = """
        SELECT user_id
        FROM us_settings
        WHERE kind = %(kind)s
        AND value = %(value)s
    """

    result = await execute(sql, {"kind": kind, "value": value})

    return {row["user_id"] for row in result}


async def remove_setting_for_all_users(kind: int) -> None:
    sql = """
        DELETE FROM us_settings
        WHERE kind = %(kind)s
    """

    await execute(sql, {"kind": kind})


async def find_all_kinds() -> set[int]:
    sql = """
        SELECT kind
        FROM us_settings
        GROUP by kind
    """

    result = await execute(sql)
    return {row["kind"] for row in result}
