"""
updated-at-field
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230417_01_0XYOQ-scores-tables"}

sql = """
ALTER TABLE s_rules
ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    sql = """
    ALTER TABLE s_rules
    DROP COLUMN updated_at
    """

    cursor.execute(sql)


steps = [step(apply_step, rollback_step)]
