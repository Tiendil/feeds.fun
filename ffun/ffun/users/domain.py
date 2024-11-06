from ffun.domain.entities import UserId
from ffun.users import errors, operations
from ffun.users.entities import Service, User

add_mapping = operations.add_mapping
get_mapping = operations.get_mapping
count_total_users = operations.count_total_users


async def get_or_create_user_id(service: Service, external_id: str) -> UserId:
    try:
        return await get_mapping(service, external_id)
    except errors.NoUserMappingFound:
        return await add_mapping(service, external_id)


async def get_or_create_user(service: Service, external_id: str) -> User:
    user_id = await get_or_create_user_id(service, external_id)

    return User(id=user_id)
