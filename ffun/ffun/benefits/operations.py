import uuid
from collections.abc import Mapping

from pydantic import ValidationError

from ffun.benefits import errors
from ffun.benefits.entities import (
    BenefitSourceId,
    BenefitSourceTransactionId,
    BenefitTransaction,
)
from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import BenefitTransactionId


def new_benefit_transaction_id() -> BenefitTransactionId:
    return BenefitTransactionId(uuid.uuid4())


def row_to_benefit_transaction(row: Mapping[str, object]) -> BenefitTransaction:
    data = dict(row)
    data.pop("created_at", None)
    # TODO: BenefitTransaction cannot validate purchase targets yet; preserve this field when those entities exist.
    data.pop("one_time_purchase_id", None)

    try:
        return BenefitTransaction.model_validate(data)
    except ValidationError as exception:
        raise errors.InvalidStoredBenefitTransaction() from exception


async def save_benefit_transaction(execute: ExecuteType, transaction: BenefitTransaction) -> bool:
    sql = """
    INSERT INTO b_transactions (
        id,
        source_id,
        source_transaction_id,
        entitlement_action,
        user_id,
        benefit_id,
        subscription_id,
        one_time_purchase_id,
        effective_at,
        period_starts_at,
        period_ends_at
    )
    VALUES (
        %(id)s,
        %(source_id)s,
        %(source_transaction_id)s,
        %(entitlement_action)s,
        %(user_id)s,
        %(benefit_id)s,
        %(subscription_id)s,
        NULL,
        %(effective_at)s,
        %(period_starts_at)s,
        %(period_ends_at)s
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
