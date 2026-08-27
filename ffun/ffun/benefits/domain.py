import datetime
from collections.abc import Awaitable, Callable, Mapping
from typing import Never, assert_never, cast

from ffun.audit.entities import AuditEntityKind
from ffun.benefits import errors, operations, target_resolution
from ffun.benefits.entities import (
    BenefitEntitlementAction,
    BenefitPackage,
    BenefitPackageTemplate,
    BenefitParameterId,
    BenefitSourceTransactionId,
    BenefitSubscriptionRefreshCommand,
    BenefitSubscriptionRefreshOutcome,
    BenefitSubscriptionRefreshResult,
    BenefitTransaction,
    BenefitTransactionApplicationResult,
    BenefitTransactionCommand,
    TargetIdT,
)
from ffun.benefits.settings import settings
from ffun.core.postgresql import TransactionExecuteType, run_in_transaction, transaction
from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.entities import (
    BenefitId,
    OneTimePurchaseId,
    PurchasedStateSaveOutcome,
    SerializedId,
    SubscriptionId,
)
from ffun.entitlements import domain as entitlement_domain
from ffun.entitlements.entities import SourceEntitlement
from ffun.one_time_purchases import domain as purchase_domain
from ffun.one_time_purchases.entities import PurchaseSnapshot
from ffun.subscriptions import domain as subscription_domain
from ffun.subscriptions.entities import SubscriptionSnapshot

_ActualizeTransaction = Callable[
    [TransactionExecuteType, datetime.datetime],
    Awaitable[tuple[BenefitTransaction, list[Callable[[], None]]]],
]

get_benefit_transaction = run_in_transaction(operations.load_benefit_transaction)


def _find_benefit(benefit_id: BenefitId) -> BenefitPackageTemplate | None:
    for template in settings.package_templates:
        if template.id == benefit_id:
            return template

    return None


def has_benefit(benefit_id: BenefitId) -> bool:
    return _find_benefit(benefit_id) is not None


def get_benefit(benefit_id: BenefitId) -> BenefitPackageTemplate:
    template = _find_benefit(benefit_id)

    if template is not None:
        return template

    raise errors.UnknownBenefit(benefit_id=benefit_id)


def materialize_benefit_package(
    benefit_id: BenefitId,
    parameters: Mapping[BenefitParameterId, object],
) -> BenefitPackage:
    return get_benefit(benefit_id).materialize(parameters)


def _application_result(
    benefit_transaction: BenefitTransaction,
    target_id: TargetIdT,
    *,
    created: bool,
) -> BenefitTransactionApplicationResult[TargetIdT]:
    return BenefitTransactionApplicationResult(
        transaction_id=benefit_transaction.id,
        transaction_created=created,
        target_id=target_id,
    )


def _validate_package_for_interval(package: BenefitPackage, period_ends_at: datetime.datetime) -> None:
    period_is_lifetime = period_ends_at == LIFETIME_INTERVAL_END_MARKER

    for guarantee in package.guarantees:
        kind = entitlement_domain.get_entitlement_kind(guarantee.kind_id)

        if kind.is_lifetime == period_is_lifetime:
            continue

        raise errors.InvalidBenefitEntitlement(
            benefit_id=package.id,
            entitlement_kind_id=int(guarantee.kind_id),
            reason="entitlement kind lifetime status must match the benefit period",
        )


def _subscription_has_required_entitlements(
    package: BenefitPackage,
    subscription: SubscriptionSnapshot,
    source_entitlements: list[SourceEntitlement],
    *,
    evaluation_time: datetime.datetime,
) -> bool:
    expected = sorted(
        (
            guarantee.kind_id,
            guarantee.value,
            max(subscription.period_starts_at, evaluation_time),
            subscription.period_ends_at,
        )
        for guarantee in package.guarantees
    )
    current = sorted(
        (
            entitlement.kind_id,
            entitlement.value,
            max(entitlement.starts_at, evaluation_time),
            entitlement.expires_at,
        )
        for entitlement in source_entitlements
        if entitlement.revoked_at is None and entitlement.expires_at > evaluation_time
    )
    return current == expected


