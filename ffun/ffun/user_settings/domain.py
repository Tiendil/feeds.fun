import uuid
from typing import Any, Iterable

from . import operations
from .values import user_settings


async def save_setting(user_id: uuid.UUID,
                       kind: int,
                       value: Any) -> None:
    value_to_save = user_settings.get(kind).type.serialize(value)

    await operations.save_setting(user_id, kind, value_to_save)


async def load_settings(user_id: uuid.UUID,
                        kinds: Iterable[int]) -> Any:
     values = await operations.load_settings(user_id, kinds)

     return {kind: user_settings.get(kind).type.deserialize(value)
             for kind, value in values.items()}


async def load_settings_for_users(user_ids: Iterable[uuid.UUID],
                                  kinds: Iterable[int]) -> dict[uuid.UUID, Any]:

    values = await operations.load_settings_for_users(user_ids, kinds)

    return {user_id: {kind: user_settings.get(kind).type.deserialize(value)
                      for kind, value in user_values.items()}
            for user_id, user_values in values.items()}
