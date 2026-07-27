import datetime
import uuid

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import UserId


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
