"""
users-mapping
"""
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_user_mapping_table = """
CREATE TABLE u_mapping (
    external_id TEXT NOT NULL,
    internal_id UUID NOT NULL,
    service_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (service_id, external_id)
);
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_user_mapping_table)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE u_mapping")


steps = [step(apply_step, rollback_step)]
