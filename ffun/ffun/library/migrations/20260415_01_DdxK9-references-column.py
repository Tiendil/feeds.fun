"""
references-column
"""
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {'20260317_01_2OzYo-ingested-time-for-entries'}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    # `references` is a reserved keyword in SQL -> use `refs` instead
    cursor.execute("ALTER TABLE l_entries ADD COLUMN refs JSONB NOT NULL DEFAULT '[]'::jsonb")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE l_entries DROP COLUMN refs")



steps = [step(apply_step, rollback_step)]
