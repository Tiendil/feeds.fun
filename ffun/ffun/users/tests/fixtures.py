import uuid

import pytest
import pytest_asyncio

from ffun.domain.entities import UserId
from ffun.users.domain import get_or_create_user_id
from ffun.users.entities import Service


@pytest.fixture
def external_user_id() -> str:
    return f"external-user-{uuid.uuid4().hex}"


@pytest.fixture
def another_external_user_id() -> str:
    return f"another-external-user-{uuid.uuid4().hex}"


@pytest_asyncio.fixture
async def internal_user_id(external_user_id: str) -> UserId:
    return await get_or_create_user_id(Service.supertokens, external_user_id)


@pytest_asyncio.fixture
async def another_internal_user_id(another_external_user_id: str) -> UserId:
    return await get_or_create_user_id(Service.supertokens, another_external_user_id)


@pytest.fixture
def five_external_user_ids() -> list[str]:
    return [f"external-user-{uuid.uuid4().hex}" for _ in range(5)]


@pytest_asyncio.fixture
async def five_internal_user_ids(five_external_user_ids: list[str]) -> list[UserId]:
    return [
        await get_or_create_user_id(Service.supertokens, external_user_id)
        for external_user_id in five_external_user_ids
    ]
