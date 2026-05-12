"""
scoped-can-see-tags-markers
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230419_01_9vMm5-markers-tables"}


old_index = "idx_m_markers_user_id_marker_entry_id"
user_marker_index = "m_markers_user_id_entry_id_marker_idx"
global_marker_index = "m_markers_global_entry_id_marker_idx"


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(f"DROP INDEX {old_index}")
    cursor.execute("ALTER TABLE m_markers ALTER COLUMN user_id DROP NOT NULL")
    cursor.execute(
        f"""
        CREATE UNIQUE INDEX {user_marker_index}
        ON m_markers (user_id, entry_id, marker)
        WHERE user_id IS NOT NULL
        """
    )
    cursor.execute(
        f"""
        CREATE UNIQUE INDEX {global_marker_index}
        ON m_markers (entry_id, marker)
        WHERE user_id IS NULL
        """
    )


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(f"DROP INDEX {global_marker_index}")
    cursor.execute(f"DROP INDEX {user_marker_index}")
    cursor.execute("DELETE FROM m_markers WHERE user_id IS NULL")
    cursor.execute("ALTER TABLE m_markers ALTER COLUMN user_id SET NOT NULL")
    cursor.execute(f"CREATE UNIQUE INDEX {old_index} ON m_markers (user_id, entry_id, marker)")


steps = [step(apply_step, rollback_step)]
