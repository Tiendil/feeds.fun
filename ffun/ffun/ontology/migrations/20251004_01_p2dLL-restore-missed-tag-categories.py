"""
restore missed tag categories
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20251002_01_tbMXV-add-index-on-tags-for-tag-relations"}


sql = """
INSERT INTO o_tags_properties (tag_id, type, value, processor_id, created_at)
SELECT r.tag_id, 3, %(categories)s, p.processor_id, r.created_at
FROM o_relations AS r
LEFT JOIN o_relations_processors AS p ON r.id = p.relation_id
WHERE {condition}
ON CONFLICT (tag_id, type, processor_id) DO NOTHING;
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    for processor_id, categories in [(1, "network-domain"), (2, "feed-tag"), (5, "special")]:
        cursor.execute(
            sql.format(condition="p.processor_id = %(processor_id)s"),
            {"processor_id": processor_id, "categories": categories},
        )

    cursor.execute(sql.format(condition="p.processor_id NOT IN (1, 2, 5)"), {"categories": "free-form"})


def rollback_step(_conn: Connection[dict[str, Any]]) -> None:
    pass


steps = [step(apply_step, rollback_step)]
