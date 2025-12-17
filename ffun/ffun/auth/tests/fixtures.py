import uuid

import pytest


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
