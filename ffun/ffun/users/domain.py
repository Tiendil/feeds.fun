from ffun.domain.entities import IdPId, UserId
from ffun.users import errors, operations
from ffun.users.entities import User

add_mapping = operations.add_mapping
get_mapping = operations.get_mapping
count_total_users = operations.count_total_users
tech_move_user = operations.tech_move_user
get_user_external_ids = operations.get_user_external_ids
unlink_user = operations.unlink_user


async def check_external_user_exists(service: IdPId, external_id: str) -> bool:
    try:
        await get_mapping(service, external_id)
        return True
    except errors.NoUserMappingFound:
        return False


async def get_or_create_user_id(service: IdPId, external_id: str) -> UserId:
    try:
        return await get_mapping(service, external_id)
    except errors.NoUserMappingFound:
        return await add_mapping(service, external_id)


async def get_or_create_user(service: IdPId, external_id: str) -> User:
    user_id = await get_or_create_user_id(service, external_id)

    return User(id=user_id)
