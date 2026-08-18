import uuid
from collections.abc import Mapping
from typing import cast

from pydantic import ValidationError

from ffun.benefits import errors
from ffun.benefits.entities import (
    BenefitSourceId,
    BenefitSourceTransactionId,
    BenefitTransaction,
    ProviderAccountId,
    ProviderId,
    ProviderSubscriptionId,
)
from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import BenefitTransactionId
from ffun.subscriptions.entities import SubscriptionId


def new_benefit_transaction_id() -> BenefitTransactionId:
    return BenefitTransactionId(uuid.uuid4())


def row_to_benefit_transaction(row: Mapping[str, object]) -> BenefitTransaction:
    data = dict(row)
    data.pop("created_at", None)

    try:
        return BenefitTransaction.model_validate(data)
    except ValidationError as exception:
        raise errors.InvalidStoredBenefitTransaction() from exception


async def insert_benefit_transaction(execute: ExecuteType, transaction: BenefitTransaction) -> bool:
    sql = """
    INSERT INTO b_transactions (
        id,
        source_id,
        source_transaction_id,
        kind,
        user_id,
        benefit_id,
        subscription_id,
        effective_at,
        starts_at,
        expires_at,
        revokes_transaction_id
    )
    VALUES (
        %(id)s,
        %(source_id)s,
        %(source_transaction_id)s,
        %(kind)s,
        %(user_id)s,
        %(benefit_id)s,
        %(subscription_id)s,
        %(effective_at)s,
        %(starts_at)s,
        %(expires_at)s,
        %(revokes_transaction_id)s
    )
    ON CONFLICT (source_id, source_transaction_id)
    DO NOTHING
    RETURNING id
    """
    rows = await execute(sql, transaction.model_dump())
    return bool(rows)


async def load_benefit_transaction(
    execute: ExecuteType,
    transaction_id: BenefitTransactionId,
) -> BenefitTransaction | None:
    sql = """
    SELECT *
    FROM b_transactions
    WHERE id = %(transaction_id)s
    """
    rows = await execute(sql, {"transaction_id": transaction_id})

    if not rows:
        return None

    return row_to_benefit_transaction(rows[0])


async def load_benefit_transaction_by_source(
    execute: ExecuteType,
    *,
    source_id: BenefitSourceId,
    source_transaction_id: BenefitSourceTransactionId,
) -> BenefitTransaction | None:
    sql = """
    SELECT *
    FROM b_transactions
    WHERE source_id = %(source_id)s
      AND source_transaction_id = %(source_transaction_id)s
    """
    rows = await execute(
        sql,
        {
            "source_id": source_id,
            "source_transaction_id": source_transaction_id,
        },
    )

    if not rows:
        return None

    return row_to_benefit_transaction(rows[0])


async def load_provider_subscription_reference(
    execute: ExecuteType,
    *,
    provider_id: ProviderId,
    provider_account_id: ProviderAccountId,
    provider_subscription_id: ProviderSubscriptionId,
) -> SubscriptionId | None:
    sql = """
    SELECT subscription_id
    FROM b_subscription_refs
    WHERE provider_id = %(provider_id)s
      AND provider_account_id = %(provider_account_id)s
      AND provider_subscription_id = %(provider_subscription_id)s
    """
    rows = await execute(
        sql,
        {
            "provider_id": provider_id,
            "provider_account_id": provider_account_id,
            "provider_subscription_id": provider_subscription_id,
        },
    )

    if not rows:
        return None

    return cast(SubscriptionId, rows[0]["subscription_id"])


async def insert_provider_subscription_reference(
    execute: ExecuteType,
    *,
    provider_id: ProviderId,
    provider_account_id: ProviderAccountId,
    provider_subscription_id: ProviderSubscriptionId,
    subscription_id: SubscriptionId,
) -> None:
    sql = """
    INSERT INTO b_subscription_refs (
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
    ON CONFLICT (provider_id, provider_account_id, provider_subscription_id)
    DO NOTHING
    RETURNING subscription_id
    """
    rows = await execute(
        sql,
        {
            "provider_id": provider_id,
            "provider_account_id": provider_account_id,
            "provider_subscription_id": provider_subscription_id,
            "subscription_id": subscription_id,
        },
    )

    if rows:
        return

    stored_subscription_id = await load_provider_subscription_reference(
        execute,
        provider_id=provider_id,
        provider_account_id=provider_account_id,
        provider_subscription_id=provider_subscription_id,
    )
    assert stored_subscription_id is not None

    if stored_subscription_id != subscription_id:
        raise errors.InvalidBenefitSubscription(
            reason="The external subscription already maps to another subscription"
        )
