"""
markers-tables
"""
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()

sql_create_markers_table = """
CREATE TABLE m_markers (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    marker SMALLINT NOT NULL,
    entry_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
)
"""

sql_users_markers_index = """
CREATE UNIQUE INDEX idx_m_markers_user_id_marker_entry_id ON m_markers (user_id, entry_id, marker);
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_markers_table)
    cursor.execute(sql_users_markers_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE m_markers")


steps = [step(apply_step, rollback_step)]
