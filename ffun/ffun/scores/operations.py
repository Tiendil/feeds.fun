import uuid
from typing import Any, Iterable

import psycopg
from bidict import bidict

from ffun.core import logging
from ffun.core.postgresql import execute

from .entities import Rule


logger = logging.get_module_logger()


def normalize_tags(tags: Iterable[int]) -> list[int]:
    return list(sorted(tags))


def row_to_rule(row: dict[str, Any]) -> Rule:
    return Rule(
        id=row["id"], user_id=row["user_id"], tags=set(row["tags"]), score=row["score"], created_at=row["created_at"]
    )


async def create_rule(user_id: uuid.UUID, tags: Iterable[int], score: int) -> None:
    tags = normalize_tags(tags)
    key = ",".join(map(str, tags))

    sql = """
        INSERT INTO s_rules (id, user_id, tags, key, score)
        VALUES (%(id)s, %(user_id)s, %(tags)s, %(key)s, %(score)s)
        """

    try:
        await execute(sql, {"id": uuid.uuid4(), "user_id": user_id, "tags": tags, "key": key, "score": score})
    except psycopg.errors.UniqueViolation:
        logger.warning("rule_already_exists", key=key)


async def delete_rule(user_id: uuid.UUID, rule_id: uuid.UUID) -> None:
    sql = """
        DELETE FROM s_rules
        WHERE user_id = %(user_id)s AND id = %(rule_id)s
        """

    await execute(sql, {"user_id": user_id, "rule_id": rule_id})


async def update_rule(user_id: uuid.UUID, rule_id: uuid.UUID, tags: Iterable[int], score: int) -> None:
    tags = normalize_tags(tags)
    key = ",".join(map(str, tags))

    sql = """
    UPDATE s_rules
    SET tags = %(tags)s, key = %(key)s, score = %(score)s
    WHERE user_id = %(user_id)s AND id = %(rule_id)s
    """

    await execute(sql, {"user_id": user_id, "rule_id": rule_id, "tags": tags, "key": key, "score": score})


async def get_rules(user_id: uuid.UUID) -> list[Rule]:
    sql = """
    SELECT *
    FROM s_rules
    WHERE user_id = %(user_id)s
    """

    rows = await execute(sql, {"user_id": user_id})

    return [row_to_rule(row) for row in rows]
