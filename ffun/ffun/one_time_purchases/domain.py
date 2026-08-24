from collections.abc import Callable
from functools import partial

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind, AuditEventName
from ffun.core import logging
from ffun.core.postgresql import ExecuteType, run_in_transaction, transaction
from ffun.domain.entities import (
    BenefitTransactionId,
    OneTimePurchaseId,
    PurchasedStateSaveOutcome,
    SerializedId,
    UserId,
)
from ffun.locks.domain import Lock
from ffun.locks.entities import LockKind
from ffun.one_time_purchases import errors, operations
from ffun.one_time_purchases.entities import (
    Purchase,
    PurchaseSaveResult,
    PurchaseSnapshot,
    PurchaseStatus,
)

get_purchase = run_in_transaction(operations.load_purchase)
load_provider_purchase_reference = operations.load_provider_purchase_reference
save_provider_purchase_reference = operations.save_provider_purchase_reference
new_purchase_id = operations.new_purchase_id

logger = logging.get_module_logger()


def _empty_business_event_callback() -> None:
    pass


def _decide_purchase_save(  # noqa: CCR001
    stored: Purchase | None,
    incoming: PurchaseSnapshot,
) -> PurchasedStateSaveOutcome:
    if stored is None:
        return PurchasedStateSaveOutcome.created

    if stored.user_id != incoming.user_id or stored.benefit_id != incoming.benefit_id:
        raise errors.PurchaseConflict(one_time_purchase_id=str(stored.id))

    if incoming.provider_updated_at < stored.provider_updated_at:
        return PurchasedStateSaveOutcome.stale

    if incoming.provider_updated_at == stored.provider_updated_at:
        if not stored.has_same_business_state_as(incoming):
            raise errors.PurchaseConflict(one_time_purchase_id=str(stored.id))

        return PurchasedStateSaveOutcome.same

    if stored.has_same_business_state_as(incoming):
        return PurchasedStateSaveOutcome.refreshed

    return PurchasedStateSaveOutcome.updated


async def save_purchase(  # noqa: CCR001
    execute: ExecuteType,
    one_time_purchase_id: OneTimePurchaseId,
    state_transaction_id: BenefitTransactionId,
    snapshot: PurchaseSnapshot,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[PurchaseSaveResult, Callable[[], None]]:
    incoming = snapshot.with_identity(
        one_time_purchase_id=one_time_purchase_id,
        state_transaction_id=state_transaction_id,
    )

    async with Lock(execute, LockKind("one_time_purchase_state"), one_time_purchase_id):
        stored = await operations.load_purchase(execute, one_time_purchase_id)
        outcome = _decide_purchase_save(stored, snapshot)

        if outcome in (
            PurchasedStateSaveOutcome.created,
            PurchasedStateSaveOutcome.updated,
            PurchasedStateSaveOutcome.refreshed,
        ):
            await operations.save_purchase(execute, incoming)
            current = incoming
        else:
            assert stored is not None
            current = stored

        previous = stored if outcome == PurchasedStateSaveOutcome.updated else None

        if outcome in (PurchasedStateSaveOutcome.created, PurchasedStateSaveOutcome.updated):
            await audit_domain.record(
                execute,
                event=AuditEventName("one_time_purchase_changed"),
                actor_kind=actor_kind,
                actor_id=actor_id,
                subject_kind=AuditEntityKind.user,
                subject_id=SerializedId(str(snapshot.user_id)),
                attributes={
                    "one_time_purchase_id": str(one_time_purchase_id),
                    "state_transaction_id": str(state_transaction_id),
                    "previous_state": previous.audit_state() if previous is not None else None,
                    "new_state": incoming.audit_state(),
                },
            )

    result = PurchaseSaveResult(outcome=outcome, current=current, previous=previous)
    event_callback: Callable[[], None]

    if outcome in (PurchasedStateSaveOutcome.created, PurchasedStateSaveOutcome.updated):
        event_callback = partial(_emit_purchase_change_event, result)
    else:
        event_callback = _empty_business_event_callback

    return result, event_callback


def _emit_purchase_change_event(result: PurchaseSaveResult) -> None:
    purchase = result.current
    logger.business_event(
        "one_time_purchase_changed",
        user_id=purchase.user_id,
        previous_status=result.previous.status.value if result.previous is not None else None,
        **purchase.business_event_attributes(),
    )


async def get_purchases_for_user(
    user_id: UserId,
    *,
    statuses: list[PurchaseStatus] | None = None,
) -> list[Purchase]:
    async with transaction() as transaction_execute:
        return await operations.load_purchases(
            transaction_execute,
            user_id,
            statuses=statuses,
        )
