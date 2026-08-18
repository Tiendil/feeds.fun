import datetime
import enum
import uuid
from typing import NewType, cast

import pydantic

from ffun.core import utils
from ffun.core.entities import BaseEntity, NonEmptyString
from ffun.domain.entities import BenefitId, BenefitTransactionId, UserId

SubscriptionId = NewType("SubscriptionId", uuid.UUID)


class ProviderStatus(NonEmptyString):
    __slots__ = ()


class SubscriptionStatusId(enum.IntEnum):
    pending = 1
    trialing = 2
    active = 3
    past_due = 4
    paused = 5
    ended = 6


class SaveSubscriptionOutcome(enum.IntEnum):
    created = 1
    updated = 2
    # A skipped save may still advance provider_updated_at when the business state is unchanged.
    skipped = 3


class SubscriptionSnapshot(BaseEntity):
    user_id: UserId
    benefit_id: BenefitId
    status: SubscriptionStatusId
    provider_status: ProviderStatus
    started_at: datetime.datetime
    renews_at: datetime.datetime | None = None
    ends_at: datetime.datetime | None = None
    provider_updated_at: datetime.datetime

    @pydantic.model_validator(mode="after")
    def validate_timestamps(self) -> "SubscriptionSnapshot":
        for field_name, timestamp in (
            ("started_at", self.started_at),
            ("renews_at", self.renews_at),
            ("ends_at", self.ends_at),
            ("provider_updated_at", self.provider_updated_at),
        ):
            if timestamp is not None and not utils.has_timezone(timestamp):
                raise ValueError(f"Subscription timestamp {field_name} must have a UTC offset")

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
            renews_at=self.renews_at,
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
    outcome: SaveSubscriptionOutcome
    current: Subscription
    previous: Subscription | None = None
