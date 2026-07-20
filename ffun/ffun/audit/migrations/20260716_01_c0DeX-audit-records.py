"""
audit-records
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_audit_records = """
-- Append-only durable records of audited business changes and events.
CREATE TABLE a_records (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event TEXT NOT NULL,
    actor_kind SMALLINT NOT NULL,
    actor_id TEXT NOT NULL,
    subject_kind SMALLINT NOT NULL,
    subject_id TEXT NOT NULL,
    attributes JSONB NOT NULL
)
"""


sql_create_audit_records_subject_index = """
CREATE INDEX a_records_subject_kind_subject_id_created_at_id_idx
ON a_records (subject_kind, subject_id, created_at, id)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_audit_records)
    cursor.execute(sql_create_audit_records_subject_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE a_records")


steps = [step(apply_step, rollback_step)]
