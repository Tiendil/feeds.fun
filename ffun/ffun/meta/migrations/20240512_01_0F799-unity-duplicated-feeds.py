"""
unity-duplicated-feeds
"""
import subprocess  # noqa: S404
import sys
import uuid
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240504_02_gEapd-fill-uids-for-feeds"}


def run_merge(base_feed_id: uuid.UUID, feed_id: uuid.UUID) -> None:
    try:
        subprocess.run(  # noqa: S603, S607
            [
                #     'poetry',
                # 'run',
                "ffun",
                "merge-feeds",
                base_feed_id.hex,
                feed_id.hex,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"error: {e}\n")
        raise


def apply_step(conn: Connection[list[Any]]) -> None:
    # it is too difficult to write special migration code for this case
    # so, we will call the cli command for each found duplicated feed
    # TODO: remove this code after new version will be releases and applied to all environments
    #       see https://github.com/Tiendil/feeds.fun/issues/188

    cursor = conn.cursor()

    cursor.execute("SELECT uid FROM f_feeds GROUP BY uid HAVING COUNT(*) > 1")

    uids = [row[0] for row in cursor.fetchall()]

    for uid in uids:
        cursor.execute("SELECT id FROM f_feeds WHERE uid = %(uid)s", {"uid": uid})

        feed_ids = [row[0] for row in cursor.fetchall()]

        base_feed_id = feed_ids[0]
        merged_feed_ids = feed_ids[1:]

        for feed_id in merged_feed_ids:
            run_merge(base_feed_id, feed_id)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    pass


steps = [step(apply_step, rollback_step)]
