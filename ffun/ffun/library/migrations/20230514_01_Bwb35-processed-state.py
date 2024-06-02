"""
processed-state
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230427_01_pv33u-fix-entries-unique-index"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE l_entry_process_info ADD COLUMN state SMALLINT NOT NULL DEFAULT 1")
    cursor.execute("ALTER TABLE l_entry_process_info ADD last_error TEXT")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE l_entry_process_info DROP COLUMN state")
    cursor.execute("ALTER TABLE l_entry_process_info DROP COLUMN last_error")


steps = [step(apply_step, rollback_step)]
