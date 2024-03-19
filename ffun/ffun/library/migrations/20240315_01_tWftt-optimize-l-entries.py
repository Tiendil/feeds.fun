"""
optimize_l_entries
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230514_01_Bwb35-processed-state"}


sql_remove_column = """
ALTER TABLE l_entries DROP COLUMN cataloged_at;
"""

sql_return_column = """
ALTER TABLE l_entries ADD COLUMN cataloged_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
"""

sql_return_column_values = """
UPDATE l_entries
SET cataloged_at = created_at;
"""

sql_return_not_null = """
ALTER TABLE l_entries ALTER COLUMN cataloged_at SET NOT NULL;
"""

sql_create_index = """
CREATE INDEX idx_l_entries_created_at_feed_id ON l_entries (created_at, feed_id);
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(sql_remove_column)
    cursor.execute(sql_create_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("DROP INDEX idx_l_entries_created_at_feed_id")

    cursor.execute(sql_return_column)
    cursor.execute(sql_return_column_values)
    cursor.execute(sql_return_not_null)


steps = [step(apply_step, rollback_step)]
