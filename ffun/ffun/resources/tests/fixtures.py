import pytest

from ffun.resources.entities import ResourceKind


@pytest.fixture  # type: ignore
def resource_kind() -> ResourceKind:
    return ResourceKind(214)


@pytest.fixture  # type: ignore
def another_resource_kind() -> ResourceKind:
    return ResourceKind(215)
