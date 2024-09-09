"""
replace tokens traking with costs tracking
"""

import datetime
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from yoyo import step

__depends__ = {"20230702_01_LEEES-resources-table"}


def month_interval_start() -> datetime.datetime:
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


sql = """
INSERT INTO r_resources (user_id, kind, interval_started_at, used, reserved)
VALUES (%(user_id)s, 2, %(interval_started_at)s, %(used)s, %(reserved)s)
"""


k = 1_000_000_000
cost_1m = 0.6


def tokens_to_points(tokens: int) -> int:
    return int((tokens / 1_000_000 * cost_1m) * k)


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor(row_factory=dict_row)

    interval = month_interval_start()

    cursor.execute(
        "SELECT * FROM r_resources WHERE kind=1 AND interval_started_at=%(interval)s", {"interval": interval}
    )

    for row in cursor.fetchall():
        cursor.execute(
            sql,
            {
                "user_id": row["user_id"],
                "interval_started_at": row["interval_started_at"],
                "used": tokens_to_points(row["used"]),
                "reserved": tokens_to_points(row["reserved"]),
            },
        )

    cursor.execute("DELETE FROM r_resources WHERE kind=1")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    pass


steps = [step(apply_step, rollback_step)]
