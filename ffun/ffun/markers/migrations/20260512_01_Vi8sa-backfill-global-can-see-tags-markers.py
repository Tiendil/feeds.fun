"""
backfill-global-can-see-tags-markers
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {
    "20260415_01_DdxK9-references-column",
    "20260511_01_sptG7-scoped-can-see-tags-markers",
}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO m_markers (id, user_id, marker, entry_id)
        SELECT gen_random_uuid(), NULL, 2, le.id
        FROM l_entries AS le
        ON CONFLICT (entry_id, marker) WHERE user_id IS NULL DO NOTHING
        """
    )


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM m_markers WHERE user_id IS NULL AND marker = 2")


steps = [step(apply_step, rollback_step)]
