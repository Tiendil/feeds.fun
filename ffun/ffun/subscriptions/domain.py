import datetime
import enum
import hashlib

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind, AuditEventName
from ffun.core import logging
from ffun.core.postgresql import run_in_transaction, transaction
from ffun.domain.entities import SerializedId, UserId
from ffun.locks.domain import locked_transaction
from ffun.locks.entities import LockKind
from ffun.subscriptions import errors, operations
from ffun.subscriptions.entities import (
    SaveSubscriptionOutcome,
    Subscription,
    SubscriptionStatusId,
)

get_subscription = run_in_transaction(operations.load_subscription)

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


def _decide_subscription_save(
    stored: Subscription | None,
    incoming: Subscription,
) -> tuple[_SaveSubscriptionCommand, SaveSubscriptionOutcome]:
    if stored is None:
        return _SaveSubscriptionCommand.upsert, SaveSubscriptionOutcome.created

    if not stored.has_same_ownership_as(incoming):
        raise errors.SubscriptionConflict(
            provider_id=incoming.provider_id,
            provider_merchant_id=incoming.provider_merchant_id,
            provider_subscription_id=incoming.provider_subscription_id,
        )

    if incoming.provider_updated_at < stored.provider_updated_at:
        return _SaveSubscriptionCommand.ignore, SaveSubscriptionOutcome.skipped

    if incoming.provider_updated_at == stored.provider_updated_at:
        if not stored.has_same_business_state_as(incoming):
            raise errors.SubscriptionConflict(
                provider_id=incoming.provider_id,
                provider_merchant_id=incoming.provider_merchant_id,
                provider_subscription_id=incoming.provider_subscription_id,
            )

        return _SaveSubscriptionCommand.ignore, SaveSubscriptionOutcome.skipped

    if stored.has_same_business_state_as(incoming):
        return _SaveSubscriptionCommand.upsert, SaveSubscriptionOutcome.skipped

    return _SaveSubscriptionCommand.upsert, SaveSubscriptionOutcome.updated


async def save_subscription(  # noqa: CCR001
    subscription: Subscription,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> SaveSubscriptionOutcome:
    identity_bytes = b"".join(
        len(part.encode()).to_bytes(8, byteorder="big") + part.encode()
        for part in (
            subscription.provider_id,
            subscription.provider_merchant_id,
            subscription.provider_subscription_id,
        )
    )
    lock_argument = hashlib.sha256(identity_bytes, usedforsecurity=False).hexdigest()
    previous: Subscription | None = None

    async with locked_transaction(LockKind("subscription_identity"), lock_argument) as transaction_execute:
        stored = await operations.load_subscription(
            transaction_execute,
            provider_id=subscription.provider_id,
            provider_merchant_id=subscription.provider_merchant_id,
            provider_subscription_id=subscription.provider_subscription_id,
        )
        command, outcome = _decide_subscription_save(stored, subscription)

        if command == _SaveSubscriptionCommand.upsert:
            await operations.upsert_subscription(transaction_execute, subscription)

        if outcome == SaveSubscriptionOutcome.updated:
            previous = stored

        if outcome in (SaveSubscriptionOutcome.created, SaveSubscriptionOutcome.updated):
            await audit_domain.record(
                transaction_execute,
                event=AuditEventName("subscription_changed"),
                actor_kind=actor_kind,
                actor_id=actor_id,
                subject_kind=AuditEntityKind.user,
                subject_id=SerializedId(str(subscription.user_id)),
                attributes={
                    "provider_id": subscription.provider_id,
                    "provider_merchant_id": subscription.provider_merchant_id,
                    "provider_subscription_id": subscription.provider_subscription_id,
                    "provider_customer_id": subscription.provider_customer_id,
                    "previous_state": previous.audit_state() if previous is not None else None,
                    "new_state": subscription.audit_state(),
                },
            )

    if outcome in (SaveSubscriptionOutcome.created, SaveSubscriptionOutcome.updated):
        logger.business_event(
            "subscription_changed",
            user_id=subscription.user_id,
            previous_status=previous.status.value if previous is not None else None,
            **subscription.business_event_attributes(),
        )

    return outcome


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
