"""
entry-dispatching-status
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20260513_02_Bc4dE-entry-processing-status"}


sql_create_entry_dispatching_status = """
CREATE TABLE d_entry_dispatching_status (
    entry_id UUID NOT NULL,
    resources_consumed BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (entry_id)
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(sql_create_entry_dispatching_status)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("DROP TABLE d_entry_dispatching_status")


steps = [step(apply_step, rollback_step)]
