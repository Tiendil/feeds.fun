import datetime
from collections.abc import Mapping
from typing import Any

import psycopg
from pydantic import ValidationError
from pypika import Parameter, PostgreSQLQuery

from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import BenefitTransactionId, SubscriptionId, UserId
from ffun.entitlements import errors
from ffun.entitlements.entities import (
    EffectiveEntitlementInterval,
    EntitlementKindId,
    EntitlementSourceId,
    SourceEntitlement,
)


def row_to_source_entitlement(row: Mapping[str, object]) -> SourceEntitlement:
    data = dict(row)
    data.pop("created_at", None)
    data.pop("updated_at", None)

    try:
        return SourceEntitlement.model_validate(data)
    except ValidationError as exception:
        raise errors.InvalidStoredEntitlement(entity_kind="source_entitlement") from exception


def row_to_effective_interval(row: Mapping[str, object]) -> EffectiveEntitlementInterval:
    try:
        return EffectiveEntitlementInterval.model_validate(row)
    except ValidationError as exception:
        raise errors.InvalidStoredEntitlement(entity_kind="effective_entitlement_interval") from exception


async def load_source_entitlement(
    execute: ExecuteType,
    user_id: UserId,
    kind_id: EntitlementKindId,
    source_id: EntitlementSourceId,
    grant_transaction_id: BenefitTransactionId,
) -> SourceEntitlement | None:
    sql = """
    SELECT *
    FROM en_source_entitlements
    WHERE user_id = %(user_id)s
      AND kind_id = %(kind_id)s
      AND source_id = %(source_id)s
      AND grant_transaction_id = %(grant_transaction_id)s
    """

    rows = await execute(
        sql,
        {
            "user_id": user_id,
            "kind_id": kind_id,
            "source_id": source_id,
            "grant_transaction_id": grant_transaction_id,
        },
    )

    if not rows:
        return None

    return row_to_source_entitlement(rows[0])


async def insert_source_entitlement(execute: ExecuteType, entitlement: SourceEntitlement) -> None:
    sql = """
    INSERT INTO en_source_entitlements (
        source_id,
        grant_transaction_id,
        user_id,
        subscription_id,
        kind_id,
        value,
        starts_at,
        expires_at,
        revoked_at,
        revoked_by_transaction_id
    )
    VALUES (
        %(source_id)s,
        %(grant_transaction_id)s,
        %(user_id)s,
        %(subscription_id)s,
        %(kind_id)s,
        %(value)s,
        %(starts_at)s,
        %(expires_at)s,
        %(revoked_at)s,
        %(revoked_by_transaction_id)s
    )
    """

    try:
        await execute(
            sql,
            {
                "source_id": entitlement.source_id,
                "grant_transaction_id": entitlement.grant_transaction_id,
                "user_id": entitlement.user_id,
                "subscription_id": entitlement.subscription_id,
                "kind_id": entitlement.kind_id,
                "value": entitlement.value,
                "starts_at": entitlement.starts_at,
                "expires_at": entitlement.expires_at,
                "revoked_at": entitlement.revoked_at,
                "revoked_by_transaction_id": entitlement.revoked_by_transaction_id,
            },
        )
    except psycopg.errors.UniqueViolation as exception:
        raise errors.SourceEntitlementConflict(
            user_id=str(entitlement.user_id),
            kind_id=entitlement.kind_id,
            source_id=entitlement.source_id,
            grant_transaction_id=entitlement.grant_transaction_id,
        ) from exception


async def revoke_source_entitlement(
    execute: ExecuteType,
    entitlement: SourceEntitlement,
    *,
    revoked_at: datetime.datetime,
    revoked_by_transaction_id: BenefitTransactionId,
) -> SourceEntitlement:
    sql = """
    UPDATE en_source_entitlements
    SET revoked_at = %(revoked_at)s,
        revoked_by_transaction_id = %(revoked_by_transaction_id)s,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = %(user_id)s
      AND kind_id = %(kind_id)s
      AND source_id = %(source_id)s
      AND grant_transaction_id = %(grant_transaction_id)s
      AND (revoked_at IS NULL OR revoked_at > %(revoked_at)s)
    RETURNING *
    """

    rows = await execute(
        sql,
        {
            "user_id": entitlement.user_id,
            "kind_id": entitlement.kind_id,
            "source_id": entitlement.source_id,
            "grant_transaction_id": entitlement.grant_transaction_id,
            "revoked_at": revoked_at,
            "revoked_by_transaction_id": revoked_by_transaction_id,
        },
    )

    if not rows:
        raise errors.InvalidStoredEntitlement(
            entity_kind="source_entitlement",
            reason="Expected an unrevoked source entitlement to be updated",
        )

    return row_to_source_entitlement(rows[0])


