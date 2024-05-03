"""
migrate_to_processors_queue
"""
import uuid
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from pypika import PostgreSQLQuery
from yoyo import step

__depends__ = {"20240313_01_Yv74T-processors-pointers", "20240315_01_tWftt-optimize-l-entries"}


def get_actual_entries(cursor: Any) -> set[uuid.UUID]:
    cursor.execute("SELECT id FROM l_entries")

    return {row["id"] for row in cursor.fetchall()}


def get_old_entries(cursor: Any, processor_id: int, state: int) -> list[uuid.UUID]:
    cursor.execute(
        "SELECT entry_id FROM l_entry_process_info WHERE processor_id = %(processor_id)s AND state = %(state)s",
        {"processor_id": processor_id, "state": state},
    )

    return [row["entry_id"] for row in cursor.fetchall()]


def add_entries_to_failed_storage(cursor: Any, processor_id: int, failed_entries: list[uuid.UUID]) -> None:
    chunk = 10000

    for i in range(0, len(failed_entries), chunk):
        query = PostgreSQLQuery.into("ln_failed_entries").columns("processor_id", "entry_id")

        for entry_id in failed_entries[i : i + chunk]:
            query = query.insert((processor_id, entry_id))

        cursor.execute(str(query))


def add_entries_to_queue(cursor: Any, processor_id: int, entries: list[uuid.UUID]) -> None:
    chunk = 10000

    for i in range(0, len(entries), chunk):
        query = PostgreSQLQuery.into("ln_processors_queue").columns("processor_id", "entry_id")

        for entry_id in entries[i : i + chunk]:
            query = query.insert((processor_id, entry_id))

        cursor.execute(str(query))


def create_processor_pointer(cursor: Any, processor_id: int) -> None:
    sql = """
    INSERT INTO ln_processor_pointers (processor_id, pointer_created_at, pointer_entry_id)
    VALUES (%(processor_id)s, NOW(), '00000000-0000-0000-0000-000000000000')
    """
    cursor.execute(sql, {"processor_id": processor_id})


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor(row_factory=dict_row)

    all_entries = get_actual_entries(cursor)

    for processor_id in (1, 2, 3, 4, 5):
        failed_entries = get_old_entries(cursor, processor_id, 2)
        add_entries_to_failed_storage(cursor, processor_id, failed_entries)

        successed_entries = get_old_entries(cursor, processor_id, 1)
        retried_entries = get_old_entries(cursor, processor_id, 3)

        entries_to_add = all_entries - set(successed_entries) - set(retried_entries) - set(failed_entries)
        add_entries_to_queue(cursor, processor_id, list(entries_to_add))

        create_processor_pointer(cursor, processor_id)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    # the l_entry_process_info will be removed in https://github.com/Tiendil/feeds.fun/issues/177

    cursor = conn.cursor()

    cursor.execute("DELETE FROM ln_processors_queue")
    cursor.execute("DELETE FROM ln_failed_entries")
    cursor.execute("DELETE FROM ln_processor_pointers")


steps = [step(apply_step, rollback_step)]
