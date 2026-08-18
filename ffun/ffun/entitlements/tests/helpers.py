import datetime
from typing import cast

from ffun.core.postgresql import execute
from ffun.domain.entities import UserId
from ffun.entitlements import operations
from ffun.entitlements.entities import EntitlementKindId, SourceEntitlement


async def load_source_entitlement_timestamps(
    entitlement: SourceEntitlement,
) -> tuple[datetime.datetime, datetime.datetime]:
    arguments: dict[str, object] = {
        "user_id": entitlement.user_id,
        "kind_id": entitlement.kind_id,
        "source_id": entitlement.source_id,
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
              AND source_id = %(source_id)s
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
