import uuid
from collections.abc import Mapping
from typing import cast

from pydantic import ValidationError

from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import SubscriptionId, UserId
from ffun.subscriptions import errors
from ffun.subscriptions.entities import ProviderSubscriptionReference, Subscription, SubscriptionStatusId


def new_subscription_id() -> SubscriptionId:
    return SubscriptionId(uuid.uuid4())


def row_to_subscription(row: Mapping[str, object]) -> Subscription:
    data = dict(row)
    data.pop("created_at", None)
    data.pop("updated_at", None)

    try:
        return Subscription.model_validate(data)
    except ValidationError as exception:
        raise errors.InvalidStoredSubscription() from exception


async def load_subscription(
    execute: ExecuteType,
    subscription_id: SubscriptionId,
) -> Subscription | None:
    sql = """
SELECT *
FROM sb_subscriptions AS subscriptions
WHERE subscriptions.id = %(subscription_id)s
"""
    rows = await execute(sql, {"subscription_id": subscription_id})

    if not rows:
        return None

    return row_to_subscription(rows[0])


async def load_provider_subscription_reference(
    execute: ExecuteType,
    reference: ProviderSubscriptionReference,
) -> SubscriptionId | None:
    sql = """
    SELECT subscription_id
    FROM sb_subscription_refs
    WHERE provider_id = %(provider_id)s
      AND provider_account_id = %(provider_account_id)s
      AND provider_subscription_id = %(provider_subscription_id)s
    """
    rows = await execute(sql, reference.model_dump())

    if not rows:
        return None

    return cast(SubscriptionId, rows[0]["subscription_id"])


async def insert_provider_subscription_reference(
    execute: ExecuteType,
    reference: ProviderSubscriptionReference,
    *,
    subscription_id: SubscriptionId,
) -> None:
    sql = """
    INSERT INTO sb_subscription_refs (
        provider_id,
        provider_account_id,
        provider_subscription_id,
        subscription_id
    )
    VALUES (
        %(provider_id)s,
        %(provider_account_id)s,
        %(provider_subscription_id)s,
        %(subscription_id)s
    )
    ON CONFLICT DO NOTHING
    RETURNING subscription_id
    """
    rows = await execute(
        sql,
        {**reference.model_dump(), "subscription_id": subscription_id},
    )

    if rows:
        return

    stored_subscription_id = await load_provider_subscription_reference(execute, reference)

    if stored_subscription_id == subscription_id:
        return

    raise errors.ProviderSubscriptionReferenceConflict(
        provider_id=reference.provider_id,
        provider_account_id=reference.provider_account_id,
        provider_subscription_id=reference.provider_subscription_id,
        stored_subscription_id=(str(stored_subscription_id) if stored_subscription_id is not None else None),
        requested_subscription_id=str(subscription_id),
    )


async def upsert_subscription(execute: ExecuteType, subscription: Subscription) -> None:
    sql = """
    INSERT INTO sb_subscriptions (
        id,
        state_transaction_id,
        user_id,
        benefit_id,
        status,
        provider_status,
        started_at,
        period_starts_at,
        period_ends_at,
        expected_renewal_at,
        ends_at,
        provider_updated_at
    )
    VALUES (
        %(id)s,
        %(state_transaction_id)s,
        %(user_id)s,
        %(benefit_id)s,
        %(status)s,
        %(provider_status)s,
        %(started_at)s,
        %(period_starts_at)s,
        %(period_ends_at)s,
        %(expected_renewal_at)s,
        %(ends_at)s,
        %(provider_updated_at)s
    )
    ON CONFLICT (id)
    DO UPDATE SET
        state_transaction_id = EXCLUDED.state_transaction_id,
        benefit_id = EXCLUDED.benefit_id,
        status = EXCLUDED.status,
        provider_status = EXCLUDED.provider_status,
        started_at = EXCLUDED.started_at,
        period_starts_at = EXCLUDED.period_starts_at,
        period_ends_at = EXCLUDED.period_ends_at,
        expected_renewal_at = EXCLUDED.expected_renewal_at,
        ends_at = EXCLUDED.ends_at,
        provider_updated_at = EXCLUDED.provider_updated_at,
        updated_at = CURRENT_TIMESTAMP
    """
    await execute(sql, subscription.model_dump())


async def load_subscriptions(
    execute: ExecuteType,
    user_ids: list[UserId],
    *,
    statuses: list[SubscriptionStatusId] | None = None,
) -> list[Subscription]:
    if not user_ids or statuses == []:
        return []

    sql = """
SELECT *
FROM sb_subscriptions AS subscriptions
WHERE subscriptions.user_id = ANY(%(user_ids)s)
  AND (
      %(statuses)s::smallint[] IS NULL
      OR subscriptions.status = ANY(%(statuses)s::smallint[])
  )
ORDER BY
    subscriptions.user_id,
    subscriptions.started_at DESC,
    subscriptions.id
"""
    rows = await execute(sql, {"user_ids": user_ids, "statuses": statuses})
    return [row_to_subscription(row) for row in rows]
