"""
settings-table
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()

sql_create_table = """
CREATE TABLE us_settings (
    user_id UUID NOT NULL,
    kind INTEGER NOT NULL,
    value TEXT NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    PRIMARY KEY (user_id, kind)
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_table)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE us_settings")


steps = [step(apply_step, rollback_step)]
