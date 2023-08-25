import uuid

from ffun.users import errors, operations
from ffun.users.entities import Service, User

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
