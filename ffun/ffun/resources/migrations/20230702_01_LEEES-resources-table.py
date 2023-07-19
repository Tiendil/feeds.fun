"""
resources-table
"""

from yoyo import step


__depends__ = {}

sql_create_table = """
CREATE TABLE r_resources (
    user_id UUID NOT NULL,
    kind INTEGER NOT NULL,
    interval_started_at TIMESTAMP WITH TIME ZONE NOT NULL,

    used BIGINT NOT NULL DEFAULT 0,
    reserved BIGINT NOT NULL DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    PRIMARY KEY (kind, user_id, interval_started_at)
)
"""


def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(sql_create_table)


def rollback_step(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE r_resources")


steps = [step(apply_step, rollback_step)]
