"""
resource statistics
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240909_01_XxByn-replace-tokens-traking-with-costs-tracking"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE r_statistics (
            user_id UUID NOT NULL,
            kind INTEGER NOT NULL,
            date DATE NOT NULL,

            consumed BIGINT NOT NULL DEFAULT 0,

            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (user_id, kind, date)
        )
        """
    )


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE r_statistics")


steps = [step(apply_step, rollback_step)]
