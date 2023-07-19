"""
add-title-and-description
"""

from yoyo import step


__depends__ = {"20230329_01_ilwfq-feeds-table"}


sql = """
ALTER TABLE f_feeds
ADD COLUMN title TEXT DEFAULT NULL,
ADD COLUMN description TEXT DEFAULT NULL
"""


def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(sql)


def rollback_step(conn):
    cursor = conn.cursor()

    sql = """
    ALTER TABLE f_feeds
    DROP COLUMN title,
    DROP COLUMN description
    """

    cursor.execute(sql)


steps = [step(apply_step, rollback_step)]
