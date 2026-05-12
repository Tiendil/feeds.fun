"""
add_persistent_queues
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_queue_items = """
CREATE TABLE q_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primary_id INTEGER NOT NULL,
    secondary_id INTEGER NOT NULL,
    priority BIGINT NOT NULL,
    payload JSONB NOT NULL,
    freezed_till TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

# id: excluded because it is only a deterministic tie-breaker, not a primary lookup key.
# created_at: excluded because priority stores the queue ordering value.
# freezed_till: excluded because it changes on every pull and would add index churn.
sql_create_queue_items_primary_id_secondary_id_priority_index = """
CREATE INDEX q_items_primary_id_secondary_id_priority_idx
ON q_items (primary_id, secondary_id, priority)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(sql_create_queue_items)
    cursor.execute(sql_create_queue_items_primary_id_secondary_id_priority_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("DROP TABLE q_items")


steps = [step(apply_step, rollback_step)]
