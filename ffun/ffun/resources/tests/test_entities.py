import datetime

import pytest

from ffun.resources.entities import ResourceStatisticsInterval, ResourceStatisticsSeries


class TestResourceStatisticsInterval:
    @pytest.mark.parametrize(
        "interval, expected",
        [
            (ResourceStatisticsInterval.day, datetime.date(2024, 11, 23)),
            (ResourceStatisticsInterval.month, datetime.date(2024, 11, 1)),
            (ResourceStatisticsInterval.year, datetime.date(2024, 1, 1)),
        ],
    )
    def test_start_date(
        self,
        interval: ResourceStatisticsInterval,
        expected: datetime.date,
    ) -> None:
        assert interval.start_date(datetime.date(2024, 11, 23)) == expected

    @pytest.mark.parametrize(
        "interval, value, expected",
        [
            (
                ResourceStatisticsInterval.day,
                datetime.date(2024, 12, 31),
                datetime.date(2025, 1, 1),
            ),
            (
                ResourceStatisticsInterval.month,
                datetime.date(2024, 11, 1),
                datetime.date(2024, 12, 1),
            ),
            (
                ResourceStatisticsInterval.month,
                datetime.date(2024, 12, 1),
                datetime.date(2025, 1, 1),
            ),
            (
                ResourceStatisticsInterval.year,
                datetime.date(2024, 1, 1),
                datetime.date(2025, 1, 1),
            ),
        ],
    )
    def test_next_date(
        self,
        interval: ResourceStatisticsInterval,
        value: datetime.date,
        expected: datetime.date,
    ) -> None:
        assert interval.next_date(value) == expected


class TestResourceStatisticsSeries:
    def test_from_sorted_values__keeps_consecutive_intervals(self) -> None:
        first_date = datetime.date(2024, 1, 1)
        next_date = datetime.date(2024, 1, 2)

        series = ResourceStatisticsSeries.from_sorted_values(
            ResourceStatisticsInterval.day,
            (
                (first_date, 2),
                (next_date, 4),
            ),
            current_date=datetime.date(2026, 1, 1),
        )

        assert series == ResourceStatisticsSeries(first_date=first_date, values=(2, 4))

    @pytest.mark.parametrize(
        "interval, expected_date",
        [
            (ResourceStatisticsInterval.day, datetime.date(2024, 11, 23)),
            (ResourceStatisticsInterval.month, datetime.date(2024, 11, 1)),
            (ResourceStatisticsInterval.year, datetime.date(2024, 1, 1)),
        ],
    )
    def test_from_sorted_values__empty(
        self,
        interval: ResourceStatisticsInterval,
        expected_date: datetime.date,
    ) -> None:
        series = ResourceStatisticsSeries.from_sorted_values(
            interval,
            (),
            current_date=datetime.date(2024, 11, 23),
        )

        assert series == ResourceStatisticsSeries(first_date=expected_date, values=(0,))

    @pytest.mark.parametrize(
        "interval, first_date, last_date",
        [
            (ResourceStatisticsInterval.day, datetime.date(2024, 1, 1), datetime.date(2024, 1, 3)),
            (ResourceStatisticsInterval.month, datetime.date(2024, 11, 1), datetime.date(2025, 1, 1)),
            (ResourceStatisticsInterval.year, datetime.date(2023, 1, 1), datetime.date(2025, 1, 1)),
        ],
    )
    def test_from_sorted_values__fills_missing_intervals(
        self,
        interval: ResourceStatisticsInterval,
        first_date: datetime.date,
        last_date: datetime.date,
    ) -> None:
        series = ResourceStatisticsSeries.from_sorted_values(
            interval,
            (
                (first_date, 2),
                (last_date, 4),
            ),
            current_date=datetime.date(2026, 1, 1),
        )

        assert series == ResourceStatisticsSeries(first_date=first_date, values=(2, 0, 4))
