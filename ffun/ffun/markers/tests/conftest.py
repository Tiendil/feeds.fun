import pytest

from ffun.markers.tests.fixtures import *  # noqa


@pytest.fixture(autouse=True)
def markers_tests_log_business_events_for_all_markers(log_business_events_for_all_markers: None) -> None:
    pass
