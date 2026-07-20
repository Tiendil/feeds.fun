import datetime
import enum
from typing import NewType, TypeAlias

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import UserId

EntitlementSourceId = NewType("EntitlementSourceId", str)
EffectiveEntitlementState: TypeAlias = tuple[bool, int | None]


class EntitlementKindId(enum.IntEnum):
    day_tokens = 1
    month_tokens = 2


class MergePolicy(enum.StrEnum):
    max = "max"
    min = "min"
    sum = "sum"


class EntitlementKind(BaseEntity):
    id: EntitlementKindId
    merge_policy: MergePolicy


ENTITLEMENT_KINDS: tuple[EntitlementKind, ...] = (
    EntitlementKind(id=EntitlementKindId.day_tokens, merge_policy=MergePolicy.max),
    EntitlementKind(id=EntitlementKindId.month_tokens, merge_policy=MergePolicy.max),
)


class SourceEntitlement(BaseEntity):
    source: EntitlementSourceId
    user_id: UserId
    kind_id: EntitlementKindId
    granted: bool = pydantic.Field(strict=True)
    value: int | None = pydantic.Field(strict=True)
    starts_at: datetime.datetime
    expires_at: datetime.datetime

    @pydantic.model_validator(mode="after")
    def validate_state(self) -> "SourceEntitlement":  # noqa: CCR001
        if self.granted and self.value is None:
            raise ValueError("A granted entitlement must have an integer value")

        if not self.granted and self.value is not None:
            raise ValueError("A revoked entitlement must not have a value")

        if self.starts_at.tzinfo is None or self.starts_at.utcoffset() is None:
            raise ValueError("Entitlement activation timestamp must have a UTC offset")

        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("Entitlement expiration timestamp must have a UTC offset")

        if self.starts_at >= self.expires_at:
            raise ValueError("Entitlement activation timestamp must be earlier than expiration")

        return self

    def to_revoked(
        self,
        *,
        starts_at: datetime.datetime,
        expires_at: datetime.datetime,
    ) -> "SourceEntitlement":
        return self.replace(
            granted=False,
            value=None,
            starts_at=starts_at,
            expires_at=expires_at,
        )

    def to_granted(
        self,
        *,
        value: int,
        starts_at: datetime.datetime,
        expires_at: datetime.datetime,
    ) -> "SourceEntitlement":
        return self.replace(
            granted=True,
            value=value,
            starts_at=starts_at,
            expires_at=expires_at,
        )


class EffectiveEntitlementInterval(BaseEntity):
    user_id: UserId
    kind_id: EntitlementKindId
    value: int
    starts_at: datetime.datetime
    expires_at: datetime.datetime
