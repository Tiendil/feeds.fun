import datetime
from collections.abc import Callable
from typing import assert_never

from ffun.audit.entities import AuditEntityKind
from ffun.benefits import errors, operations
from ffun.benefits.entities import (
    BenefitPackage,
    BenefitTransaction,
    BenefitTransactionApplicationResult,
    BenefitTransactionCommand,
    BenefitTransactionKind,
    ExternalSubscriptionTarget,
    GrantBenefitEffect,
    InternalSubscriptionTarget,
    NewSubscriptionTarget,
    RevokeBenefitEffect,
    SubscriptionTarget,
    SubscriptionUpdateEffect,
)
from ffun.benefits.settings import settings
from ffun.core.postgresql import ExecuteType, run_in_transaction, transaction
from ffun.domain.entities import BenefitId, SerializedId
from ffun.entitlements import domain as entitlement_domain, errors as entitlement_errors
from ffun.entitlements.entities import EntitlementSourceId
from ffun.subscriptions import domain as subscription_domain
from ffun.subscriptions.entities import SubscriptionId, SubscriptionSnapshot

BENEFITS_ENTITLEMENT_SOURCE_ID = EntitlementSourceId("benefits")

get_benefit_transaction = run_in_transaction(operations.load_benefit_transaction)


def get_benefit(benefit_id: BenefitId) -> BenefitPackage:
    for package in settings.packages:
        if package.id == benefit_id:
            return package

    raise errors.UnknownBenefit(benefit_id=benefit_id)


async def _resolve_regular_subscription_target(
    execute: ExecuteType,
    target: SubscriptionTarget,
) -> tuple[SubscriptionId, ExternalSubscriptionTarget | None]:
    if isinstance(target, InternalSubscriptionTarget):
        return target.subscription_id, None

    if isinstance(target, ExternalSubscriptionTarget):
        reference = await operations.load_provider_subscription_reference(
            execute,
            provider_id=target.provider_id,
            provider_account_id=target.provider_account_id,
            provider_subscription_id=target.provider_subscription_id,
        )

        if reference is not None:
            return reference, None

        return subscription_domain.new_subscription_id(), target

    if isinstance(target, NewSubscriptionTarget):
        return subscription_domain.new_subscription_id(), None

    assert_never(target)


async def _load_grant_to_revoke(
    execute: ExecuteType,
    effect: RevokeBenefitEffect,
    subscription: SubscriptionSnapshot,
) -> BenefitTransaction:
    grant_transaction = await operations.load_benefit_transaction(
        execute,
        effect.revokes_transaction_id,
    )

    if grant_transaction is None:
        raise errors.BenefitTransactionNotFound(transaction_id=str(effect.revokes_transaction_id))

    if grant_transaction.kind != BenefitTransactionKind.grant:
        raise errors.InvalidBenefitRevocation(
            transaction_id=str(grant_transaction.id),
            reason="Only a benefit grant transaction can be revoked",
        )

    if grant_transaction.user_id != subscription.user_id:
        raise errors.InvalidBenefitRevocation(
            transaction_id=str(grant_transaction.id),
            reason="The grant to revoke belongs to another subscription",
        )

    return grant_transaction


async def _resolve_revoke_subscription_target(
    execute: ExecuteType,
    target: SubscriptionTarget,
    grant_transaction: BenefitTransaction,
) -> tuple[SubscriptionId, ExternalSubscriptionTarget | None]:
    if isinstance(target, InternalSubscriptionTarget):
        subscription_id = target.subscription_id
        provider_reference = None

    elif isinstance(target, ExternalSubscriptionTarget):
        reference = await operations.load_provider_subscription_reference(
            execute,
            provider_id=target.provider_id,
            provider_account_id=target.provider_account_id,
            provider_subscription_id=target.provider_subscription_id,
        )

        if reference is None:
            subscription_id = grant_transaction.subscription_id
            provider_reference = target
        else:
            subscription_id = reference
            provider_reference = None

    elif isinstance(target, NewSubscriptionTarget):
        raise errors.InvalidBenefitRevocation(
            transaction_id=str(grant_transaction.id),
            reason="A revocation cannot create a new subscription",
        )

    else:
        assert_never(target)

    if subscription_id != grant_transaction.subscription_id:
        raise errors.InvalidBenefitSubscription(reason="The transaction targets another subscription")

    return subscription_id, provider_reference


