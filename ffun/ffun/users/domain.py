import uuid

from .entities import User

first_user_id = uuid.UUID('59da1b8f-c0c4-416f-908d-85daecfb1726')


async def get_first_user() -> User:
    return User(id=first_user_id)
