"""
source-table
"""

import re
import unicodedata
from typing import Any

from furl import furl
from psycopg import Connection
from psycopg.rows import dict_row
from yoyo import step

__depends__ = {"20240512_01_jL7Mt-turn-on-unique-uids", "20230427_01_9HuHj-add-feeds-links"}


RE_SCHEMA = re.compile(r"^(\w+):")


def _fake_schema_for_url(url: str) -> str:
    url = url.strip()

    if url.startswith("//"):
        return url

    if RE_SCHEMA.match(url):
        return url

    if "." not in url.split("/")[0]:
        return url

    return f"//{url}"


def url_to_source_uid(url: str) -> str:
    normalized_url = unicodedata.normalize("NFC", url).lower().strip()

    normalized_url = _fake_schema_for_url(normalized_url)

    url_object = furl(normalized_url)

    domain = url_object.host

    if domain.startswith("www."):
        domain = domain[4:]

    if domain.endswith(".reddit.com"):
        domain = "reddit.com"

    assert isinstance(domain, str)

    return domain


sql_sources_table = """
CREATE TABLE f_sources (
    id UUID PRIMARY KEY,
    uid TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor(row_factory=dict_row)

    ####################################
    # cleaning up feeds from broken urls
    cursor.execute("SELECT id FROM f_feeds WHERE url NOT LIKE 'http%'")
    result = cursor.fetchall()
    feed_ids = [row["id"] for row in result]
    cursor.execute("DELETE FROM fl_links WHERE feed_id = ANY(%(feed_ids)s)", {"feed_ids": feed_ids})
    cursor.execute("DELETE FROM f_feeds WHERE id = ANY(%(feed_ids)s)", {"feed_ids": feed_ids})
    ####################################

    cursor.execute(sql_sources_table)

    cursor.execute("ALTER TABLE f_feeds ADD COLUMN source_id UUID REFERENCES f_sources (id) NULL")

    cursor.execute("SELECT * from f_feeds")

    result = cursor.fetchall()

    for row in result:
        source_uid = url_to_source_uid(row["url"])

        cursor.execute(
            "INSERT INTO f_sources (id, uid) VALUES (gen_random_uuid(), %(uid)s) ON CONFLICT DO NOTHING",
            {"uid": source_uid},
        )

        cursor.execute(
            """UPDATE f_feeds
                          SET source_id = (SELECT id FROM f_sources WHERE uid = %(source_uid)s)
                          WHERE id = %(feed_id)s""",
            {"source_uid": source_uid, "feed_id": row["id"]},
        )

    cursor.execute("ALTER TABLE f_feeds ALTER COLUMN source_id SET NOT NULL")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE f_feeds DROP COLUMN source_id")
    cursor.execute("DROP TABLE f_sources")


steps = [step(apply_step, rollback_step)]
