import uuid

import pytest
import pytest_asyncio

from ffun.auth.settings import primary_oidc_service_id
from ffun.domain.entities import UserId
from ffun.users.domain import get_or_create_user_id


@pytest.fixture
def external_user_id() -> str:
    return f"external-user-{uuid.uuid4().hex}"


@pytest.fixture
def another_external_user_id() -> str:
    return f"another-external-user-{uuid.uuid4().hex}"


@pytest.fixture
def external_user_email(external_user_id: str) -> str:
    return f"email-{external_user_id}@example.com"


@pytest.fixture
def another_external_user_email(another_external_user_id: str) -> str:
    return f"email-{another_external_user_id}@example.com"
