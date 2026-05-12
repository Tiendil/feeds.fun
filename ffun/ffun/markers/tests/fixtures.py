from typing import Generator
from unittest import mock

import pytest

from ffun.markers.entities import Marker
from ffun.markers.settings import settings


@pytest.fixture()
def log_business_events_for_all_markers() -> Generator[None, None, None]:
    with mock.patch.object(settings, "log_business_events_for", list(Marker)):
        yield
