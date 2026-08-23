import datetime
from collections.abc import Callable, Mapping
from functools import singledispatch

from ffun.audit.entities import AuditEntityKind
from ffun.benefits import errors, operations
from ffun.benefits.entities import (
    BenefitEntitlementAction,
    BenefitPackage,
    BenefitPackageTemplate,
    BenefitParameterId,
    BenefitTransaction,
    BenefitTransactionApplicationResult,
    BenefitTransactionCommand,
    ExternalTarget,
    InternalTarget,
    NewTarget,
    SubscriptionTarget,
    TargetIdT,
)
from ffun.benefits.settings import settings
from ffun.core.postgresql import ExecuteType, run_in_transaction, transaction
from ffun.domain.entities import BenefitId, PurchasedStateSaveOutcome, SerializedId, SubscriptionId
from ffun.entitlements import domain as entitlement_domain
from ffun.entitlements.entities import EntitlementSourceId
from ffun.subscriptions import domain as subscription_domain
from ffun.subscriptions.entities import (
    SubscriptionSaveResult,
    SubscriptionSnapshot,
)

BENEFITS_ENTITLEMENT_SOURCE_ID = EntitlementSourceId("benefits")

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


@singledispatch  # type: ignore[misc]
async def _resolve_subscription_target(
    target: object,
    execute: ExecuteType,
) -> SubscriptionId | None:
    raise NotImplementedError(f"Unsupported subscription target: {target!r}")


@_resolve_subscription_target.register(InternalTarget)
async def _resolve_internal_subscription_target(
    target: InternalTarget[SubscriptionId],
    _execute: ExecuteType,
) -> SubscriptionId:
    return target.internal_id


@_resolve_subscription_target.register  # type: ignore[misc]
async def _resolve_external_subscription_target(
    target: ExternalTarget,
    execute: ExecuteType,
) -> SubscriptionId | None:
    return await subscription_domain.load_provider_subscription_reference(
        execute,
        target.provider_reference,
    )


@_resolve_subscription_target.register  # type: ignore[misc]
async def _resolve_new_subscription_target(
    _target: NewTarget,
    _execute: ExecuteType,
) -> None:
    return None


async def _resolve_regular_subscription_target(
    execute: ExecuteType,
    target: SubscriptionTarget,
) -> SubscriptionId:
    subscription_id = await _resolve_subscription_target(target, execute)

    if subscription_id is None:
        subscription_id = subscription_domain.new_subscription_id()

    if target.provider_reference is not None:
        await subscription_domain.insert_provider_subscription_reference(
            execute,
            target.provider_reference,
            subscription_id=subscription_id,
        )

    return subscription_id


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


async def _accept_subscription_transaction(
    execute: ExecuteType,
    benefit_transaction: BenefitTransaction,
    subscription: SubscriptionSnapshot,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[SubscriptionSaveResult, Callable[[], None]]:
    subscription_id = benefit_transaction.get_subscription_id_or_raise()

    if not await operations.save_benefit_transaction(execute, benefit_transaction):
        raise errors.ConcurrentBenefitTransaction(
            source_id=int(benefit_transaction.source_id),
            source_transaction_id=str(benefit_transaction.source_transaction_id),
        )

    return await subscription_domain.save_subscription(
        execute,
        subscription_id,
        benefit_transaction.id,
        subscription,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )


async def _replace_benefit(  # noqa: CFQ002
    execute: ExecuteType,
    benefit_transaction: BenefitTransaction,
    package: BenefitPackage,
    subscription: SubscriptionSnapshot,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> list[Callable[[], None]]:
    subscription_id = benefit_transaction.get_subscription_id_or_raise()

    _, callbacks = await entitlement_domain.revoke_subscription_entitlements(
        execute,
        subscription_id=subscription_id,
        revoked_by_transaction_id=benefit_transaction.id,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )

    if benefit_transaction.entitlement_action == BenefitEntitlementAction.revoke:
        return callbacks

    _, grant_callbacks = await entitlement_domain.grant_source_entitlements(
        execute,
        source_id=BENEFITS_ENTITLEMENT_SOURCE_ID,
        grant_transaction_id=benefit_transaction.id,
        user_id=benefit_transaction.user_id,
        subscription_id=subscription_id,
        one_time_purchase_id=None,
        guarantees=package.guarantees,
        starts_at=subscription.period_starts_at,
        expires_at=subscription.period_ends_at,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )

    callbacks.extend(grant_callbacks)
    return callbacks


async def _apply_transaction(  # noqa: CFQ002
    command: BenefitTransactionCommand[SubscriptionId],
    execute: ExecuteType,
    subscription: SubscriptionSnapshot,
    parameters: Mapping[BenefitParameterId, object],
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[BenefitTransaction, list[Callable[[], None]]]:
    package = materialize_benefit_package(subscription.benefit_id, parameters)
    subscription_id = await _resolve_regular_subscription_target(
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
    subscription_save, subscription_callback = await _accept_subscription_transaction(
        execute,
        benefit_transaction,
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
        subscription,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )
    return benefit_transaction, [subscription_callback, *callbacks]


async def apply_subscription_transaction(
    subscription: SubscriptionSnapshot,
    parameters: Mapping[BenefitParameterId, object],
    command: BenefitTransactionCommand[SubscriptionId],
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> BenefitTransactionApplicationResult[SubscriptionId]:
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
            subscription_id = stored.get_subscription_id_or_raise()
            return _application_result(stored, subscription_id, created=False)

        # Source identity uniqueness prevents duplicated operations. If concurrent first
        # operations for one external subscription become likely, lock its provider identity
        # from target resolution through provider reference creation.
        benefit_transaction, business_event_callbacks = await _apply_transaction(
            command,
            execute,
            subscription,
            parameters,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )

    for callback in business_event_callbacks:
        callback()

    subscription_id = benefit_transaction.get_subscription_id_or_raise()
    return _application_result(benefit_transaction, subscription_id, created=True)
