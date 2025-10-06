from typing import Iterable

from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.domain.entities import RuleId, TagId, UserId
from ffun.scores import entities, operations

count_rules_per_user = operations.count_rules_per_user


def get_score_rules(rules: Iterable[entities.Rule], tags: set[TagId]) -> list[entities.Rule]:
    score_rules = []

    for rule in rules:
        if rule.excluded_tags & tags:
            continue

        if rule.required_tags <= tags:
            score_rules.append(rule)

    return score_rules


def get_score_contributions(rules: Iterable[entities.Rule], tags: set[TagId]) -> tuple[int, dict[TagId, int]]:
    score = 0
    contributions: dict[TagId, int] = {}

    for rule in get_score_rules(rules, tags):
        score += rule.score

        # We may want to think about calculating contributions for excluded tags
        # but currently there is no visible need for that
        for tag in rule.required_tags:
            contributions[tag] = contributions.get(tag, 0) + rule.score

    return score, contributions


create_or_update_rule = operations.create_or_update_rule
update_rule = operations.update_rule
get_all_tags_in_rules = operations.get_all_tags_in_rules


async def get_rules_for_user(user_id: UserId) -> list[entities.Rule]:
    return await operations.get_rules_for(execute, user_ids=[user_id])


async def delete_rule(user_id: UserId, rule_id: RuleId) -> None:
    await operations.delete_rule(execute, user_id, rule_id)


@run_in_transaction
async def clone_rules_for_replacements(execute: ExecuteType, replacements: dict[TagId, TagId]) -> None:
    if not replacements:
        return

    rules = await operations.get_rules_for(execute, tag_ids=list(replacements.keys()))

    for rule in rules:
        new_required_tags, new_excluded_tags = rule.replace_tags(replacements)

        await operations.create_or_update_rule(
            user_id=rule.user_id, required_tags=new_required_tags, excluded_tags=new_excluded_tags, score=rule.score
        )


@run_in_transaction
async def remove_rules_with_tags(execute: ExecuteType, tag_ids: list[TagId]) -> None:
    if not tag_ids:
        return

    rules = await operations.get_rules_for(execute, tag_ids=tag_ids)

    for rule in rules:
        await operations.delete_rule(execute, rule.user_id, rule.id)
