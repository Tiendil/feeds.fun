import pytest

from ffun.llms_framework.keys_statuses import Statuses


@pytest.fixture
def statuses() -> Statuses:
    return Statuses()
