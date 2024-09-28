"""
source-table
"""

from yoyo import step

from typing import Any

from psycopg import Connection
from yoyo import step


__depends__ = {'20240512_01_jL7Mt-turn-on-unique-uids'}


# TODO: test on production data


# TODO: sync with actual implementation
def url_to_source_uid(url: str) -> str:
    return url


sql_sources_table = """
CREATE TABLE f_sources (
    id UUID PRIMARY KEY,
    uid TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(sql_sources_table)

    cursor.execute("ALTER TABLE f_feeds ADD COLUMN source_id UUID REFERENCES f_sources (id) NULL")

    cursor.execute("SELECT * from f_feeds")

    result = cursor.fetchall()

    for row in result:
        source_uid = url_to_source_uid(row["url"])

        cursor.execute("INSERT INTO f_sources (id, uid) VALUES (gen_random_uuid(), %(uid)s) ON CONFLICT DO NOTHING",
                       {"uid": source_uid})

        cursor.execute("""UPDATE f_feeds
                          SET source_id = (SELECT id FROM f_sources WHERE uid = %(source_uid)s)
                          WHERE id = %(feed_id)s""",
                       {"source_uid": source_uid,
                        "feed_id": row["id"]})

    cursor.execute("ALTER TABLE f_entries ALTER COLUMN source_id SET NOT NULL")


# TODO: restore lost indexes if any
def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE f_feeds DROP COLUMN source_id")
    cursor.execute("DROP TABLE f_sources")


steps = [step(apply_step, rollback_step)]
