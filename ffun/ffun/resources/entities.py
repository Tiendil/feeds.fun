import datetime
import enum
import uuid
from collections.abc import Iterable
from typing import NewType

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import UserId

ResourceKind = NewType("ResourceKind", int)


class ResourceKey(BaseEntity):
    kind: int
    interval_started_at: datetime.datetime


class ResourceIdentity(BaseEntity):
    user_id: UserId
    kind: int
    interval_started_at: datetime.datetime

    @staticmethod
    def single(user_id: UserId, resource_key: ResourceKey) -> list["ResourceIdentity"]:
        return [
            ResourceIdentity(
                user_id=user_id,
                kind=resource_key.kind,
                interval_started_at=resource_key.interval_started_at,
            )
        ]

    @staticmethod
    def for_user(user_id: UserId, resource_keys: Iterable[ResourceKey]) -> list["ResourceIdentity"]:
        return [
            ResourceIdentity(
                user_id=user_id,
                kind=resource_key.kind,
                interval_started_at=resource_key.interval_started_at,
            )
            for resource_key in resource_keys
        ]

    @staticmethod
    def for_resource(user_ids: Iterable[UserId], resource_key: ResourceKey) -> list["ResourceIdentity"]:
        return [
            ResourceIdentity(
                user_id=user_id,
                kind=resource_key.kind,
                interval_started_at=resource_key.interval_started_at,
            )
            for user_id in user_ids
        ]

    @staticmethod
    def cartesian_product(
        user_ids: Iterable[UserId], resource_keys: Iterable[ResourceKey]
    ) -> list["ResourceIdentity"]:
        resource_keys = list(resource_keys)

        return [
            ResourceIdentity(
                user_id=user_id,
                kind=resource_key.kind,
                interval_started_at=resource_key.interval_started_at,
            )
            for user_id in user_ids
            for resource_key in resource_keys
        ]


class ResourceReservationOption(BaseEntity):
    kind: int
    interval_started_at: datetime.datetime


class ResourceReservationSpecification(BaseEntity):
    user_id: UserId
    limits: tuple[int | None, ...]


class ResourceReservationLimit(BaseEntity):
    user_id: UserId
    limit: int


class ResourceReservation(BaseEntity):
    user_id: UserId
    kind: int
    interval_started_at: datetime.datetime
    amount: int


class Resource(pydantic.BaseModel):
    user_id: uuid.UUID
    kind: int
    interval_started_at: datetime.datetime

    used: int
    reserved: int

    @property
    def total(self) -> int:
        return self.used + self.reserved


class ResourceStatisticsInterval(enum.StrEnum):
    day = "day"
    month = "month"
    year = "year"

    def start_date(self, value: datetime.date) -> datetime.date:
        if self == ResourceStatisticsInterval.day:
            return value

        if self == ResourceStatisticsInterval.month:
            return datetime.date(value.year, value.month, 1)

        return datetime.date(value.year, 1, 1)

    def next_date(self, value: datetime.date) -> datetime.date:
        if self == ResourceStatisticsInterval.day:
            return value + datetime.timedelta(days=1)

        if self == ResourceStatisticsInterval.month:
            if value.month == 12:
                return datetime.date(value.year + 1, 1, 1)

            return datetime.date(value.year, value.month + 1, 1)

        return datetime.date(value.year + 1, 1, 1)


class ResourceStatisticsSeries(BaseEntity):
    first_date: datetime.date
    values: tuple[int, ...]

    @classmethod
    def from_sorted_values(
        cls,
        interval: ResourceStatisticsInterval,
        recorded_values: Iterable[tuple[datetime.date, int]],
        *,
        current_date: datetime.date,
    ) -> "ResourceStatisticsSeries":
        values_iterator = iter(recorded_values)

        try:
            first_date, first_value = next(values_iterator)
        except StopIteration:
            return cls(first_date=interval.start_date(current_date), values=(0,))

        values = [first_value]
        previous_date = first_date

        for current_date, current_value in values_iterator:
            missing_date = interval.next_date(previous_date)

            while missing_date < current_date:
                values.append(0)
                missing_date = interval.next_date(missing_date)

            values.append(current_value)
            previous_date = current_date

        return cls(first_date=first_date, values=tuple(values))
