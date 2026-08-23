import datetime
import enum
import uuid
from collections.abc import Mapping
from typing import Annotated, Generic, Literal, NewType, TypeAlias, TypeVar, cast

import pydantic

from ffun.benefits import errors
from ffun.core import utils
from ffun.core.entities import BaseEntity, NonEmptyString
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    OneTimePurchaseId,
    ProviderAccountId,
    ProviderId,
    ProviderObjectId,
    ProviderObjectReference,
    SubscriptionId,
    UserId,
)
from ffun.entitlements import entities as entitlement_entities
from ffun.entitlements.entities import EntitlementGuarantee, EntitlementKindId, EntitlementValue

BenefitSourceId = NewType("BenefitSourceId", int)
BenefitSourceTransactionId = NewType("BenefitSourceTransactionId", uuid.UUID)


class BenefitParameterId(NonEmptyString):
    __slots__ = ()


BenefitParameters: TypeAlias = dict[BenefitParameterId, EntitlementValue]


class BenefitEntitlementAction(enum.IntEnum):
    grant = 1
    revoke = 2


class BenefitParameterDefinition(BaseEntity):
    id: BenefitParameterId
    minimum: EntitlementValue
    maximum: EntitlementValue

    @pydantic.model_validator(mode="after")
    def validate_bounds(self) -> "BenefitParameterDefinition":
        if self.minimum > self.maximum:
            raise ValueError("Benefit parameter minimum must not exceed maximum")

        return self

    def validate_value(self, value: object) -> None:
        if type(value) is not int:
            raise errors.InvalidBenefitParameter(
                parameter_id=self.id,
                value_type=type(value).__name__,
            )

        if not self.minimum <= value <= self.maximum:
            raise errors.InvalidBenefitParameter(
                parameter_id=self.id,
                value=value,
                minimum=self.minimum,
                maximum=self.maximum,
            )


class ParameterConstant(BaseEntity):
    value: EntitlementValue

    def materialize(self, parameters: BenefitParameters) -> EntitlementValue:
        return self.value


class ParameterReference(BaseEntity):
    parameter_id: BenefitParameterId

    def materialize(self, parameters: BenefitParameters) -> EntitlementValue:
        try:
            return parameters[self.parameter_id]
        except KeyError as error:
            raise errors.MissingBenefitParameter(parameter_id=self.parameter_id) from error


class BenefitPackage(BaseEntity):
    id: BenefitId
    parameters: BenefitParameters = pydantic.Field(default_factory=dict)
    entitlements: dict[EntitlementKindId, EntitlementValue] = pydantic.Field(min_length=1)

    @property
    def guarantees(self) -> tuple[EntitlementGuarantee, ...]:
        return tuple(
            EntitlementGuarantee(kind_id=kind_id, value=value) for kind_id, value in sorted(self.entitlements.items())
        )


class BenefitPackageTemplate(BaseEntity):
    id: BenefitId
    title: NonEmptyString
    description: str
    parameters: tuple[BenefitParameterDefinition, ...] = ()
    entitlements: dict[EntitlementKindId, ParameterConstant | ParameterReference] = pydantic.Field(min_length=1)

    @pydantic.model_validator(mode="after")
    def parameter_ids_must_be_unique(self) -> "BenefitPackageTemplate":
        parameter_ids = [definition.id for definition in self.parameters]

        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError(f"Benefit package template {self.id} parameter ids must be unique")

        return self

    @pydantic.model_validator(mode="after")
    def parameter_references_must_be_valid(self) -> "BenefitPackageTemplate":
        declared_parameter_ids = {definition.id for definition in self.parameters}
        referenced_parameter_ids = {
            value_template.parameter_id
            for value_template in self.entitlements.values()
            if isinstance(value_template, ParameterReference)
        }
        undeclared_parameter_ids = referenced_parameter_ids - declared_parameter_ids

        if undeclared_parameter_ids:
            parameter_list = ", ".join(sorted(undeclared_parameter_ids))
            raise ValueError(f"Benefit package template {self.id} references undeclared parameters: {parameter_list}")

        unused_parameter_ids = declared_parameter_ids - referenced_parameter_ids

        if unused_parameter_ids:
            parameter_list = ", ".join(sorted(unused_parameter_ids))
            raise ValueError(f"Benefit package template {self.id} has unused parameters: {parameter_list}")

        return self

    @pydantic.model_validator(mode="after")
    def constant_values_must_match_entitlement_kinds(self) -> "BenefitPackageTemplate":
        entitlement_kinds = {kind.id: kind for kind in entitlement_entities.ENTITLEMENT_KINDS}

        for kind_id, value_template in self.entitlements.items():
            if not isinstance(value_template, ParameterConstant):
                continue

            kind = entitlement_kinds[kind_id]

            try:
                kind.validate_value(value_template.value)
            except ValueError as error:
                raise ValueError(
                    f"Benefit package template {self.id} constant for {kind_id.name} "
                    "must be within entitlement kind bounds"
                ) from error

        return self

    @pydantic.model_validator(mode="after")
    def parameter_ranges_must_match_entitlement_kinds(self) -> "BenefitPackageTemplate":
        entitlement_kinds = {kind.id: kind for kind in entitlement_entities.ENTITLEMENT_KINDS}
        parameters = {definition.id: definition for definition in self.parameters}

        for kind_id, value_template in self.entitlements.items():
            if not isinstance(value_template, ParameterReference):
                continue

            definition = parameters[value_template.parameter_id]
            kind = entitlement_kinds[kind_id]

            try:
                kind.validate_value(definition.minimum)
                kind.validate_value(definition.maximum)
            except ValueError as error:
                raise ValueError(
                    f"Benefit package template {self.id} parameter {definition.id} range for {kind_id.name} "
                    "must be within entitlement kind bounds"
                ) from error

        return self

    def materialize(self, parameters: Mapping[BenefitParameterId, object]) -> BenefitPackage:
        definitions = {definition.id: definition for definition in self.parameters}
        supplied_parameter_ids = set(parameters)
        missing_parameter_ids = set(definitions) - supplied_parameter_ids

        if missing_parameter_ids:
            raise errors.MissingBenefitParameter(parameter_id=min(missing_parameter_ids))

        unknown_parameter_ids = supplied_parameter_ids - set(definitions)

        if unknown_parameter_ids:
            raise errors.UnknownBenefitParameter(parameter_id=min(unknown_parameter_ids))

        normalized_parameters: BenefitParameters = {}

        for definition in self.parameters:
            value = parameters[definition.id]
            definition.validate_value(value)
            normalized_parameters[definition.id] = cast(EntitlementValue, value)

        materialized_entitlements = {
            kind_id: value_template.materialize(normalized_parameters)
            for kind_id, value_template in self.entitlements.items()
        }
        entitlement_kinds = {kind.id: kind for kind in entitlement_entities.ENTITLEMENT_KINDS}

        for kind_id, value in materialized_entitlements.items():
            kind = entitlement_kinds[kind_id]

            try:
                kind.validate_value(value)
            except ValueError as error:
                raise errors.InvalidBenefitEntitlement(
                    benefit_id=self.id,
                    entitlement_kind_id=int(kind_id),
                    value=value,
                    minimum=kind.minimum_value,
                    maximum=kind.maximum_value,
                ) from error

        return BenefitPackage(
            id=self.id,
            parameters=normalized_parameters,
            entitlements=materialized_entitlements,
        )


