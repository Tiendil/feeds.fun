import uuid
from typing import Any, Iterable

from . import operations
from .entities import UserSettings
from .values import user_settings


async def save_setting(user_id: uuid.UUID, kind: int, value: Any) -> None:
    value_to_save = user_settings.get(kind).type.serialize(value)

    await operations.save_setting(user_id, kind, value_to_save)


def _full_settings(values: dict[int, Any], kinds: Iterable[int]) -> UserSettings:
    result = {}

    for kind in kinds:
        if kind in values:
            result[kind] = user_settings.get(kind).type.deserialize(values[kind])
            continue

        result[kind] = user_settings.get(kind).default

    return result


async def load_settings(user_id: uuid.UUID, kinds: Iterable[int]) -> UserSettings:
    values = await operations.load_settings(user_id, kinds)

    return _full_settings(values, kinds)


async def load_settings_for_users(
    user_ids: Iterable[uuid.UUID], kinds: Iterable[int]
) -> dict[uuid.UUID, UserSettings]:
    values = await operations.load_settings_for_users(user_ids, kinds)

    return {user_id: _full_settings(user_values, kinds) for user_id, user_values in values.items()}
