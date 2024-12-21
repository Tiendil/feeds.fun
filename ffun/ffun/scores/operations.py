from typing import Any, Iterable

import psycopg

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.domain.domain import new_rule_id
from ffun.domain.entities import RuleId, UserId
from ffun.scores import errors
from ffun.scores.entities import Rule

logger = logging.get_module_logger()


def _normalize_tags(tags: Iterable[int]) -> list[int]:
    return list(sorted(tags))


def _key_from_tags(required_tags: Iterable[int], excluded_tags: Iterable[int]) -> str:
    return ",".join(map(str, required_tags)) + "|" + ",".join(map(str, excluded_tags))


def row_to_rule(row: dict[str, Any]) -> Rule:
    return Rule(
        id=row["id"],
        user_id=row["user_id"],
        required_tags=row["required_tags"],
        excluded_tags=row["excluded_tags"],
        score=row["score"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_or_update_rule(
    user_id: UserId, required_tags: Iterable[int], excluded_tags: Iterable[int], score: int
) -> Rule:
    required_tags = set(required_tags)
    excluded_tags = set(excluded_tags)

    if required_tags & excluded_tags:
        raise errors.TagsIntersection()

    required_tags = _normalize_tags(required_tags)
    excluded_tags = _normalize_tags(excluded_tags)

    key = _key_from_tags(required_tags, excluded_tags)

    sql = """
        INSERT INTO s_rules (id, user_id, required_tags, excluded_tags, key, score)
        VALUES (%(id)s, %(user_id)s, %(required_tags)s, %(excluded_tags)s, %(key)s, %(score)s)
        RETURNING *
        """

    try:
        result = await execute(
            sql,
            {
                "id": new_rule_id(),
                "user_id": user_id,
                "required_tags": required_tags,
                "excluded_tags": excluded_tags,
                "key": key,
                "score": score,
            },
        )

        logger.business_event(
            "rule_created",
            user_id=user_id,
            rule_id=result[0]["id"],
            required_tags=required_tags,
            excluded_tags=excluded_tags,
            score=score,
        )
    except psycopg.errors.UniqueViolation:
        logger.info("rule_already_exists_change_score", key=key)

        sql = """
        UPDATE s_rules
        SET score = %(score)s, updated_at = NOW()
        WHERE user_id = %(user_id)s AND key = %(key)s
        RETURNING *
        """

        result = await execute(sql, {"user_id": user_id, "key": key, "score": score})

        logger.business_event(
            "rule_updated",
            user_id=user_id,
            rule_id=result[0]["id"],
            required_tags=required_tags,
            excluded_tags=excluded_tags,
            score=score,
        )

    return row_to_rule(result[0])


async def delete_rule(user_id: UserId, rule_id: RuleId) -> None:
    sql = """
        DELETE FROM s_rules
        WHERE user_id = %(user_id)s AND id = %(rule_id)s
        RETURNING id
        """

    result = await execute(sql, {"user_id": user_id, "rule_id": rule_id})

    if result:
        logger.business_event("rule_deleted", user_id=user_id, rule_id=rule_id)


async def update_rule(
    user_id: UserId, rule_id: RuleId, required_tags: Iterable[int], excluded_tags: Iterable[int], score: int
) -> Rule:
    required_tags = set(required_tags)
    excluded_tags = set(excluded_tags)

    if required_tags & excluded_tags:
        raise errors.TagsIntersection()

    required_tags = _normalize_tags(required_tags)
    excluded_tags = _normalize_tags(excluded_tags)

    key = _key_from_tags(required_tags, excluded_tags)

    sql = """
    UPDATE s_rules
    SET required_tags = %(required_tags)s,
        excluded_tags = %(excluded_tags)s,
        key = %(key)s,
        score = %(score)s,
        updated_at = NOW()
    WHERE user_id = %(user_id)s AND id = %(rule_id)s
    returning *
    """

    result = await execute(
        sql,
        {
            "user_id": user_id,
            "rule_id": rule_id,
            "required_tags": required_tags,
            "excluded_tags": excluded_tags,
            "key": key,
            "score": score,
        },
    )

    if not result:
        raise errors.NoRuleFound()

    logger.business_event(
        "rule_updated",
        user_id=user_id,
        rule_id=result[0]["id"],
        required_tags=required_tags,
        excluded_tags=excluded_tags,
        score=score,
    )

    return row_to_rule(result[0])


async def get_rules(user_id: UserId) -> list[Rule]:
    sql = """
    SELECT *
    FROM s_rules
    WHERE user_id = %(user_id)s
    """

    rows = await execute(sql, {"user_id": user_id})

    return [row_to_rule(row) for row in rows]


async def count_rules_per_user() -> dict[UserId, int]:
    # Not optimal implementation, but should work for a very long time
    result = await execute("SELECT user_id, COUNT(*) FROM s_rules GROUP BY user_id")

    return {row["user_id"]: row["count"] for row in result}
