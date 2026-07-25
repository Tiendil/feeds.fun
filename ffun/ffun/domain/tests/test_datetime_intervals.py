import datetime

import pytest
from pytest_mock import MockerFixture

from ffun.domain.datetime_intervals import (
    LIFETIME_INTERVAL_END_MARKER,
    LIFETIME_INTERVAL_START_MARKER,
    day_interval_start,
    month_interval_start,
)


def test_lifetime_interval_start_marker() -> None:
    assert LIFETIME_INTERVAL_START_MARKER == datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)


def test_lifetime_interval_end_marker() -> None:
    assert LIFETIME_INTERVAL_END_MARKER == datetime.datetime.max.replace(tzinfo=datetime.UTC)


class TestDayIntervalStart:

    @pytest.mark.asyncio
    async def test_explicit_value_truncated_to_midnight(self) -> None:
        now = datetime.datetime.now()

        assert day_interval_start(now) == datetime.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=now.tzinfo,
        )

    def test_midnight_boundary(self) -> None:
        midnight = datetime.datetime.now(tz=datetime.UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        assert day_interval_start(midnight) == midnight

    def test_default_value(self, mocker: MockerFixture) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        mocker.patch("ffun.domain.datetime_intervals.utils.now", return_value=now)

        assert day_interval_start() == now.replace(hour=0, minute=0, second=0, microsecond=0)


class TestMonthIntervalStart:

    @pytest.mark.asyncio
    async def test_month_interval_start(self) -> None:
        now = datetime.datetime.now()

        assert month_interval_start(now) == datetime.datetime(
            year=now.year,
            month=now.month,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=now.tzinfo,
        )

    def test_default_value(self, mocker: MockerFixture) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        mocker.patch("ffun.domain.datetime_intervals.utils.now", return_value=now)

        assert month_interval_start() == now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
