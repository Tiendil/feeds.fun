import datetime
import enum
import uuid
from typing import Annotated, Literal, NewType, TypeAlias

import pydantic

from ffun.core import utils
from ffun.core.entities import BaseEntity, NonEmptyString
from ffun.domain.entities import BenefitId, BenefitTransactionId, SubscriptionId, UserId
from ffun.entitlements.entities import EntitlementGuarantee
from ffun.subscriptions.entities import (
    ProviderAccountId,
    ProviderId,
    ProviderSubscriptionId,
    ProviderSubscriptionReference,
)

BenefitSourceId = NewType("BenefitSourceId", int)
BenefitSourceTransactionId = NewType("BenefitSourceTransactionId", uuid.UUID)


class BenefitEntitlementAction(enum.IntEnum):
    grant = 1
    revoke = 2


class BenefitPackage(BaseEntity):
    id: BenefitId
    title: NonEmptyString
    description: str
    entitlements: tuple[EntitlementGuarantee, ...] = ()

    @pydantic.model_validator(mode="after")
    def entitlement_kinds_must_be_unique(self) -> "BenefitPackage":
        kind_ids = [entitlement.kind_id for entitlement in self.entitlements]

        if len(kind_ids) != len(set(kind_ids)):
            raise ValueError("Benefit package entitlement kinds must be unique")

        return self


class InternalSubscriptionTarget(BaseEntity):
    kind: Literal["internal"] = "internal"
    subscription_id: SubscriptionId

    @property
    def provider_reference(self) -> None:
        return None


class ExternalSubscriptionTarget(BaseEntity):
    kind: Literal["external"] = "external"
    provider_id: ProviderId
    provider_account_id: ProviderAccountId
    provider_subscription_id: ProviderSubscriptionId

    @property
    def provider_reference(self) -> ProviderSubscriptionReference:
        return ProviderSubscriptionReference(
            provider_id=self.provider_id,
            provider_account_id=self.provider_account_id,
            provider_subscription_id=self.provider_subscription_id,
        )

    @property
    def identity(self) -> tuple[ProviderId, ProviderAccountId, ProviderSubscriptionId]:
        return (
            self.provider_id,
            self.provider_account_id,
            self.provider_subscription_id,
        )


class NewSubscriptionTarget(BaseEntity):
    kind: Literal["new"] = "new"

    @property
    def provider_reference(self) -> None:
        return None


SubscriptionTarget: TypeAlias = Annotated[
    InternalSubscriptionTarget | ExternalSubscriptionTarget | NewSubscriptionTarget,
    pydantic.Field(discriminator="kind"),
]


class BenefitTransactionCommand(BaseEntity):
    source_id: BenefitSourceId
    source_transaction_id: BenefitSourceTransactionId
    subscription_target: SubscriptionTarget
    effective_at: datetime.datetime

    @property
    def source_identity(
        self,
    ) -> tuple[BenefitSourceId, BenefitSourceTransactionId]:
        return self.source_id, self.source_transaction_id

    @pydantic.field_validator("effective_at")
    @classmethod
    def effective_at_must_have_timezone(cls, timestamp: datetime.datetime) -> datetime.datetime:
        if not utils.has_timezone(timestamp):
            raise ValueError("Benefit transaction effective timestamp must have a UTC offset")

        return timestamp


class BenefitTransaction(BaseEntity):
    id: BenefitTransactionId
    source_id: BenefitSourceId
    source_transaction_id: BenefitSourceTransactionId
    entitlement_action: BenefitEntitlementAction
    user_id: UserId
    benefit_id: BenefitId
    subscription_id: SubscriptionId
    effective_at: datetime.datetime
    period_starts_at: datetime.datetime
    period_ends_at: datetime.datetime

    @property
    def source_identity(
        self,
    ) -> tuple[BenefitSourceId, BenefitSourceTransactionId]:
        return self.source_id, self.source_transaction_id

    @pydantic.field_validator("effective_at", "period_starts_at", "period_ends_at")
    @classmethod
    def timestamp_must_have_timezone(
        cls,
        timestamp: datetime.datetime,
        info: pydantic.ValidationInfo,
    ) -> datetime.datetime:
        if not utils.has_timezone(timestamp):
            raise ValueError(f"Benefit transaction timestamp {info.field_name} must have a UTC offset")

        return timestamp

    @pydantic.model_validator(mode="after")
    def validate_period_order(self) -> "BenefitTransaction":
        if self.period_starts_at >= self.period_ends_at:
            raise ValueError("Benefit transaction period start must be earlier than period end")

        return self


class BenefitTransactionApplicationResult(BaseEntity):
    transaction_id: BenefitTransactionId
    transaction_created: bool
    subscription_id: SubscriptionId
