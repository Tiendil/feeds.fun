"""
replace tokens traking with costs tracking
"""

from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from yoyo import step

__depends__ = {"20230911_01_5vjXI-index-to-search-by-value"}

sql = """
INSERT INTO us_settings (user_id, kind, value)
VALUES (%(user_id)s, 6, %(value)s)
"""


cost_1m = 0.6


def tokens_to_costs(tokens: int) -> int:
    return int(tokens / 1_000_000 * cost_1m)


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor(row_factory=dict_row)

    cursor.execute("SELECT * FROM us_settings WHERE kind=2")

    for row in cursor.fetchall():

        cursor.execute(
            sql,
            {
                "user_id": row["user_id"],
                "value": tokens_to_costs(int(row["value"])),
            },
        )

    cursor.execute("DELETE FROM us_settings WHERE kind=2")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    pass


steps = [step(apply_step, rollback_step)]
