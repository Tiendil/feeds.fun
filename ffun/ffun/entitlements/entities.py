import datetime
import enum
from typing import Annotated, TypeAlias

import pydantic

from ffun.core import utils
from ffun.core.entities import BaseEntity, NonEmptyString
from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.entities import BenefitTransactionId, SubscriptionId, UserId


class EntitlementSourceId(NonEmptyString):
    __slots__ = ()


EffectiveEntitlementState: TypeAlias = tuple[bool, int | None]

MIN_ENTITLEMENT_VALUE = 1
MAX_ENTITLEMENT_VALUE = 2**63 - 1

EntitlementValue: TypeAlias = Annotated[
    int,
    pydantic.Field(strict=True, ge=MIN_ENTITLEMENT_VALUE, le=MAX_ENTITLEMENT_VALUE),
]


class EntitlementKindId(enum.IntEnum):
    day_tokens = 1
    month_tokens = 2
    lifetime_tokens = 3


class MergePolicy(enum.StrEnum):
    max = "max"
    min = "min"
    sum = "sum"


class EntitlementKind(BaseEntity):
    id: EntitlementKindId
    merge_policy: MergePolicy
    is_lifetime: bool
    minimum_value: EntitlementValue = MIN_ENTITLEMENT_VALUE
    maximum_value: EntitlementValue = MAX_ENTITLEMENT_VALUE

    @pydantic.model_validator(mode="after")
    def validate_value_bounds(self) -> "EntitlementKind":
        if self.minimum_value > self.maximum_value:
            raise ValueError("Entitlement kind minimum value must not exceed maximum value")

        return self

    def validate_value(self, value: EntitlementValue) -> None:
        if not self.minimum_value <= value <= self.maximum_value:
            raise ValueError("Entitlement value must be within entitlement kind bounds")


class EntitlementGuarantee(BaseEntity):
    kind_id: EntitlementKindId
    value: EntitlementValue


ENTITLEMENT_KINDS: tuple[EntitlementKind, ...] = (
    EntitlementKind(id=EntitlementKindId.day_tokens, merge_policy=MergePolicy.max, is_lifetime=False),
    EntitlementKind(id=EntitlementKindId.month_tokens, merge_policy=MergePolicy.max, is_lifetime=False),
    EntitlementKind(id=EntitlementKindId.lifetime_tokens, merge_policy=MergePolicy.sum, is_lifetime=True),
)


class SourceEntitlement(BaseEntity):
    source_id: EntitlementSourceId
    grant_transaction_id: BenefitTransactionId
    user_id: UserId
    subscription_id: SubscriptionId | None = None
    kind_id: EntitlementKindId
    value: EntitlementValue
    starts_at: datetime.datetime
    expires_at: datetime.datetime
    revoked_at: datetime.datetime | None = None
    revoked_by_transaction_id: BenefitTransactionId | None = None

    @pydantic.model_validator(mode="after")
    def validate_state(self) -> "SourceEntitlement":  # noqa: CCR001
        if not utils.has_timezone(self.starts_at):
            raise ValueError("Entitlement activation timestamp must have a UTC offset")

        if not utils.has_timezone(self.expires_at):
            raise ValueError("Entitlement expiration timestamp must have a UTC offset")

        if self.starts_at >= self.expires_at:
            raise ValueError("Entitlement activation timestamp must be earlier than expiration")

        if self.revoked_at is not None and not utils.has_timezone(self.revoked_at):
            raise ValueError("Entitlement revocation timestamp must have a UTC offset")

        return self

    @pydantic.model_validator(mode="after")
    def validate_revocation_reference(self) -> "SourceEntitlement":
        if (self.revoked_at is None) != (self.revoked_by_transaction_id is None):
            raise ValueError("Entitlement revocation time and transaction must be defined together")

        return self

    @property
    def granted(self) -> bool:
        return self.revoked_at is None

    def validate_grant(self, kind: EntitlementKind) -> None:
        if self.kind_id != kind.id:
            raise ValueError("Source entitlement kind must match entitlement kind")

        kind.validate_value(self.value)

        if not self.granted:
            raise ValueError("A source entitlement grant must not be revoked")

        if kind.is_lifetime and self.expires_at != LIFETIME_INTERVAL_END_MARKER:
            raise ValueError("A lifetime entitlement must use the stable lifetime expiration timestamp")

        if not kind.is_lifetime and self.expires_at == LIFETIME_INTERVAL_END_MARKER:
            raise ValueError("A non-lifetime entitlement must use a source-supplied expiration timestamp")

    def has_same_grant_as(self, other: "SourceEntitlement") -> bool:
        return (
            self.source_id == other.source_id
            and self.grant_transaction_id == other.grant_transaction_id
            and self.user_id == other.user_id
            and self.subscription_id == other.subscription_id
            and self.kind_id == other.kind_id
            and self.value == other.value
            and self.starts_at == other.starts_at
            and self.expires_at == other.expires_at
        )


class EffectiveEntitlementInterval(BaseEntity):
    user_id: UserId
    kind_id: EntitlementKindId
    value: EntitlementValue
    starts_at: datetime.datetime
    expires_at: datetime.datetime

    @pydantic.model_validator(mode="after")
    def validate_interval(self) -> "EffectiveEntitlementInterval":
        if not utils.has_timezone(self.starts_at):
            raise ValueError("Effective entitlement activation timestamp must have a UTC offset")

        if not utils.has_timezone(self.expires_at):
            raise ValueError("Effective entitlement expiration timestamp must have a UTC offset")

        if self.starts_at >= self.expires_at:
            raise ValueError("Effective entitlement activation timestamp must be earlier than expiration")

        return self


class SourceEntitlementChange(BaseEntity):
    changed: bool
    effective_state: EffectiveEntitlementState
    effective_intervals: list[EffectiveEntitlementInterval]
    source_state: SourceEntitlement
