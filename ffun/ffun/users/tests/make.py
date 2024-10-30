import uuid

from ffun.domain.entities import UserId
from ffun.users import operations
from ffun.users.entities import Service


async def fake_user_id() -> UserId:
    external_id = f"fake-user#{uuid.uuid4()}"
    return await operations.add_mapping(Service.supertokens, external_id)


async def n_users(n: int) -> list[UserId]:
    return [await fake_user_id() for _ in range(n)]
