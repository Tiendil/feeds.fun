import uuid

from ffun.auth.settings import primary_oidc_service_id
from ffun.domain.entities import UserId
from ffun.users import operations


async def fake_user_id() -> UserId:
    external_id = f"fake-user#{uuid.uuid4()}"
    return await operations.add_mapping(primary_oidc_service_id, external_id)


async def n_users(n: int) -> list[UserId]:
    return [await fake_user_id() for _ in range(n)]
