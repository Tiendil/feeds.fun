import uuid

import pytest
import pytest_asyncio

from ffun.users.domain import get_or_create_user_id
from ffun.users.entities import Service


@pytest.fixture
def external_user_id() -> str:
    return f"external-user-{uuid.uuid4().hex}"


@pytest.fixture
def another_external_user_id() -> str:
    return f"another-external-user-{uuid.uuid4().hex}"


@pytest_asyncio.fixture
async def internal_user_id(external_user_id: str) -> uuid.UUID:
    return await get_or_create_user_id(Service.supertokens, external_user_id)


@pytest_asyncio.fixture
async def another_internal_user_id(another_external_user_id: str) -> uuid.UUID:
    return await get_or_create_user_id(Service.supertokens, another_external_user_id)