async def load_source_entitlements_for_subscription(
    execute: ExecuteType,
    subscription_id: SubscriptionId,
    *,
    active_at: datetime.datetime,
) -> list[SourceEntitlement]:
    sql = """
    SELECT *
    FROM en_source_entitlements
    WHERE subscription_id = %(subscription_id)s
      AND starts_at <= %(active_at)s
      AND %(active_at)s < expires_at
      AND (revoked_at IS NULL OR %(active_at)s < revoked_at)
    ORDER BY kind_id, grant_transaction_id
    """
    rows = await execute(
        sql,
        {
            "subscription_id": subscription_id,
            "active_at": active_at,
        },
    )
    return [row_to_source_entitlement(row) for row in rows]


async def load_source_entitlements(
    execute: ExecuteType, user_id: UserId, kind_id: EntitlementKindId
) -> list[SourceEntitlement]:
    sql = """
    SELECT *
    FROM en_source_entitlements
    WHERE user_id = %(user_id)s
      AND kind_id = %(kind_id)s
    ORDER BY starts_at, expires_at, source_id, grant_transaction_id
    """

    rows = await execute(sql, {"user_id": user_id, "kind_id": kind_id})
    return [row_to_source_entitlement(row) for row in rows]


async def load_effective_intervals(
    execute: ExecuteType,
    user_id: UserId,
    kind_id: EntitlementKindId,
    *,
    ending_after: datetime.datetime,
) -> list[EffectiveEntitlementInterval]:
    sql = """
    SELECT user_id, kind_id, value, starts_at, expires_at
    FROM en_entitlements
    WHERE user_id = %(user_id)s
      AND kind_id = %(kind_id)s
      AND expires_at > %(ending_after)s
    ORDER BY starts_at
    """

    rows = await execute(
        sql,
        {"user_id": user_id, "kind_id": kind_id, "ending_after": ending_after},
    )
    return [row_to_effective_interval(row) for row in rows]


async def replace_effective_intervals(
    execute: ExecuteType,
    user_id: UserId,
    kind_id: EntitlementKindId,
    intervals: list[EffectiveEntitlementInterval],
) -> None:
    sql_delete = """
    DELETE FROM en_entitlements
    WHERE user_id = %(user_id)s
      AND kind_id = %(kind_id)s
    """

    await execute(sql_delete, {"user_id": user_id, "kind_id": kind_id})

    if not intervals:
        return

    query = PostgreSQLQuery.into("en_entitlements").columns("user_id", "kind_id", "value", "starts_at", "expires_at")
    arguments: dict[str, Any] = {}

    for index, interval in enumerate(intervals):
        arguments.update(
            {
                f"user_id_{index}": interval.user_id,
                f"kind_id_{index}": interval.kind_id,
                f"value_{index}": interval.value,
                f"starts_at_{index}": interval.starts_at,
                f"expires_at_{index}": interval.expires_at,
            }
        )
        query = query.insert(
            Parameter(f"%(user_id_{index})s"),
            Parameter(f"%(kind_id_{index})s"),
            Parameter(f"%(value_{index})s"),
            Parameter(f"%(starts_at_{index})s"),
            Parameter(f"%(expires_at_{index})s"),
        )

    await execute(str(query), arguments)


async def load_active_intervals(
    execute: ExecuteType,
    user_ids: list[UserId],
    kind_ids: list[EntitlementKindId],
    *,
    evaluation_time: datetime.datetime,
) -> list[EffectiveEntitlementInterval]:
    if not user_ids or not kind_ids:
        return []

    sql = """
    SELECT user_id, kind_id, value, starts_at, expires_at
    FROM en_entitlements
    WHERE user_id = ANY(%(user_ids)s)
      AND kind_id = ANY(%(kind_ids)s)
      AND starts_at <= %(evaluation_time)s
      AND %(evaluation_time)s < expires_at
    ORDER BY user_id, kind_id
    """

    rows = await execute(
        sql,
        {
            "user_ids": user_ids,
            "kind_ids": kind_ids,
            "evaluation_time": evaluation_time,
        },
    )
    return [row_to_effective_interval(row) for row in rows]


async def delete_expired_effective_intervals(execute: ExecuteType, cleanup_time: datetime.datetime) -> int:
    sql = """
    DELETE FROM en_entitlements
    WHERE expires_at <= %(cleanup_time)s
    RETURNING user_id
    """

    rows = await execute(sql, {"cleanup_time": cleanup_time})
    return len(rows)
