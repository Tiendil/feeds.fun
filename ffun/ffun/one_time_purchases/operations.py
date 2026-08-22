import uuid
from collections.abc import Mapping
from typing import cast

from pydantic import ValidationError

from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import OneTimePurchaseId, ProviderObjectReference, UserId
from ffun.one_time_purchases import errors
from ffun.one_time_purchases.entities import Purchase, PurchaseStatus


def new_purchase_id() -> OneTimePurchaseId:
    return OneTimePurchaseId(uuid.uuid4())


def row_to_purchase(row: Mapping[str, object]) -> Purchase:
    data = dict(row)
    data.pop("created_at", None)
    data.pop("updated_at", None)

    try:
        return Purchase.model_validate(data)
    except ValidationError as exception:
        raise errors.InvalidStoredPurchase() from exception


async def load_purchase(
    execute: ExecuteType,
    one_time_purchase_id: OneTimePurchaseId,
) -> Purchase | None:
    sql = """
SELECT *
FROM otp_purchases AS purchases
WHERE purchases.id = %(one_time_purchase_id)s
"""
    rows = await execute(sql, {"one_time_purchase_id": one_time_purchase_id})

    if not rows:
        return None

    return row_to_purchase(rows[0])


async def load_provider_purchase_reference(
    execute: ExecuteType,
    reference: ProviderObjectReference,
) -> OneTimePurchaseId | None:
    sql = """
    SELECT one_time_purchase_id
    FROM otp_purchase_refs
    WHERE provider_id = %(provider_id)s
      AND provider_account_id = %(provider_account_id)s
      AND provider_object_id = %(provider_object_id)s
    """
    rows = await execute(sql, reference.model_dump())

    if not rows:
        return None

    return cast(OneTimePurchaseId, rows[0]["one_time_purchase_id"])


async def insert_provider_purchase_reference(
    execute: ExecuteType,
    reference: ProviderObjectReference,
    *,
    one_time_purchase_id: OneTimePurchaseId,
) -> None:
    sql = """
    INSERT INTO otp_purchase_refs (
        provider_id,
        provider_account_id,
        provider_object_id,
        one_time_purchase_id
    )
    VALUES (
        %(provider_id)s,
        %(provider_account_id)s,
        %(provider_object_id)s,
        %(one_time_purchase_id)s
    )
    ON CONFLICT DO NOTHING
    RETURNING one_time_purchase_id
    """
    rows = await execute(
        sql,
        {**reference.model_dump(), "one_time_purchase_id": one_time_purchase_id},
    )

    if rows:
        return

    stored_purchase_id = await load_provider_purchase_reference(execute, reference)

    if stored_purchase_id == one_time_purchase_id:
        return

    raise errors.ProviderPurchaseReferenceConflict(
        provider_id=reference.provider_id,
        provider_account_id=reference.provider_account_id,
        provider_object_id=reference.provider_object_id,
        stored_purchase_id=(str(stored_purchase_id) if stored_purchase_id is not None else None),
        requested_purchase_id=str(one_time_purchase_id),
    )


async def save_purchase(execute: ExecuteType, purchase: Purchase) -> None:
    sql = """
    INSERT INTO otp_purchases (
        id,
        state_transaction_id,
        user_id,
        benefit_id,
        status,
        provider_status,
        purchased_at,
        provider_updated_at
    )
    VALUES (
        %(id)s,
        %(state_transaction_id)s,
        %(user_id)s,
        %(benefit_id)s,
        %(status)s,
        %(provider_status)s,
        %(purchased_at)s,
        %(provider_updated_at)s
    )
    ON CONFLICT (id)
    DO UPDATE SET
        state_transaction_id = EXCLUDED.state_transaction_id,
        status = EXCLUDED.status,
        provider_status = EXCLUDED.provider_status,
        purchased_at = EXCLUDED.purchased_at,
        provider_updated_at = EXCLUDED.provider_updated_at,
        updated_at = CURRENT_TIMESTAMP
    """
    await execute(sql, purchase.model_dump())


async def load_purchases(
    execute: ExecuteType,
    user_id: UserId,
    *,
    statuses: list[PurchaseStatus] | None = None,
) -> list[Purchase]:
    if statuses == []:
        return []

    sql = """
SELECT *
FROM otp_purchases AS purchases
WHERE purchases.user_id = %(user_id)s
  AND (
      %(statuses)s::smallint[] IS NULL
      OR purchases.status = ANY(%(statuses)s::smallint[])
  )
ORDER BY
    purchases.purchased_at DESC,
    purchases.id
"""
    rows = await execute(sql, {"user_id": user_id, "statuses": statuses})
    return [row_to_purchase(row) for row in rows]
