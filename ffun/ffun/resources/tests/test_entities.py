import datetime

import pytest

from ffun.domain.entities import UserId
from ffun.resources.entities import ResourceIdentity, ResourceKey, ResourceStatisticsInterval, ResourceStatisticsSeries


class TestResourceIdentity:
    def test_single__constructs_identity(self, internal_user_id: UserId) -> None:
        resource_key = ResourceKey(
            kind=1,
            interval_started_at=datetime.datetime.now(tz=datetime.UTC),
        )

        assert ResourceIdentity.single(internal_user_id, resource_key) == [
            ResourceIdentity(
                user_id=internal_user_id,
                kind=resource_key.kind,
                interval_started_at=resource_key.interval_started_at,
            )
        ]

    def test_for_user__constructs_identities(self, internal_user_id: UserId) -> None:
        interval_started_at = datetime.datetime.now(tz=datetime.UTC)
        resource_keys = [
            ResourceKey(kind=1, interval_started_at=interval_started_at),
            ResourceKey(kind=2, interval_started_at=interval_started_at + datetime.timedelta(days=1)),
        ]

        assert ResourceIdentity.for_user(internal_user_id, resource_keys) == [
            ResourceIdentity(
                user_id=internal_user_id,
                kind=resource_key.kind,
                interval_started_at=resource_key.interval_started_at,
            )
            for resource_key in resource_keys
        ]

    def test_for_user__empty_resource_keys(self, internal_user_id: UserId) -> None:
        assert ResourceIdentity.for_user(internal_user_id, []) == []

    def test_for_resource__constructs_identities(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
    ) -> None:
        resource_key = ResourceKey(
            kind=1,
            interval_started_at=datetime.datetime.now(tz=datetime.UTC),
        )
        user_ids = [internal_user_id, another_internal_user_id]

        assert ResourceIdentity.for_resource(user_ids, resource_key) == [
            ResourceIdentity(
                user_id=user_id,
                kind=resource_key.kind,
                interval_started_at=resource_key.interval_started_at,
            )
            for user_id in user_ids
        ]

    def test_for_resource__empty_user_ids(self) -> None:
        resource_key = ResourceKey(
            kind=1,
            interval_started_at=datetime.datetime.now(tz=datetime.UTC),
        )

        assert ResourceIdentity.for_resource([], resource_key) == []

    def test_cartesian_product__constructs_identities(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
    ) -> None:
        interval_started_at = datetime.datetime.now(tz=datetime.UTC)
        user_ids = [internal_user_id, another_internal_user_id]
        resource_keys = [
            ResourceKey(kind=1, interval_started_at=interval_started_at),
            ResourceKey(kind=2, interval_started_at=interval_started_at + datetime.timedelta(days=1)),
        ]

        assert ResourceIdentity.cartesian_product(user_ids, iter(resource_keys)) == [
            ResourceIdentity(
                user_id=user_id,
                kind=resource_key.kind,
                interval_started_at=resource_key.interval_started_at,
            )
            for user_id in user_ids
            for resource_key in resource_keys
        ]

    def test_cartesian_product__empty_user_ids(self) -> None:
        resource_key = ResourceKey(
            kind=1,
            interval_started_at=datetime.datetime.now(tz=datetime.UTC),
        )

        assert ResourceIdentity.cartesian_product([], [resource_key]) == []

    def test_cartesian_product__empty_resource_keys(self, internal_user_id: UserId) -> None:
        assert ResourceIdentity.cartesian_product([internal_user_id], []) == []


class TestResourceStatisticsInterval:
    @pytest.mark.parametrize(
        "interval, expected",
        [
            (ResourceStatisticsInterval.day, datetime.date(2024, 11, 23)),
            (ResourceStatisticsInterval.month, datetime.date(2024, 11, 1)),
            (ResourceStatisticsInterval.year, datetime.date(2024, 1, 1)),
        ],
    )
    def test_start_date__normalizes_date(
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
    def test_next_date__advances_interval(
        self,
        interval: ResourceStatisticsInterval,
        value: datetime.date,
        expected: datetime.date,
    ) -> None:
        assert interval.next_date(value) == expected


class TestResourceStatisticsSeries:
    def test_from_sorted_values__singleton(self) -> None:
        first_date = datetime.date(2024, 1, 1)

        series = ResourceStatisticsSeries.from_sorted_values(
            ResourceStatisticsInterval.day,
            ((first_date, 2),),
            current_date=datetime.date(2026, 1, 1),
        )

        assert series == ResourceStatisticsSeries(first_date=first_date, values=(2,))

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
