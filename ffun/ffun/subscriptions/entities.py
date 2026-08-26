import datetime
import enum
from typing import cast

import pydantic

from ffun.core import utils
from ffun.core.entities import BaseEntity
from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    ProviderStatus,
    PurchasedStateSaveOutcome,
    SubscriptionId,
    UserId,
)


class SubscriptionStatusId(enum.IntEnum):
    pending = 1
    trialing = 2
    active = 3
    past_due = 4
    paused = 5
    ended = 6

    @property
    def grants_benefits(self) -> bool:
        return self in _BENEFIT_GRANTING_STATUSES


_BENEFIT_GRANTING_STATUSES = frozenset(
    {
        SubscriptionStatusId.trialing,
        SubscriptionStatusId.active,
        SubscriptionStatusId.past_due,
    }
)


class SubscriptionSnapshot(BaseEntity):
    user_id: UserId
    benefit_id: BenefitId
    status: SubscriptionStatusId
    provider_status: ProviderStatus
    started_at: datetime.datetime
    period_starts_at: datetime.datetime
    period_ends_at: datetime.datetime
    expected_renewal_at: datetime.datetime | None = None
    ends_at: datetime.datetime | None = None
    provider_updated_at: datetime.datetime

    @pydantic.model_validator(mode="after")
    def validate_timestamp_timezones(self) -> "SubscriptionSnapshot":
        for field_name, timestamp in (
            ("started_at", self.started_at),
            ("period_starts_at", self.period_starts_at),
            ("period_ends_at", self.period_ends_at),
            ("expected_renewal_at", self.expected_renewal_at),
            ("ends_at", self.ends_at),
            ("provider_updated_at", self.provider_updated_at),
        ):
            if timestamp is not None and not utils.has_timezone(timestamp):
                raise ValueError(f"Subscription timestamp {field_name} must have a UTC offset")

        return self

    @pydantic.model_validator(mode="after")
    def validate_subscription_period(self) -> "SubscriptionSnapshot":
        if self.period_starts_at >= self.period_ends_at:
            raise ValueError("Subscription period start must be earlier than period end")

        if self.period_ends_at == LIFETIME_INTERVAL_END_MARKER:
            raise ValueError("Subscription period end must be finite")

        return self

    def business_state(self) -> dict[str, object]:
        fields = set(SubscriptionSnapshot.model_fields) - {"provider_updated_at"}
        return cast(dict[str, object], self.model_dump(include=fields))

    def has_same_business_state_as(self, other: "SubscriptionSnapshot") -> bool:
        return self.business_state() == other.business_state()

    def audit_state(self) -> dict[str, object]:
        return cast(
            dict[str, object],
            self.model_dump(mode="json", exclude={"user_id"}),
        )

    def with_identity(
        self,
        *,
        subscription_id: SubscriptionId,
        state_transaction_id: BenefitTransactionId,
    ) -> "Subscription":
        return Subscription(
            id=subscription_id,
            state_transaction_id=state_transaction_id,
            user_id=self.user_id,
            benefit_id=self.benefit_id,
            status=self.status,
            provider_status=self.provider_status,
            started_at=self.started_at,
            period_starts_at=self.period_starts_at,
            period_ends_at=self.period_ends_at,
            expected_renewal_at=self.expected_renewal_at,
            ends_at=self.ends_at,
            provider_updated_at=self.provider_updated_at,
        )


class Subscription(SubscriptionSnapshot):
    id: SubscriptionId
    state_transaction_id: BenefitTransactionId

    def audit_state(self) -> dict[str, object]:
        return cast(
            dict[str, object],
            self.model_dump(mode="json", exclude={"id", "state_transaction_id", "user_id"}),
        )

    def business_event_attributes(self) -> dict[str, object]:
        attributes = cast(
            dict[str, object],
            self.model_dump(mode="json", exclude={"id", "user_id"}),
        )
        attributes["subscription_id"] = str(self.id)
        return attributes


class SubscriptionSaveResult(BaseEntity):
    outcome: PurchasedStateSaveOutcome
    current: Subscription
    previous: Subscription | None = None
