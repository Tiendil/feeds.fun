"""
index-to-search-by-value
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230701_01_7zBP0-settings-table"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX idx_us_settings_kind_value ON us_settings (kind, value)")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP INDEX idx_us_settings_kind_value")


steps = [step(apply_step, rollback_step)]