def _run_business_event_callbacks(callbacks: list[Callable[[], None]]) -> None:
    first_error: Exception | None = None

    for callback in callbacks:
        try:
            callback()
        except Exception as error:
            if first_error is None:
                first_error = error

    if first_error is not None:
        raise first_error


async def _revoke_owned_entitlements(  # noqa: CFQ002
    execute: TransactionExecuteType,
    benefit_transaction: BenefitTransaction,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[Callable[[], None]]:
    if benefit_transaction.subscription_id is not None:
        _, callbacks = await entitlement_domain.revoke_subscription_entitlements(
            execute,
            subscription_id=benefit_transaction.subscription_id,
            revoked_by_transaction_id=benefit_transaction.id,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )
        return callbacks

    if benefit_transaction.one_time_purchase_id is not None:
        _, callbacks = await entitlement_domain.revoke_one_time_purchase_entitlements(
            execute,
            one_time_purchase_id=benefit_transaction.one_time_purchase_id,
            revoked_by_transaction_id=benefit_transaction.id,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )
        return callbacks

    assert_never(cast(Never, benefit_transaction))


async def _replace_benefit(  # noqa: CFQ002
    execute: TransactionExecuteType,
    benefit_transaction: BenefitTransaction,
    package: BenefitPackage,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[Callable[[], None]]:
    # Concurrent replacements for different targets of the same user can deadlock when
    # revocations and grants acquire entitlement-kind locks in different orders. A fix
    # must lock the sorted union of existing and desired kinds for the whole replacement.
    callbacks = await _revoke_owned_entitlements(
        execute,
        benefit_transaction,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )

    if benefit_transaction.entitlement_action == BenefitEntitlementAction.revoke:
        return callbacks

    _, grant_callbacks = await entitlement_domain.grant_source_entitlements(
        execute,
        grant_transaction_id=benefit_transaction.id,
        user_id=benefit_transaction.user_id,
        subscription_id=benefit_transaction.subscription_id,
        one_time_purchase_id=benefit_transaction.one_time_purchase_id,
        guarantees=package.guarantees,
        starts_at=benefit_transaction.period_starts_at,
        expires_at=benefit_transaction.period_ends_at,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )

    callbacks.extend(grant_callbacks)
    return callbacks


async def _actualize_subscription_transaction(  # noqa: CFQ002
    command: BenefitTransactionCommand[SubscriptionId],
    execute: TransactionExecuteType,
    subscription: SubscriptionSnapshot,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[BenefitTransaction, list[Callable[[], None]]]:
    package = materialize_benefit_package(subscription.benefit_id, {})
    _validate_package_for_interval(package, subscription.period_ends_at)
    subscription_id = await target_resolution.resolve_subscription_target(
        execute,
        command.target,
    )
    benefit_transaction = BenefitTransaction(
        id=operations.new_benefit_transaction_id(),
        source_id=command.source_id,
        source_transaction_id=command.source_transaction_id,
        entitlement_action=(
            BenefitEntitlementAction.grant if subscription.status.grants_benefits else BenefitEntitlementAction.revoke
        ),
        user_id=subscription.user_id,
        benefit_id=package.id,
        subscription_id=subscription_id,
        effective_at=command.effective_at,
        period_starts_at=subscription.period_starts_at,
        period_ends_at=subscription.period_ends_at,
    )
    await operations.save_benefit_transaction(execute, benefit_transaction)
    subscription_save, subscription_callback = await subscription_domain.save_subscription(
        execute,
        subscription_id,
        benefit_transaction.id,
        subscription,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    if subscription_save.outcome == PurchasedStateSaveOutcome.stale:
        raise errors.StaleBenefitTransaction(
            subscription_id=str(subscription_id),
            incoming_provider_updated_at=subscription.provider_updated_at.isoformat(),
            current_provider_updated_at=subscription_save.current.provider_updated_at.isoformat(),
        )

    callbacks = await _replace_benefit(
        execute,
        benefit_transaction,
        package,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    return benefit_transaction, [subscription_callback, *callbacks]


async def _actualize_one_time_purchase_transaction(  # noqa: CFQ002
    command: BenefitTransactionCommand[OneTimePurchaseId],
    execute: TransactionExecuteType,
    purchase: PurchaseSnapshot,
    parameters: Mapping[BenefitParameterId, object],
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[BenefitTransaction, list[Callable[[], None]]]:
    package = materialize_benefit_package(purchase.benefit_id, parameters)
    _validate_package_for_interval(package, purchase.period_ends_at)
    one_time_purchase_id = await target_resolution.resolve_one_time_purchase_target(
        execute,
        command.target,
    )
    benefit_transaction = BenefitTransaction(
        id=operations.new_benefit_transaction_id(),
        source_id=command.source_id,
        source_transaction_id=command.source_transaction_id,
        entitlement_action=(
            BenefitEntitlementAction.grant if purchase.status.grants_benefits else BenefitEntitlementAction.revoke
        ),
        user_id=purchase.user_id,
        benefit_id=package.id,
        one_time_purchase_id=one_time_purchase_id,
        effective_at=command.effective_at,
        period_starts_at=purchase.period_starts_at,
        period_ends_at=purchase.period_ends_at,
    )
    await operations.save_benefit_transaction(execute, benefit_transaction)
    purchase_save, purchase_callback = await purchase_domain.save_purchase(
        execute,
        one_time_purchase_id,
        benefit_transaction.id,
        purchase,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    if purchase_save.outcome == PurchasedStateSaveOutcome.stale:
        raise errors.StaleBenefitTransaction(
            one_time_purchase_id=str(one_time_purchase_id),
            incoming_provider_updated_at=purchase.provider_updated_at.isoformat(),
            current_provider_updated_at=purchase_save.current.provider_updated_at.isoformat(),
        )

    callbacks = await _replace_benefit(
        execute,
        benefit_transaction,
        package,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    return benefit_transaction, [purchase_callback, *callbacks]


async def _apply_benefit_transaction(
    command: BenefitTransactionCommand[TargetIdT],
    *,
    actualize: _ActualizeTransaction,
    get_target_id: Callable[[BenefitTransaction], TargetIdT],
) -> BenefitTransactionApplicationResult[TargetIdT]:
    evaluation_time = datetime.datetime.now(tz=datetime.UTC)

    async with transaction() as execute:
        source_id, source_transaction_id = command.source_identity
        stored = await operations.load_benefit_transaction_by_source(
            execute,
            source_id=source_id,
            source_transaction_id=source_transaction_id,
        )

        if stored is not None:
            # Trusted callers never reuse a source identity; the stored transaction is authoritative.
            return _application_result(stored, get_target_id(stored), created=False)

        # Source identity uniqueness prevents duplicated operations. If concurrent first
        # operations for one external target become likely, lock its provider identity
        # from target resolution through provider reference creation.
        benefit_transaction, business_event_callbacks = await actualize(
            execute,
            evaluation_time,
        )

    _run_business_event_callbacks(business_event_callbacks)

    return _application_result(
        benefit_transaction,
        get_target_id(benefit_transaction),
        created=True,
    )


async def apply_subscription_transaction(
    subscription: SubscriptionSnapshot,
    command: BenefitTransactionCommand[SubscriptionId],
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> BenefitTransactionApplicationResult[SubscriptionId]:
    """Atomically apply one benefit transaction to subscription and entitlement state."""
    return await _apply_benefit_transaction(
        command,
        actualize=lambda execute, evaluation_time: _actualize_subscription_transaction(
            command,
            execute,
            subscription,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        ),
        get_target_id=BenefitTransaction.get_subscription_id_or_raise,
    )


async def apply_one_time_purchase_transaction(
    purchase: PurchaseSnapshot,
    parameters: Mapping[BenefitParameterId, object],
    command: BenefitTransactionCommand[OneTimePurchaseId],
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> BenefitTransactionApplicationResult[OneTimePurchaseId]:
    """Atomically apply one benefit transaction to one-time-purchase and entitlement state."""
    return await _apply_benefit_transaction(
        command,
        actualize=lambda execute, evaluation_time: _actualize_one_time_purchase_transaction(
            command,
            execute,
            purchase,
            parameters,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        ),
        get_target_id=BenefitTransaction.get_one_time_purchase_id_or_raise,
    )


async def _refresh_subscription_entitlements(
    subscription_id: SubscriptionId,
    command: BenefitSubscriptionRefreshCommand,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> BenefitSubscriptionRefreshResult:
    callbacks: list[Callable[[], None]] = []

    async with transaction() as execute:
        async with subscription_domain.lock_subscription(execute, subscription_id):
            subscription = await subscription_domain.load_subscription(execute, subscription_id)

            if subscription is None:
                raise errors.InvalidBenefitSubscription(subscription_id=str(subscription_id), reason="not found")

            if subscription.benefit_id != command.benefit_id or not (
                subscription.is_in_effect(command.effective_at) or subscription.is_upcoming(command.effective_at)
            ):
                return BenefitSubscriptionRefreshResult(
                    subscription_id=subscription_id,
                    outcome=BenefitSubscriptionRefreshOutcome.ineligible,
                )

            package = materialize_benefit_package(command.benefit_id, {})
            _validate_package_for_interval(package, subscription.period_ends_at)
            source_entitlements = await entitlement_domain.load_source_entitlements_for_subscription(
                execute,
                subscription_id,
            )

            if _subscription_has_required_entitlements(
                package,
                subscription,
                source_entitlements,
                evaluation_time=command.effective_at,
            ):
                return BenefitSubscriptionRefreshResult(
                    subscription_id=subscription_id,
                    outcome=BenefitSubscriptionRefreshOutcome.unchanged,
                )

            transaction_id = operations.new_benefit_transaction_id()
            benefit_transaction = BenefitTransaction(
                id=transaction_id,
                source_id=command.source_id,
                source_transaction_id=BenefitSourceTransactionId(transaction_id),
                entitlement_action=BenefitEntitlementAction.grant,
                user_id=subscription.user_id,
                benefit_id=package.id,
                subscription_id=subscription.id,
                effective_at=command.effective_at,
                period_starts_at=subscription.period_starts_at,
                period_ends_at=subscription.period_ends_at,
            )
            await operations.save_benefit_transaction(execute, benefit_transaction)
            callbacks = await _replace_benefit(
                execute,
                benefit_transaction,
                package,
                evaluation_time=command.effective_at,
                actor_kind=actor_kind,
                actor_id=actor_id,
            )

    _run_business_event_callbacks(callbacks)

    return BenefitSubscriptionRefreshResult(
        subscription_id=subscription_id,
        outcome=BenefitSubscriptionRefreshOutcome.updated,
        transaction_id=benefit_transaction.id,
    )


async def refresh_subscription_entitlements(
    command: BenefitSubscriptionRefreshCommand,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[BenefitSubscriptionRefreshResult]:
    async with transaction() as execute:
        subscription_ids = await subscription_domain.load_subscription_ids_by_benefit(execute, command.benefit_id)

    results: list[BenefitSubscriptionRefreshResult] = []

    for subscription_id in subscription_ids:
        results.append(
            await _refresh_subscription_entitlements(
                subscription_id,
                command,
                actor_kind=actor_kind,
                actor_id=actor_id,
            )
        )

    return results
