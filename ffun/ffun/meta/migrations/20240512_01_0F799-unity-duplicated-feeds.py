"""
unity-duplicated-feeds
"""
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240504_02_gEapd-fill-uids-for-feeds"}


def apply_step(conn: Connection[list[Any]]) -> None:
    pass


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    pass


steps = [step(apply_step, rollback_step)]
