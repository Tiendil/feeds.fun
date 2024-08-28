import datetime

import pytest

from ffun.domain.datetime_intervals import month_interval_start


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
