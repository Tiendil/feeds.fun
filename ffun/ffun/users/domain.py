import uuid

from . import errors, operations
from .entities import Service, User

# first_user_id = uuid.UUID('59da1b8f-c0c4-416f-908d-85daecfb1726')


add_mapping = operations.add_mapping
get_mapping = operations.get_mapping


async def get_or_create_user_id(service: Service, external_id: str) -> uuid.UUID:
    try:
        return await get_mapping(service, external_id)
    except errors.NoUserMappingFound:
        return await add_mapping(service, external_id)


async def get_or_create_user(service: Service, external_id: str) -> User:
    user_id = await get_or_create_user_id(service, external_id)

    return User(id=user_id)
