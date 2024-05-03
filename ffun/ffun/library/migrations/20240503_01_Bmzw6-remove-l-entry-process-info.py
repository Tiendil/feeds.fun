"""
remove-l-entry-process-info
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240315_01_tWftt-optimize-l-entries", "20240319_01_MTJyn-migrate-to-processors-queue"}


sql_create_entry_process_info_table = """
CREATE TABLE l_entry_process_info (
    entry_id UUID NOT NULL REFERENCES l_entries (id),
    processor_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE NULL,
    state SMALLINT NOT NULL DEFAULT 1,
    last_error TEXT,

    PRIMARY KEY (processor_id, entry_id)
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE l_entry_process_info")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_entry_process_info_table)


steps = [step(apply_step, rollback_step)]