def _application_result(
    benefit_transaction: BenefitTransaction,
    *,
    created: bool,
) -> BenefitTransactionApplicationResult:
    return BenefitTransactionApplicationResult(
        transaction_id=benefit_transaction.id,
        transaction_created=created,
        subscription_id=benefit_transaction.subscription_id,
    )


async def _accept_subscription_transaction(
    execute: ExecuteType,
    benefit_transaction: BenefitTransaction,
    subscription: SubscriptionSnapshot,
    provider_reference: ExternalSubscriptionTarget | None,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> Callable[[], None]:
    if not await operations.insert_benefit_transaction(execute, benefit_transaction):
        raise errors.ConcurrentBenefitTransaction(
            source_id=int(benefit_transaction.source_id),
            source_transaction_id=str(benefit_transaction.source_transaction_id),
        )

    if provider_reference is not None:
        await operations.insert_provider_subscription_reference(
            execute,
            provider_id=provider_reference.provider_id,
            provider_account_id=provider_reference.provider_account_id,
            provider_subscription_id=provider_reference.provider_subscription_id,
            subscription_id=benefit_transaction.subscription_id,
        )

    _, callback = await subscription_domain.save_subscription(
        execute,
        benefit_transaction.subscription_id,
        benefit_transaction.id,
        subscription,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    return callback


async def _grant_benefit(
    execute: ExecuteType,
    benefit_transaction: BenefitTransaction,
    package: BenefitPackage,
    effect: GrantBenefitEffect,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[Callable[[], None]]:
    try:
        _, callbacks = await entitlement_domain.grant_source_entitlements(
            execute,
            source_id=BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant_transaction_id=benefit_transaction.id,
            user_id=benefit_transaction.user_id,
            guarantees=package.entitlements,
            starts_at=effect.starts_at,
            expires_at=effect.expires_at,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )
    except entitlement_errors.InvalidSourceEntitlement as error:
        raise errors.InvalidBenefitGrant(
            transaction_id=str(benefit_transaction.id),
            reason=str(error),
        ) from error

    return callbacks


async def _revoke_benefit(
    execute: ExecuteType,
    benefit_transaction: BenefitTransaction,
    grant_transaction: BenefitTransaction,
    package: BenefitPackage,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[Callable[[], None]]:
    _, callbacks = await entitlement_domain.revoke_source_entitlements(
        execute,
        source_id=BENEFITS_ENTITLEMENT_SOURCE_ID,
        grant_transaction_id=grant_transaction.id,
        revoked_by_transaction_id=benefit_transaction.id,
        user_id=grant_transaction.user_id,
        kind_ids=[guarantee.kind_id for guarantee in package.entitlements],
        revoked_at=benefit_transaction.effective_at,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    return callbacks


async def _apply_regular_subscription_transaction(
    execute: ExecuteType,
    subscription: SubscriptionSnapshot,
    command: BenefitTransactionCommand,
    effect: SubscriptionUpdateEffect | GrantBenefitEffect,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[BenefitTransaction, list[Callable[[], None]]]:
    package = get_benefit(subscription.benefit_id)
    subscription_id, provider_reference = await _resolve_regular_subscription_target(
        execute,
        command.subscription_target,
    )
    benefit_transaction = BenefitTransaction(
        id=operations.new_benefit_transaction_id(),
        source_id=command.source_id,
        source_transaction_id=command.source_transaction_id,
        kind=effect.transaction_kind,
        user_id=subscription.user_id,
        benefit_id=package.id,
        subscription_id=subscription_id,
        effective_at=command.effective_at,
        starts_at=effect.starts_at if isinstance(effect, GrantBenefitEffect) else None,
        expires_at=effect.expires_at if isinstance(effect, GrantBenefitEffect) else None,
    )
    subscription_callback = await _accept_subscription_transaction(
        execute,
        benefit_transaction,
        subscription,
        provider_reference,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    callbacks = [subscription_callback]

    if isinstance(effect, GrantBenefitEffect):
        callbacks.extend(
            await _grant_benefit(
                execute,
                benefit_transaction,
                package,
                effect,
                evaluation_time=evaluation_time,
                actor_kind=actor_kind,
                actor_id=actor_id,
            )
        )

    return benefit_transaction, callbacks


async def _apply_revoke_subscription_transaction(
    execute: ExecuteType,
    subscription: SubscriptionSnapshot,
    command: BenefitTransactionCommand,
    effect: RevokeBenefitEffect,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[BenefitTransaction, list[Callable[[], None]]]:
    subscription_package = get_benefit(subscription.benefit_id)
    grant_transaction = await _load_grant_to_revoke(execute, effect, subscription)
    grant_package = (
        subscription_package
        if subscription_package.id == grant_transaction.benefit_id
        else get_benefit(grant_transaction.benefit_id)
    )
    subscription_id, provider_reference = await _resolve_revoke_subscription_target(
        execute,
        command.subscription_target,
        grant_transaction,
    )
    benefit_transaction = BenefitTransaction(
        id=operations.new_benefit_transaction_id(),
        source_id=command.source_id,
        source_transaction_id=command.source_transaction_id,
        kind=effect.transaction_kind,
        user_id=subscription.user_id,
        benefit_id=grant_package.id,
        subscription_id=subscription_id,
        effective_at=command.effective_at,
        revokes_transaction_id=effect.revokes_transaction_id,
    )
    subscription_callback = await _accept_subscription_transaction(
        execute,
        benefit_transaction,
        subscription,
        provider_reference,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    callbacks = await _revoke_benefit(
        execute,
        benefit_transaction,
        grant_transaction,
        grant_package,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    return benefit_transaction, [subscription_callback, *callbacks]


async def apply_subscription_transaction(
    subscription: SubscriptionSnapshot,
    command: BenefitTransactionCommand,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> BenefitTransactionApplicationResult:
    """Atomically apply one benefit transaction to subscription and entitlement state."""
    evaluation_time = datetime.datetime.now(tz=datetime.UTC)
    business_event_callbacks: list[Callable[[], None]] = []

    async with transaction() as execute:
        source_id, source_transaction_id = command.source_identity
        stored = await operations.load_benefit_transaction_by_source(
            execute,
            source_id=source_id,
            source_transaction_id=source_transaction_id,
        )

        if stored is not None:
            # Trusted callers never reuse a source identity; the stored transaction is authoritative.
            return _application_result(stored, created=False)

        # Source identity uniqueness prevents duplicated operations. If concurrent first
        # operations for one external subscription become likely, lock its provider identity
        # from target resolution through provider reference creation.
        effect = command.effect

        if isinstance(effect, RevokeBenefitEffect):
            benefit_transaction, business_event_callbacks = await _apply_revoke_subscription_transaction(
                execute,
                subscription,
                command,
                effect,
                evaluation_time=evaluation_time,
                actor_kind=actor_kind,
                actor_id=actor_id,
            )
        else:
            benefit_transaction, business_event_callbacks = await _apply_regular_subscription_transaction(
                execute,
                subscription,
                command,
                effect,
                evaluation_time=evaluation_time,
                actor_kind=actor_kind,
                actor_id=actor_id,
            )

    for callback in business_event_callbacks:
        callback()

    return _application_result(benefit_transaction, created=True)
