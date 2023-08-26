from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_feeds_table = """
CREATE TABLE f_feeds (
    id UUID PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    state INTEGER NOT NULL,
    last_error INTEGER NULL DEFAULT NULL,
    loaded_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NULL,
    load_attempted_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
"""

sql_create_load_attempted_at_index = """
CREATE INDEX idx_f_feeds_load_attempted_at_at ON f_feeds (load_attempted_at);
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_feeds_table)
    cursor.execute(sql_create_load_attempted_at_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE f_feeds")


steps = [step(apply_step, rollback_step)]
