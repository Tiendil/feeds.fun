import datetime
import uuid

from ffun.benefits.entities import (
    BenefitEntitlementAction,
    BenefitPackage,
    BenefitPackageTemplate,
    BenefitParameterDefinition,
    BenefitParameterId,
    BenefitSourceId,
    BenefitSourceTransactionId,
    BenefitTransaction,
    BenefitTransactionCommand,
    ExternalTarget,
    NewTarget,
    OneTimePurchaseTarget,
    ParameterConstant,
    ParameterReference,
    SubscriptionTarget,
)
from ffun.core.entities import NonEmptyString
from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.domain import new_user_id
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    OneTimePurchaseId,
    ProviderObjectReference,
    ProviderStatus,
    SubscriptionId,
    UserId,
)
from ffun.entitlements.entities import EntitlementKindId, EntitlementValue
from ffun.one_time_purchases.domain import new_purchase_id
from ffun.subscriptions.domain import new_subscription_id
from ffun.subscriptions.entities import SubscriptionSnapshot, SubscriptionStatusId
from ffun.subscriptions.tests.make import make_provider_subscription_reference


def make_benefit_package(
    *,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    parameters: dict[BenefitParameterId, EntitlementValue] | None = None,
    entitlements: dict[EntitlementKindId, EntitlementValue] | None = None,
) -> BenefitPackage:
    if parameters is None:
        parameters = {}

    if entitlements is None:
        entitlements = {EntitlementKindId.day_tokens: 10}

    return BenefitPackage(
        id=benefit_id,
        parameters=parameters,
        entitlements=entitlements,
    )


def make_benefit_package_template(
    *,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    parameters: tuple[BenefitParameterDefinition, ...] = (),
    entitlements: dict[EntitlementKindId, ParameterConstant | ParameterReference] | None = None,
) -> BenefitPackageTemplate:
    if entitlements is None:
        entitlements = {EntitlementKindId.day_tokens: ParameterConstant(value=10)}

    return BenefitPackageTemplate(
        id=benefit_id,
        title=NonEmptyString("Test benefit"),
        description="Test benefit package template",
        parameters=parameters,
        entitlements=entitlements,
    )


def make_external_target(
    reference: ProviderObjectReference | None = None,
) -> ExternalTarget:
    reference = reference or make_provider_subscription_reference()
    return ExternalTarget(
        provider_id=reference.provider_id,
        provider_account_id=reference.provider_account_id,
        provider_object_id=reference.provider_object_id,
    )


def make_benefit_transaction(  # noqa: CFQ002
    *,
    transaction_id: BenefitTransactionId | None = None,
    source_id: BenefitSourceId = BenefitSourceId(17),
    source_transaction_id: BenefitSourceTransactionId | None = None,
    entitlement_action: BenefitEntitlementAction = BenefitEntitlementAction.grant,
    user_id: UserId | None = None,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    subscription_id: SubscriptionId | None = None,
    effective_at: datetime.datetime | None = None,
    period_starts_at: datetime.datetime | None = None,
    period_ends_at: datetime.datetime | None = None,
) -> BenefitTransaction:
    now = effective_at or datetime.datetime.now(tz=datetime.UTC)
    period_starts_at = period_starts_at or now - datetime.timedelta(days=1)
    period_ends_at = period_ends_at or now + datetime.timedelta(days=1)

    return BenefitTransaction(
        id=transaction_id or BenefitTransactionId(uuid.uuid4()),
        source_id=source_id,
        source_transaction_id=source_transaction_id or BenefitSourceTransactionId(uuid.uuid4()),
        entitlement_action=entitlement_action,
        user_id=user_id or new_user_id(),
        benefit_id=benefit_id,
        subscription_id=subscription_id or new_subscription_id(),
        effective_at=now,
        period_starts_at=period_starts_at,
        period_ends_at=period_ends_at,
    )


def make_one_time_purchase_benefit_transaction(  # noqa: CFQ002
    *,
    transaction_id: BenefitTransactionId | None = None,
    source_id: BenefitSourceId = BenefitSourceId(17),
    source_transaction_id: BenefitSourceTransactionId | None = None,
    entitlement_action: BenefitEntitlementAction = BenefitEntitlementAction.grant,
    user_id: UserId | None = None,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    one_time_purchase_id: OneTimePurchaseId | None = None,
    effective_at: datetime.datetime | None = None,
    period_starts_at: datetime.datetime | None = None,
    period_ends_at: datetime.datetime | None = None,
) -> BenefitTransaction:
    now = effective_at or datetime.datetime.now(tz=datetime.UTC)
    period_starts_at = period_starts_at or now
    period_ends_at = period_ends_at or LIFETIME_INTERVAL_END_MARKER

    return BenefitTransaction(
        id=transaction_id or BenefitTransactionId(uuid.uuid4()),
        source_id=source_id,
        source_transaction_id=source_transaction_id or BenefitSourceTransactionId(uuid.uuid4()),
        entitlement_action=entitlement_action,
        user_id=user_id or new_user_id(),
        benefit_id=benefit_id,
        one_time_purchase_id=one_time_purchase_id or new_purchase_id(),
        effective_at=now,
        period_starts_at=period_starts_at,
        period_ends_at=period_ends_at,
    )


def make_transaction_command(
    *,
    source_id: BenefitSourceId = BenefitSourceId(17),
    source_transaction_id: BenefitSourceTransactionId | None = None,
    target: SubscriptionTarget | None = None,
    effective_at: datetime.datetime | None = None,
) -> BenefitTransactionCommand[SubscriptionId]:
    return BenefitTransactionCommand[SubscriptionId](
        source_id=source_id,
        source_transaction_id=source_transaction_id or BenefitSourceTransactionId(uuid.uuid4()),
        target=target or NewTarget(),
        effective_at=effective_at or datetime.datetime.now(tz=datetime.UTC),
    )


def make_one_time_purchase_transaction_command(
    *,
    source_id: BenefitSourceId = BenefitSourceId(17),
    source_transaction_id: BenefitSourceTransactionId | None = None,
    target: OneTimePurchaseTarget | None = None,
    effective_at: datetime.datetime | None = None,
) -> BenefitTransactionCommand[OneTimePurchaseId]:
    return BenefitTransactionCommand[OneTimePurchaseId](
        source_id=source_id,
        source_transaction_id=source_transaction_id or BenefitSourceTransactionId(uuid.uuid4()),
        target=target or NewTarget(),
        effective_at=effective_at or datetime.datetime.now(tz=datetime.UTC),
    )


def make_subscription_snapshot(  # noqa: CFQ002
    *,
    user_id: UserId | None = None,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    status: SubscriptionStatusId = SubscriptionStatusId.active,
    provider_status: str = "active",
    started_at: datetime.datetime | None = None,
    period_starts_at: datetime.datetime | None = None,
    period_ends_at: datetime.datetime | None = None,
    expected_renewal_at: datetime.datetime | None = None,
    ends_at: datetime.datetime | None = None,
    provider_updated_at: datetime.datetime | None = None,
) -> SubscriptionSnapshot:
    now = datetime.datetime.now(tz=datetime.UTC)
    return SubscriptionSnapshot(
        user_id=user_id or new_user_id(),
        benefit_id=benefit_id,
        status=status,
        provider_status=ProviderStatus(provider_status),
        started_at=started_at or now - datetime.timedelta(days=30),
        period_starts_at=period_starts_at or now - datetime.timedelta(days=1),
        period_ends_at=period_ends_at or now + datetime.timedelta(days=30),
        expected_renewal_at=expected_renewal_at,
        ends_at=ends_at,
        provider_updated_at=provider_updated_at or now,
    )
