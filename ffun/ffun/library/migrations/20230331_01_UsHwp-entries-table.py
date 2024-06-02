"""
entries_table
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_entries_table = """
CREATE TABLE l_entries (
    id UUID PRIMARY KEY,
    feed_id UUID NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    external_id TEXT NOT NULL UNIQUE,
    external_url TEXT NOT NULL,
    external_tags TEXT[] NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cataloged_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
)
"""


sql_create_feeds_index = """
CREATE INDEX idx_l_entries_feed_id ON l_entries (feed_id);
"""


sql_create_entry_process_info_table = """
CREATE TABLE l_entry_process_info (
    entry_id UUID NOT NULL REFERENCES l_entries (id),
    processor_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE NULL,

    PRIMARY KEY (processor_id, entry_id)
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_entries_table)
    cursor.execute(sql_create_feeds_index)
    cursor.execute(sql_create_entry_process_info_table)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE l_entries, l_entry_process_info")


steps = [step(apply_step, rollback_step)]
