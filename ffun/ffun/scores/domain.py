from typing import Iterable

from ffun.domain.entities import TagId
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
delete_rule = operations.delete_rule
get_rules = operations.get_rules
update_rule = operations.update_rule
get_all_tags_in_rules = operations.get_all_tags_in_rules


# TODO: tests
async def clone_rules_for_replacements(replacements: dict[TagId, TagId]) -> None:
    rule_ids = await operations.get_rules_with_tags(set(replacements.keys()))

    rules = await operations.get_rules_by_ids(rule_ids)

    new_rules = [rule.replace_tags(replacements) for rule in rules]

    for rule in new_rules:
        await operations.create_or_update_rule(
            user_id=rule.user_id,
            required_tags=rule.required_tags,
            excluded_tags=rule.excluded_tags,
            score=rule.score)


# TODO: tests
async def remove_rules_with_tags(tag_ids: Iterable[TagId]) -> None:
    rule_ids = await operations.get_rules_with_tags(tag_ids)

    for rule_id in rule_ids:
        await operations.delete_rule(rule_id)
