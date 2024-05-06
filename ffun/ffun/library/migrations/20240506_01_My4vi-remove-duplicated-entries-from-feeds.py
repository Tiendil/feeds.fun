"""
remove-duplicated-entries-from-feeds
"""
import uuid
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from yoyo import step


__depends__ = {'20240503_01_Bmzw6-remove-l-entry-process-info'}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor(row_factory=dict_row)

    sql = 'SELECT feed_id, external_id FROM l_entries GROUP BY feed_id, external_id HAVING count(*) > 1'

    cursor.execute(sql)

    saved_ids: dict[tuple[uuid.UUID, uuid.UUID], uuid.UUID] = {}
    ids_to_remove = []

    for row in cursor.fetchall():
        feed_id = row['feed_id']
        external_id = row['external_id']

        key = (feed_id, external_id)

        if key not in saved_ids:
            saved_ids[key] = row['id']
            continue

        ids_to_remove.append(row['id'])

    sql = 'DELETE FROM l_entries WHERE id = ANY(%(ids)s)'

    cursor.execute(sql, {'ids': ids_to_remove})


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    pass


steps = [step(apply_step, rollback_step)]
