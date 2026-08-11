from collections.abc import Mapping

from pydantic import ValidationError

from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import UserId
from ffun.subscriptions import errors
from ffun.subscriptions.entities import (
    ProviderId,
    ProviderMerchantId,
    ProviderSubscriptionId,
    Subscription,
    SubscriptionStatusId,
)


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
    *,
    provider_id: ProviderId,
    provider_merchant_id: ProviderMerchantId,
    provider_subscription_id: ProviderSubscriptionId,
) -> Subscription | None:
    sql = """
SELECT *
FROM sub_subscriptions AS subscriptions
WHERE subscriptions.provider_id = %(provider_id)s
  AND subscriptions.provider_merchant_id = %(provider_merchant_id)s
  AND subscriptions.provider_subscription_id = %(provider_subscription_id)s
"""
    rows = await execute(
        sql,
        {
            "provider_id": provider_id,
            "provider_merchant_id": provider_merchant_id,
            "provider_subscription_id": provider_subscription_id,
        },
    )

    if not rows:
        return None

    return row_to_subscription(rows[0])


async def upsert_subscription(execute: ExecuteType, subscription: Subscription) -> None:
    sql = """
    INSERT INTO sub_subscriptions (
        provider_id,
        provider_merchant_id,
        provider_subscription_id,
        user_id,
        provider_customer_id,
        status,
        provider_status,
        started_at,
        renews_at,
        ends_at,
        provider_updated_at
    )
    VALUES (
        %(provider_id)s,
        %(provider_merchant_id)s,
        %(provider_subscription_id)s,
        %(user_id)s,
        %(provider_customer_id)s,
        %(status)s,
        %(provider_status)s,
        %(started_at)s,
        %(renews_at)s,
        %(ends_at)s,
        %(provider_updated_at)s
    )
    ON CONFLICT (
        provider_id,
        provider_merchant_id,
        provider_subscription_id
    )
    DO UPDATE SET
        status = EXCLUDED.status,
        provider_status = EXCLUDED.provider_status,
        started_at = EXCLUDED.started_at,
        renews_at = EXCLUDED.renews_at,
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
FROM sub_subscriptions AS subscriptions
WHERE subscriptions.user_id = ANY(%(user_ids)s)
  AND (
      %(statuses)s::smallint[] IS NULL
      OR subscriptions.status = ANY(%(statuses)s::smallint[])
  )
ORDER BY
    subscriptions.user_id,
    subscriptions.started_at DESC,
    subscriptions.provider_id,
    subscriptions.provider_merchant_id,
    subscriptions.provider_subscription_id
"""
    rows = await execute(sql, {"user_ids": user_ids, "statuses": statuses})
    return [row_to_subscription(row) for row in rows]
