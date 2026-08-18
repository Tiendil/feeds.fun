import datetime
from collections.abc import Callable

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


async def _load_reversed_transaction(
    execute: ExecuteType,
    effect: SubscriptionUpdateEffect | GrantBenefitEffect | RevokeBenefitEffect,
) -> BenefitTransaction | None:
    if not isinstance(effect, RevokeBenefitEffect):
        return None

    reversed_transaction = await operations.load_benefit_transaction(
        execute,
        effect.reverses_transaction_id,
    )

    if reversed_transaction is None:
        raise errors.BenefitTransactionNotFound(transaction_id=str(effect.reverses_transaction_id))

    return reversed_transaction


async def _resolve_subscription_id(
    execute: ExecuteType,
    command: BenefitTransactionCommand,
    reversed_transaction: BenefitTransaction | None,
) -> tuple[SubscriptionId, bool]:
    expected_subscription_id = (
        reversed_transaction.subscription_id if reversed_transaction is not None else None
    )
    target = command.subscription_target
    create_external_reference = False

    if isinstance(target, InternalSubscriptionTarget):
        subscription_id = target.subscription_id

    elif isinstance(target, ExternalSubscriptionTarget):
        reference = await operations.load_provider_subscription_reference(
            execute,
            provider_id=target.provider_id,
            provider_account_id=target.provider_account_id,
            provider_subscription_id=target.provider_subscription_id,
        )

        if reference is None:
            subscription_id = expected_subscription_id or subscription_domain.new_subscription_id()
            create_external_reference = True
        else:
            subscription_id = reference

    elif isinstance(target, NewSubscriptionTarget):
        if expected_subscription_id is not None:
            raise errors.InvalidBenefitTransactionReversal(
                transaction_id=str(reversed_transaction.id),
                reason="A revocation cannot create a new subscription",
            )

        subscription_id = subscription_domain.new_subscription_id()

    else:
        raise AssertionError(f"Unsupported subscription target: {target!r}")

    if expected_subscription_id is not None and subscription_id != expected_subscription_id:
        raise errors.InvalidBenefitSubscription(reason="The transaction targets another subscription")

    return subscription_id, create_external_reference


def _validate_reversed_transaction(
    reversed_transaction: BenefitTransaction,
    *,
    subscription_id: SubscriptionId,
    subscription: SubscriptionSnapshot,
) -> None:
    if reversed_transaction.kind != BenefitTransactionKind.grant:
        raise errors.InvalidBenefitTransactionReversal(
            transaction_id=str(reversed_transaction.id),
            reason="Only a benefit grant transaction can be reversed",
        )

    if (
        reversed_transaction.subscription_id != subscription_id
        or reversed_transaction.user_id != subscription.user_id
    ):
        raise errors.InvalidBenefitTransactionReversal(
            transaction_id=str(reversed_transaction.id),
            reason="The reversed grant belongs to another subscription",
        )


def _transaction_kind(
    effect: SubscriptionUpdateEffect | GrantBenefitEffect | RevokeBenefitEffect,
) -> BenefitTransactionKind:
    if isinstance(effect, SubscriptionUpdateEffect):
        return BenefitTransactionKind.subscription_update

    if isinstance(effect, GrantBenefitEffect):
        return BenefitTransactionKind.grant

    if isinstance(effect, RevokeBenefitEffect):
        return BenefitTransactionKind.revoke

    raise AssertionError(f"Unsupported benefit effect: {effect!r}")


def _new_benefit_transaction(
    command: BenefitTransactionCommand,
    subscription: SubscriptionSnapshot,
    *,
    subscription_id: SubscriptionId,
    benefit_id: BenefitId,
) -> BenefitTransaction:
    effect = command.effect

    return BenefitTransaction(
        id=operations.new_benefit_transaction_id(),
        source_id=command.source_id,
        source_transaction_id=command.source_transaction_id,
        kind=_transaction_kind(effect),
        user_id=subscription.user_id,
        benefit_id=benefit_id,
        subscription_id=subscription_id,
        effective_at=command.effective_at,
        starts_at=effect.starts_at if isinstance(effect, GrantBenefitEffect) else None,
        expires_at=effect.expires_at if isinstance(effect, GrantBenefitEffect) else None,
        reverses_transaction_id=(
            effect.reverses_transaction_id if isinstance(effect, RevokeBenefitEffect) else None
        ),
    )


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


