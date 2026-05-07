import time
from collections.abc import Sequence

from psycopg.types.json import Jsonb

from ffun.core.postgresql import execute
from ffun.queues.entities import (
    DEFAULT_SECONDARY_ID,
    BaseQueueItem,
    QueueItemT,
    QueueKind,
    QueueRecord,
    QueueRecordId,
)
from ffun.queues.settings import settings


def row_to_queue_record(row: dict[str, object], item_type: type[QueueItemT]) -> QueueRecord[QueueItemT]:
    return QueueRecord(
        id=row["id"],  # type: ignore[arg-type]
        primary_id=QueueKind(row["primary_id"]),  # type: ignore[arg-type]
        secondary_id=row["secondary_id"],  # type: ignore[arg-type]
        priority=row["priority"],  # type: ignore[arg-type]
        freezed_till=row["freezed_till"],  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
        item=item_type.from_queue(row["payload"]),  # type: ignore[arg-type]
    )


async def push(
    primary_id: QueueKind,
    items: Sequence[BaseQueueItem],
    secondary_id: int = DEFAULT_SECONDARY_ID,
    priority: int | None = None,
) -> None:
    if not items:
        return

    if priority is None:
        priority = time.time_ns()

    sql = """
    WITH payloads AS (
        SELECT payload
        FROM jsonb_array_elements(%(payloads)s::jsonb) AS payload
    )
    INSERT INTO q_items (primary_id, secondary_id, priority, payload)
    SELECT
        %(primary_id)s,
        %(secondary_id)s,
        %(priority)s,
        payload
    FROM payloads
    """

    await execute(
        sql,
        {
            "primary_id": primary_id,
            "secondary_id": secondary_id,
            "priority": priority,
            "payloads": Jsonb([item.to_queue() for item in items]),
        },
    )


async def pull(
    primary_id: QueueKind,
    item_type: type[QueueItemT],
    limit: int,
    secondary_id: int = DEFAULT_SECONDARY_ID,
) -> list[QueueRecord[QueueItemT]]:
    if limit <= 0:
        return []

    sql = """
    WITH next_items AS (
        SELECT id
        FROM q_items
        WHERE primary_id = %(primary_id)s
          AND secondary_id = %(secondary_id)s
          AND freezed_till <= CURRENT_TIMESTAMP
        ORDER BY priority ASC, created_at ASC, id ASC
        LIMIT %(limit)s
        FOR UPDATE SKIP LOCKED
    )
    UPDATE q_items AS queue_item
    SET freezed_till = CURRENT_TIMESTAMP + %(freezing_delay)s,
        updated_at = CURRENT_TIMESTAMP
    FROM next_items
    WHERE queue_item.id = next_items.id
    RETURNING queue_item.*
    """

    rows = await execute(
        sql,
        {
            "primary_id": primary_id,
            "secondary_id": secondary_id,
            "limit": limit,
            "freezing_delay": settings.freezing_delay,
        },
    )

    records = [row_to_queue_record(row, item_type) for row in rows]

    return sorted(records, key=lambda record: (record.priority, record.created_at, record.id))


async def acknowledge(record_ids: Sequence[QueueRecordId]) -> int:
    if not record_ids:
        return 0

    sql = """
    DELETE FROM q_items
    WHERE id = ANY(%(record_ids)s)
    RETURNING id
    """

    rows = await execute(sql, {"record_ids": list(record_ids)})

    return len(rows)


async def queues_stats() -> dict[tuple[int, int], int]:
    sql = """
    SELECT primary_id, secondary_id, COUNT(*) AS count
    FROM q_items
    GROUP BY primary_id, secondary_id
    ORDER BY primary_id, secondary_id
    """

    rows: list[dict[str, object]] = await execute(sql)

    stats: dict[tuple[int, int], int] = {}

    for row in rows:
        stats[(row["primary_id"], row["secondary_id"])] = row["count"]  # type: ignore

    return stats


async def tech_get_queue_records(
    primary_id: QueueKind,
    item_type: type[QueueItemT],
    secondary_id: int = DEFAULT_SECONDARY_ID,
    limit: int = 1000,
) -> list[QueueRecord[QueueItemT]]:
    sql = """
    SELECT *
    FROM q_items
    WHERE primary_id = %(primary_id)s
      AND secondary_id = %(secondary_id)s
    ORDER BY priority ASC, created_at ASC, id ASC
    LIMIT %(limit)s
    """

    rows = await execute(sql, {"primary_id": primary_id, "secondary_id": secondary_id, "limit": limit})

    return [row_to_queue_record(row, item_type) for row in rows]


async def tech_clear_queue(primary_id: QueueKind, secondary_id: int | None = None) -> None:
    if secondary_id is None:
        sql = """
        DELETE FROM q_items
        WHERE primary_id = %(primary_id)s
        """
        await execute(sql, {"primary_id": primary_id})
        return

    sql = """
    DELETE FROM q_items
    WHERE primary_id = %(primary_id)s
      AND secondary_id = %(secondary_id)s
    """

    await execute(sql, {"primary_id": primary_id, "secondary_id": secondary_id})
