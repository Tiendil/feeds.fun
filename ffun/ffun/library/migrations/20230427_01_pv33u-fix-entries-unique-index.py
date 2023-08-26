"""
fix-entries-unique-index
"""
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230331_01_UsHwp-entries-table"}

constraint = "l_entries_external_id_key"
index = "l_entries_feed_id_external_id_key"
unnecessary_index = "idx_l_entries_feed_id"

# we must controll unique constraint on entries by pair feed + id because
# 1. we can not guarantee that there will be no duplicates of feeds
#    (can not guarantee perfect normalization of urls, etc)
# 2. someone can damage database by infecting with wrong entries from faked feed


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(f"ALTER TABLE l_entries DROP CONSTRAINT {constraint}")
    cursor.execute(f"CREATE INDEX {index} ON l_entries (feed_id, external_id)")
    cursor.execute(f"DROP INDEX {unnecessary_index}")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE l_entry_process_info, l_entries")
    cursor.execute(f"ALTER TABLE l_entries ADD CONSTRAINT {constraint} UNIQUE (external_id)")
    cursor.execute(f"DROP INDEX {index}")
    cursor.execute(f"CREATE INDEX {unnecessary_index} ON l_entries (feed_id)")


steps = [step(apply_step, rollback_step)]
