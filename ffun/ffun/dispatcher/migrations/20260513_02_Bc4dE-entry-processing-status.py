"""
entry-processing-status
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_entry_processing_status = """
CREATE TABLE d_entry_processing_status (
    entry_id UUID NOT NULL,
    processor_id INTEGER NOT NULL,
    status INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (entry_id, processor_id)
)
"""

sql_create_entry_processing_status_processor_id_status_index = """
CREATE INDEX d_entry_processing_status_processor_id_status_idx
ON d_entry_processing_status (processor_id, status)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(sql_create_entry_processing_status)
    cursor.execute(sql_create_entry_processing_status_processor_id_status_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("DROP TABLE d_entry_processing_status")


steps = [step(apply_step, rollback_step)]