async def _grant_benefit(
    execute: ExecuteType,
    benefit_transaction: BenefitTransaction,
    effect: GrantBenefitEffect,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[Callable[[], None]]:
    package = get_benefit(benefit_transaction.benefit_id)

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
    reversed_transaction: BenefitTransaction,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[Callable[[], None]]:
    package = get_benefit(reversed_transaction.benefit_id)

    _, callbacks = await entitlement_domain.revoke_source_entitlements(
        execute,
        source_id=BENEFITS_ENTITLEMENT_SOURCE_ID,
        grant_transaction_id=reversed_transaction.id,
        revoked_by_transaction_id=benefit_transaction.id,
        user_id=reversed_transaction.user_id,
        kind_ids=[guarantee.kind_id for guarantee in package.entitlements],
        revoked_at=benefit_transaction.effective_at,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    return callbacks


async def _apply_entitlement_effect(
    execute: ExecuteType,
    benefit_transaction: BenefitTransaction,
    effect: SubscriptionUpdateEffect | GrantBenefitEffect | RevokeBenefitEffect,
    reversed_transaction: BenefitTransaction | None,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[Callable[[], None]]:
    if isinstance(effect, SubscriptionUpdateEffect):
        return []

    if isinstance(effect, GrantBenefitEffect):
        return await _grant_benefit(
            execute,
            benefit_transaction,
            effect,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )

    assert reversed_transaction is not None
    return await _revoke_benefit(
        execute,
        benefit_transaction,
        reversed_transaction,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )


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

        subscription_benefit = get_benefit(subscription.benefit_id)
        reversed_transaction = await _load_reversed_transaction(execute, command.effect)

        # The source identity constraint prevents duplicated operations. If concurrent first
        # operations for one external subscription become likely, lock its provider identity
        # while resolving and creating the provider subscription reference.
        subscription_id, create_external_reference = await _resolve_subscription_id(
            execute,
            command,
            reversed_transaction,
        )

        if reversed_transaction is not None:
            _validate_reversed_transaction(
                reversed_transaction,
                subscription_id=subscription_id,
                subscription=subscription,
            )

        transaction_benefit_id = (
            reversed_transaction.benefit_id
            if reversed_transaction is not None
            else subscription_benefit.id
        )
        candidate = _new_benefit_transaction(
            command,
            subscription,
            subscription_id=subscription_id,
            benefit_id=transaction_benefit_id,
        )
        if not await operations.insert_benefit_transaction(execute, candidate):
            raise errors.ConcurrentBenefitTransaction(
                source_id=int(candidate.source_id),
                source_transaction_id=str(candidate.source_transaction_id),
            )

        benefit_transaction = candidate

        target = command.subscription_target
        if create_external_reference:
            assert isinstance(target, ExternalSubscriptionTarget)
            await operations.insert_provider_subscription_reference(
                execute,
                provider_id=target.provider_id,
                provider_account_id=target.provider_account_id,
                provider_subscription_id=target.provider_subscription_id,
                subscription_id=subscription_id,
            )

        _, subscription_callback = await subscription_domain.save_subscription(
            execute,
            subscription_id,
            benefit_transaction.id,
            subscription,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )
        business_event_callbacks.append(subscription_callback)
        business_event_callbacks.extend(
            await _apply_entitlement_effect(
                execute,
                benefit_transaction,
                command.effect,
                reversed_transaction,
                evaluation_time=evaluation_time,
                actor_kind=actor_kind,
                actor_id=actor_id,
            )
        )

    for callback in business_event_callbacks:
        callback()

    return _application_result(benefit_transaction, created=True)
