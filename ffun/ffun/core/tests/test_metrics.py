import datetime

import pytest

from ffun.core import utils
from ffun.core.metrics import Accumulator
from ffun.core.tests.helpers import assert_logs_has_business_slice, assert_logs_has_no_business_slice, capture_logs


class TestAccumulator:

    @pytest.fixture()
    def accumulator(self) -> Accumulator:
        interval = datetime.timedelta(seconds=10)
        event = "test_event"
        attributes = {"key": "value"}

        return Accumulator(interval, event, **attributes)

    def test_initialization(self, accumulator: Accumulator) -> None:

        assert accumulator.interval == datetime.timedelta(seconds=10)
        assert accumulator.event == "test_event"
        assert accumulator.attributes == {"key": "value"}
        assert accumulator._last_measure_at is None
        assert accumulator._count == 0
        assert accumulator._sum == 0

    def test_measure(self, accumulator: Accumulator) -> None:
        accumulator.measure(5)

        pytest.approx(accumulator._last_measure_at, utils.now(), abs=1)
        assert accumulator._count == 1
        assert accumulator._sum == 5

        last_measure_at = accumulator._last_measure_at

        accumulator.measure(10)
        accumulator.measure(13)

        assert accumulator._count == 3
        assert accumulator._sum == 28

        assert accumulator._last_measure_at == last_measure_at

    def test_flush_if_time__no_measures(self, accumulator: Accumulator) -> None:

        with capture_logs() as logs:
            accumulator.flush_if_time()

        assert_logs_has_no_business_slice(logs, name=accumulator.event)

        assert accumulator._last_measure_at is None
        assert accumulator._count == 0
        assert accumulator._sum == 0

    def test_flush_if_time__measures_not_ready(self, accumulator: Accumulator) -> None:
        accumulator.measure(5)

        with capture_logs() as logs:
            accumulator.flush_if_time()

        assert_logs_has_no_business_slice(logs, name=accumulator.event)

        assert accumulator._last_measure_at is not None
        assert accumulator._count == 1
        assert accumulator._sum == 5

    def test_flush_if_time__measures_ready(self, accumulator: Accumulator) -> None:
        accumulator.measure(5)
        accumulator.measure(10)

        assert accumulator._last_measure_at is not None

        accumulator._last_measure_at -= datetime.timedelta(seconds=11)

        with capture_logs() as logs:
            accumulator.flush_if_time()

        assert_logs_has_business_slice(logs, name=accumulator.event, user_id=None, count=2, sum=15, key="value")

        assert accumulator._last_measure_at is None
        assert accumulator._count == 0
        assert accumulator._sum == 0
