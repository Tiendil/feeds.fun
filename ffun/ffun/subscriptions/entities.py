import datetime
import enum
from typing import cast

import pydantic

from ffun.core import utils
from ffun.core.entities import BaseEntity, NonEmptyString
from ffun.domain.entities import UserId


class ProviderId(NonEmptyString):
    __slots__ = ()


class ProviderMerchantId(NonEmptyString):
    __slots__ = ()


class ProviderSubscriptionId(NonEmptyString):
    __slots__ = ()


class ProviderCustomerId(NonEmptyString):
    __slots__ = ()


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


class Subscription(BaseEntity):
    provider_id: ProviderId
    provider_merchant_id: ProviderMerchantId
    provider_subscription_id: ProviderSubscriptionId
    user_id: UserId
    provider_customer_id: ProviderCustomerId
    status: SubscriptionStatusId
    provider_status: ProviderStatus
    started_at: datetime.datetime
    renews_at: datetime.datetime | None = None
    ends_at: datetime.datetime | None = None
    provider_updated_at: datetime.datetime

    @pydantic.model_validator(mode="after")
    def validate_timestamps(self) -> "Subscription":
        for field_name, timestamp in (
            ("started_at", self.started_at),
            ("renews_at", self.renews_at),
            ("ends_at", self.ends_at),
            ("provider_updated_at", self.provider_updated_at),
        ):
            if timestamp is not None and not utils.has_timezone(timestamp):
                raise ValueError(f"Subscription timestamp {field_name} must have a UTC offset")

        return self

    def has_same_ownership_as(self, other: "Subscription") -> bool:
        return (
            self.provider_id == other.provider_id
            and self.provider_merchant_id == other.provider_merchant_id
            and self.provider_subscription_id == other.provider_subscription_id
            and self.user_id == other.user_id
            and (self.provider_customer_id == other.provider_customer_id)
        )

    def has_same_business_state_as(self, other: "Subscription") -> bool:
        return self.replace(provider_updated_at=other.provider_updated_at) == other

    def audit_state(self) -> dict[str, object]:
        return cast(
            dict[str, object],
            self.model_dump(
                mode="json",
                exclude={
                    "provider_id",
                    "provider_merchant_id",
                    "provider_subscription_id",
                    "user_id",
                    "provider_customer_id",
                },
            ),
        )

    def business_event_attributes(self) -> dict[str, object]:
        return cast(
            dict[str, object],
            self.model_dump(mode="json", exclude={"user_id"}),
        )