TargetIdT = TypeVar("TargetIdT", SubscriptionId, OneTimePurchaseId)


class InternalTarget(BaseEntity, Generic[TargetIdT]):
    kind: Literal["internal"] = "internal"
    internal_id: TargetIdT

    @property
    def provider_reference(self) -> None:
        return None


class ExternalTarget(BaseEntity):
    kind: Literal["external"] = "external"
    provider_id: ProviderId
    provider_account_id: ProviderAccountId
    provider_object_id: ProviderObjectId

    @property
    def provider_reference(self) -> ProviderObjectReference:
        return ProviderObjectReference(
            provider_id=self.provider_id,
            provider_account_id=self.provider_account_id,
            provider_object_id=self.provider_object_id,
        )

    @property
    def identity(self) -> tuple[ProviderId, ProviderAccountId, ProviderObjectId]:
        return (
            self.provider_id,
            self.provider_account_id,
            self.provider_object_id,
        )


class NewTarget(BaseEntity):
    kind: Literal["new"] = "new"

    @property
    def provider_reference(self) -> None:
        return None


SubscriptionTarget: TypeAlias = Annotated[
    InternalTarget[SubscriptionId] | ExternalTarget | NewTarget,
    pydantic.Field(discriminator="kind"),
]


OneTimePurchaseTarget: TypeAlias = Annotated[
    InternalTarget[OneTimePurchaseId] | ExternalTarget | NewTarget,
    pydantic.Field(discriminator="kind"),
]


class BenefitTransactionCommand(BaseEntity, Generic[TargetIdT]):
    source_id: BenefitSourceId
    source_transaction_id: BenefitSourceTransactionId
    target: Annotated[
        InternalTarget[TargetIdT] | ExternalTarget | NewTarget,
        pydantic.Field(discriminator="kind"),
    ]
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
    subscription_id: SubscriptionId | None = None
    one_time_purchase_id: OneTimePurchaseId | None = None
    effective_at: datetime.datetime
    period_starts_at: datetime.datetime
    period_ends_at: datetime.datetime

    @property
    def source_identity(
        self,
    ) -> tuple[BenefitSourceId, BenefitSourceTransactionId]:
        return self.source_id, self.source_transaction_id

    def get_subscription_id_or_raise(self) -> SubscriptionId:
        if self.subscription_id is None:
            raise errors.InvalidBenefitTransactionTarget(
                transaction_id=str(self.id),
                expected_target="subscription",
                actual_target="one_time_purchase",
            )

        return self.subscription_id

    def get_one_time_purchase_id_or_raise(self) -> OneTimePurchaseId:
        if self.one_time_purchase_id is None:
            raise errors.InvalidBenefitTransactionTarget(
                transaction_id=str(self.id),
                expected_target="one_time_purchase",
                actual_target="subscription",
            )

        return self.one_time_purchase_id

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

    @pydantic.model_validator(mode="after")
    def validate_target(self) -> "BenefitTransaction":
        if (self.subscription_id is None) == (self.one_time_purchase_id is None):
            raise ValueError("Benefit transaction must have exactly one target")

        return self


class BenefitTransactionApplicationResult(BaseEntity, Generic[TargetIdT]):
    transaction_id: BenefitTransactionId
    transaction_created: bool
    target_id: TargetIdT
