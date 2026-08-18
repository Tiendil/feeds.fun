import datetime
import enum
from collections.abc import Callable
from functools import partial

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind, AuditEventName
from ffun.core import logging
from ffun.core.postgresql import ExecuteType, run_in_transaction, transaction
from ffun.domain.entities import BenefitTransactionId, SerializedId, SubscriptionId, UserId
from ffun.locks.domain import Lock
from ffun.locks.entities import LockKind
from ffun.subscriptions import errors, operations
from ffun.subscriptions.entities import (
    SaveSubscriptionOutcome,
    Subscription,
    SubscriptionSaveResult,
    SubscriptionSnapshot,
    SubscriptionStatusId,
)

get_subscription = run_in_transaction(operations.load_subscription)
new_subscription_id = operations.new_subscription_id

logger = logging.get_module_logger()

ALIVE_SUBSCRIPTION_STATUSES = [
    SubscriptionStatusId.pending,
    SubscriptionStatusId.trialing,
    SubscriptionStatusId.active,
    SubscriptionStatusId.past_due,
    SubscriptionStatusId.paused,
]


class _SaveSubscriptionCommand(enum.IntEnum):
    ignore = 1
    upsert = 2


def _empty_business_event_callback() -> None:
    pass


def _decide_subscription_save(
    stored: Subscription | None,
    incoming: SubscriptionSnapshot,
) -> tuple[_SaveSubscriptionCommand, SaveSubscriptionOutcome]:
    if stored is None:
        return _SaveSubscriptionCommand.upsert, SaveSubscriptionOutcome.created

    if stored.user_id != incoming.user_id:
        raise errors.SubscriptionConflict(subscription_id=str(stored.id))

    if incoming.provider_updated_at < stored.provider_updated_at:
        return _SaveSubscriptionCommand.ignore, SaveSubscriptionOutcome.skipped

    if incoming.provider_updated_at == stored.provider_updated_at:
        if not stored.has_same_business_state_as(incoming):
            raise errors.SubscriptionConflict(subscription_id=str(stored.id))

        return _SaveSubscriptionCommand.ignore, SaveSubscriptionOutcome.skipped

    if stored.has_same_business_state_as(incoming):
        return _SaveSubscriptionCommand.upsert, SaveSubscriptionOutcome.skipped

    return _SaveSubscriptionCommand.upsert, SaveSubscriptionOutcome.updated


async def save_subscription(  # noqa: CCR001
    execute: ExecuteType,
    subscription_id: SubscriptionId,
    state_transaction_id: BenefitTransactionId,
    snapshot: SubscriptionSnapshot,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[SubscriptionSaveResult, Callable[[], None]]:
    incoming = snapshot.with_identity(
        subscription_id=subscription_id,
        state_transaction_id=state_transaction_id,
    )

    async with Lock(execute, LockKind("subscription_state"), subscription_id):
        stored = await operations.load_subscription(execute, subscription_id)
        command, outcome = _decide_subscription_save(stored, snapshot)

        if command == _SaveSubscriptionCommand.upsert:
            await operations.upsert_subscription(execute, incoming)
            current = incoming
        else:
            assert stored is not None
            current = stored

        previous = stored if outcome == SaveSubscriptionOutcome.updated else None

        if outcome in (SaveSubscriptionOutcome.created, SaveSubscriptionOutcome.updated):
            await audit_domain.record(
                execute,
                event=AuditEventName("subscription_changed"),
                actor_kind=actor_kind,
                actor_id=actor_id,
                subject_kind=AuditEntityKind.user,
                subject_id=SerializedId(str(snapshot.user_id)),
                attributes={
                    "subscription_id": str(subscription_id),
                    "state_transaction_id": str(state_transaction_id),
                    "previous_state": previous.audit_state() if previous is not None else None,
                    "new_state": incoming.audit_state(),
                },
            )

    result = SubscriptionSaveResult(outcome=outcome, current=current, previous=previous)
    event_callback: Callable[[], None]

    if outcome in (SaveSubscriptionOutcome.created, SaveSubscriptionOutcome.updated):
        event_callback = partial(_emit_subscription_change_event, result)
    else:
        event_callback = _empty_business_event_callback

    return result, event_callback


def _emit_subscription_change_event(result: SubscriptionSaveResult) -> None:
    subscription = result.current
    logger.business_event(
        "subscription_changed",
        user_id=subscription.user_id,
        previous_status=result.previous.status.value if result.previous is not None else None,
        **subscription.business_event_attributes(),
    )


async def get_subscriptions_for_user(
    user_id: UserId,
    *,
    statuses: list[SubscriptionStatusId] | None = None,
) -> list[Subscription]:
    async with transaction() as transaction_execute:
        return await operations.load_subscriptions(
            transaction_execute,
            [user_id],
            statuses=statuses,
        )


async def get_alive_subscriptions_for_user(user_id: UserId) -> list[Subscription]:
    evaluation_time = datetime.datetime.now(tz=datetime.UTC)
    subscriptions = await get_subscriptions_for_user(user_id, statuses=ALIVE_SUBSCRIPTION_STATUSES)

    return [
        subscription
        for subscription in subscriptions
        if subscription.ends_at is None or subscription.ends_at > evaluation_time
    ]
