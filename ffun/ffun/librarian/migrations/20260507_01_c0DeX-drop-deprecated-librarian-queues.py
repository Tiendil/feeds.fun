"""
drop_deprecated_librarian_queues
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240319_01_MTJyn-migrate-to-processors-queue", "20260506_01_Hs7pQ-add-persistent-queues"}


sql_create_processor_pointers = """
CREATE TABLE ln_processor_pointers (
    processor_id INTEGER PRIMARY KEY,
    pointer_created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT '1970-01-01 00:00:00',
    pointer_entry_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

sql_create_processors_queue = """
CREATE TABLE ln_processors_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processor_id INTEGER NOT NULL,
    entry_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (processor_id, entry_id)
)
"""

sql_create_processors_queue_index = """
CREATE INDEX idx_ln_processors_queue_processor_id_created_at ON ln_processors_queue (processor_id, created_at)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("DROP TABLE ln_processor_pointers, ln_processors_queue")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(sql_create_processor_pointers)
    cursor.execute(sql_create_processors_queue)
    cursor.execute(sql_create_processors_queue_index)


steps = [step(apply_step, rollback_step)]
