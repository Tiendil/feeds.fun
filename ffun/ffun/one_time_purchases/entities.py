import datetime
import enum
from typing import cast

import pydantic

from ffun.core import utils
from ffun.core.entities import BaseEntity
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    OneTimePurchaseId,
    ProviderStatus,
    PurchasedStateSaveOutcome,
    UserId,
)


class PurchaseStatus(enum.IntEnum):
    pending = 1
    completed = 2
    refunded = 3
    reversed = 4
    disputed = 5

    @property
    def grants_benefits(self) -> bool:
        return self == PurchaseStatus.completed


class PurchaseSnapshot(BaseEntity):
    user_id: UserId
    benefit_id: BenefitId
    status: PurchaseStatus
    provider_status: ProviderStatus
    purchased_at: datetime.datetime
    provider_updated_at: datetime.datetime

    @pydantic.model_validator(mode="after")
    def validate_timestamp_timezones(self) -> "PurchaseSnapshot":
        for field_name, timestamp in (
            ("purchased_at", self.purchased_at),
            ("provider_updated_at", self.provider_updated_at),
        ):
            if not utils.has_timezone(timestamp):
                raise ValueError(f"Purchase timestamp {field_name} must have a UTC offset")

        return self

    def business_state(self) -> dict[str, object]:
        fields = set(PurchaseSnapshot.model_fields) - {"provider_updated_at"}
        return cast(dict[str, object], self.model_dump(include=fields))

    def has_same_business_state_as(self, other: "PurchaseSnapshot") -> bool:
        return self.business_state() == other.business_state()

    def audit_state(self) -> dict[str, object]:
        return cast(
            dict[str, object],
            self.model_dump(mode="json", exclude={"user_id"}),
        )

    def with_identity(
        self,
        *,
        one_time_purchase_id: OneTimePurchaseId,
        state_transaction_id: BenefitTransactionId,
    ) -> "Purchase":
        return Purchase(
            id=one_time_purchase_id,
            state_transaction_id=state_transaction_id,
            user_id=self.user_id,
            benefit_id=self.benefit_id,
            status=self.status,
            provider_status=self.provider_status,
            purchased_at=self.purchased_at,
            provider_updated_at=self.provider_updated_at,
        )


class Purchase(PurchaseSnapshot):
    id: OneTimePurchaseId
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
        attributes["one_time_purchase_id"] = str(self.id)
        return attributes


class PurchaseSaveResult(BaseEntity):
    outcome: PurchasedStateSaveOutcome
    current: Purchase
    previous: Purchase | None = None
