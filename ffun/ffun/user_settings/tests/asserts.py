import uuid
from typing import Iterable

from ffun.user_settings import operations


async def has_settings(user_id: uuid.UUID, values: dict[int, str]) -> None:
    settings = await operations.load_settings_for_users([user_id], list(values.keys()))
    assert settings[user_id] == values


async def has_no_settings(user_id: uuid.UUID, kinds: Iterable[int]) -> None:
    settings = await operations.load_settings_for_users([user_id], list(kinds))
    assert set(kinds) - set(settings[user_id]) == set(kinds)
