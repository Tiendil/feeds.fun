import datetime
import uuid

from ffun.benefits.entities import (
    BenefitPackage,
    BenefitSourceId,
    BenefitSourceTransactionId,
    BenefitTransaction,
    BenefitTransactionCommand,
    BenefitTransactionKind,
    ExternalSubscriptionTarget,
    GrantBenefitEffect,
    NewSubscriptionTarget,
    ProviderAccountId,
    ProviderId,
    ProviderSubscriptionId,
    ProviderSubscriptionReference,
    RevokeBenefitEffect,
    SubscriptionTarget,
)
from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitId, BenefitTransactionId, UserId
from ffun.entitlements.entities import EntitlementGuarantee, EntitlementKindId
from ffun.subscriptions.domain import new_subscription_id
from ffun.subscriptions.entities import (
    ProviderStatus,
    SubscriptionId,
    SubscriptionSnapshot,
    SubscriptionStatusId,
)


def make_benefit_package(
    *,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    title: str = "Test benefit",
    description: str = "Benefit package used by tests",
    entitlements: tuple[EntitlementGuarantee, ...] | None = None,
) -> BenefitPackage:
    if entitlements is None:
        entitlements = (EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),)

    return BenefitPackage(
        id=benefit_id,
        title=title,
        description=description,
        entitlements=entitlements,
    )


def make_provider_subscription_reference(
    *,
    provider_id: str = "test-provider",
    provider_account_id: str = "test-account",
    provider_subscription_id: str | None = None,
) -> ProviderSubscriptionReference:
    return ProviderSubscriptionReference(
        provider_id=ProviderId(provider_id),
        provider_account_id=ProviderAccountId(provider_account_id),
        provider_subscription_id=ProviderSubscriptionId(provider_subscription_id or str(uuid.uuid4())),
    )


def make_external_subscription_target(
    reference: ProviderSubscriptionReference | None = None,
) -> ExternalSubscriptionTarget:
    reference = reference or make_provider_subscription_reference()
    return ExternalSubscriptionTarget(**reference.model_dump())


def make_grant_effect(
    *,
    starts_at: datetime.datetime | None = None,
    expires_at: datetime.datetime | None = None,
) -> GrantBenefitEffect:
    now = datetime.datetime.now(tz=datetime.UTC)
    return GrantBenefitEffect(
        starts_at=starts_at or now - datetime.timedelta(days=1),
        expires_at=expires_at or now + datetime.timedelta(days=1),
    )


def make_revoke_effect(
    *,
    revokes_transaction_id: BenefitTransactionId | None = None,
) -> RevokeBenefitEffect:
    return RevokeBenefitEffect(
        revokes_transaction_id=revokes_transaction_id or BenefitTransactionId(uuid.uuid4())
    )


def make_benefit_transaction(  # noqa: CFQ002
    *,
    transaction_id: BenefitTransactionId | None = None,
    source_id: BenefitSourceId = BenefitSourceId(17),
    source_transaction_id: BenefitSourceTransactionId | None = None,
    kind: BenefitTransactionKind = BenefitTransactionKind.grant,
    user_id: UserId | None = None,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    subscription_id: SubscriptionId | None = None,
    effective_at: datetime.datetime | None = None,
    starts_at: datetime.datetime | None = None,
    expires_at: datetime.datetime | None = None,
    revokes_transaction_id: BenefitTransactionId | None = None,
) -> BenefitTransaction:
    now = effective_at or datetime.datetime.now(tz=datetime.UTC)

    if kind == BenefitTransactionKind.grant:
        starts_at = starts_at or now - datetime.timedelta(days=1)
        expires_at = expires_at or now + datetime.timedelta(days=1)
    else:
        revokes_transaction_id = revokes_transaction_id or BenefitTransactionId(uuid.uuid4())

    return BenefitTransaction(
        id=transaction_id or BenefitTransactionId(uuid.uuid4()),
        source_id=source_id,
        source_transaction_id=source_transaction_id or BenefitSourceTransactionId(uuid.uuid4()),
        kind=kind,
        user_id=user_id or new_user_id(),
        benefit_id=benefit_id,
        subscription_id=subscription_id or new_subscription_id(),
        effective_at=now,
        starts_at=starts_at,
        expires_at=expires_at,
        revokes_transaction_id=revokes_transaction_id,
    )


def make_benefit_command(
    *,
    source_id: BenefitSourceId = BenefitSourceId(17),
    source_transaction_id: BenefitSourceTransactionId | None = None,
    subscription_target: SubscriptionTarget | None = None,
    effect: GrantBenefitEffect | RevokeBenefitEffect | None = None,
    effective_at: datetime.datetime | None = None,
) -> BenefitTransactionCommand:
    return BenefitTransactionCommand(
        source_id=source_id,
        source_transaction_id=source_transaction_id or BenefitSourceTransactionId(uuid.uuid4()),
        subscription_target=subscription_target or NewSubscriptionTarget(),
        effect=effect or make_grant_effect(),
        effective_at=effective_at or datetime.datetime.now(tz=datetime.UTC),
    )


def make_subscription_snapshot(
    *,
    user_id: UserId | None = None,
    benefit_id: BenefitId = BenefitId("test-benefit"),
    status: SubscriptionStatusId = SubscriptionStatusId.active,
    provider_status: str = "active",
    started_at: datetime.datetime | None = None,
    renews_at: datetime.datetime | None = None,
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
        renews_at=renews_at,
        ends_at=ends_at,
        provider_updated_at=provider_updated_at or now,
    )
