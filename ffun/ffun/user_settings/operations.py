import uuid
from typing import Iterable

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.user_settings.entities import UserSettings

logger = logging.get_module_logger()


async def save_setting(user_id: uuid.UUID, kind: int, value: str) -> None:
    sql = """
        INSERT INTO us_settings (user_id, kind, value)
        VALUES (%(user_id)s, %(kind)s, %(value)s)
        ON CONFLICT (user_id, kind)
        DO UPDATE SET value = %(value)s,
                      updated_at = NOW()
    """

    await execute(sql, {"user_id": user_id, "kind": kind, "value": value})


async def load_settings_for_users(
    user_ids: Iterable[uuid.UUID], kinds: Iterable[int]
) -> dict[uuid.UUID, UserSettings]:
    sql = """
        SELECT *
        FROM us_settings
        WHERE user_id = ANY(%(user_ids)s)
        AND kind = ANY(%(kinds)s)
    """

    result = await execute(sql, {"user_ids": user_ids, "kinds": kinds})

    values: dict[uuid.UUID, UserSettings] = {}

    for row in result:
        user_id = row["user_id"]
        kind = row["kind"]
        value = row["value"]

        assert isinstance(user_id, uuid.UUID)

        if user_id not in values:
            values[user_id] = {}

        values[user_id][kind] = value

    return values


async def load_settings(user_id: uuid.UUID, kinds: Iterable[int]) -> UserSettings:
    values = await load_settings_for_users([user_id], kinds)

    return values[user_id] if user_id in values else {}


async def get_users_with_setting(kind: int, value: str) -> set[uuid.UUID]:
    sql = """
        SELECT user_id
        FROM us_settings
        WHERE kind = %(kind)s
        AND value = %(value)s
    """

    result = await execute(sql, {"kind": kind, "value": value})

    return {row["user_id"] for row in result}
