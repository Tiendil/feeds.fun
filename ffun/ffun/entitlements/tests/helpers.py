import datetime
import uuid
from collections.abc import Callable
from typing import cast

from ffun.audit.entities import AuditEntityKind
from ffun.core.postgresql import ExecuteType, execute, transaction
from ffun.domain.entities import BenefitTransactionId, SerializedId, UserId
from ffun.entitlements import domain
from ffun.entitlements import entities as entitlement_entities
from ffun.entitlements import operations
from ffun.entitlements.entities import EntitlementKindId, SourceEntitlement

_REVOKING_TRANSACTION_ID = BenefitTransactionId(uuid.UUID(int=2))
_ACTOR_KIND = AuditEntityKind.admin
_ACTOR_ID = SerializedId("test-admin")


async def _grant(
    source_entitlement: SourceEntitlement,
    *,
    evaluation_time: datetime.datetime | None = None,
    emit_event: bool = True,
) -> tuple[entitlement_entities.SourceEntitlementChange, Callable[[], None]]:
    if evaluation_time is None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

    async with transaction() as transaction_execute:
        outcome, callback = await domain.grant_source_entitlement(
            transaction_execute,
            source_entitlement,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

    if emit_event:
        callback()

    return outcome, callback


async def _revoke(
    source_entitlement: SourceEntitlement,
    *,
    revoked_by_transaction_id: BenefitTransactionId = _REVOKING_TRANSACTION_ID,
    evaluation_time: datetime.datetime | None = None,
    emit_event: bool = True,
) -> tuple[entitlement_entities.SourceEntitlementChange, Callable[[], None]]:
    if evaluation_time is None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

    async with transaction() as transaction_execute:
        outcome, callback = await domain.revoke_source_entitlement(
            transaction_execute,
            grant_transaction_id=source_entitlement.grant_transaction_id,
            revoked_by_transaction_id=revoked_by_transaction_id,
            user_id=source_entitlement.user_id,
            kind_id=source_entitlement.kind_id,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

    if emit_event:
        callback()

    return outcome, callback


async def load_source_entitlement(
    execute: ExecuteType,
    user_id: UserId,
    kind_id: EntitlementKindId,
    grant_transaction_id: BenefitTransactionId,
) -> SourceEntitlement | None:
    return await operations.load_source_entitlement(
        execute,
        user_id,
        kind_id,
        grant_transaction_id,
    )


async def load_source_entitlement_timestamps(
    entitlement: SourceEntitlement,
) -> tuple[datetime.datetime, datetime.datetime]:
    arguments: dict[str, object] = {
        "user_id": entitlement.user_id,
        "kind_id": entitlement.kind_id,
        "grant_transaction_id": entitlement.grant_transaction_id,
    }
    rows = cast(
        list[dict[str, datetime.datetime]],
        await execute(
            """
            SELECT created_at, updated_at
            FROM en_source_entitlements
            WHERE user_id = %(user_id)s
              AND kind_id = %(kind_id)s
              AND grant_transaction_id = %(grant_transaction_id)s
            """,
            arguments,
        ),
    )
    assert len(rows) == 1
    return rows[0]["created_at"], rows[0]["updated_at"]


async def load_effective_interval_timestamps(
    user_id: UserId,
    kind_id: EntitlementKindId,
) -> list[tuple[datetime.datetime, datetime.datetime]]:
    arguments: dict[str, object] = {"user_id": user_id, "kind_id": kind_id}
    rows = cast(
        list[dict[str, datetime.datetime]],
        await execute(
            """
            SELECT created_at, updated_at
            FROM en_entitlements
            WHERE user_id = %(user_id)s AND kind_id = %(kind_id)s
            ORDER BY starts_at
            """,
            arguments,
        ),
    )
    return [(row["created_at"], row["updated_at"]) for row in rows]


async def clear_effective_intervals() -> None:
    await operations.delete_expired_effective_intervals(
        execute,
        datetime.datetime.max.replace(tzinfo=datetime.UTC),
    )
