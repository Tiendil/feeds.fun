import pytest

from ffun.openai.keys_statuses import Statuses


@pytest.fixture
def statuses() -> Statuses:
    return Statuses()
