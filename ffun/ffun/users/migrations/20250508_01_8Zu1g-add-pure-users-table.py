"""
add pure users table
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230527_01_soIr3-users-mapping"}


sql_create_users_table = """
CREATE TABLE u_users (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_users_table)

    sql = """
        INSERT INTO u_users (id, created_at)
        SELECT internal_id, MIN(created_at)
        FROM u_mapping
        GROUP BY internal_id
    """

    cursor.execute(sql)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE u_users")


steps = [step(apply_step, rollback_step)]
