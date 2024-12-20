from typing import Iterable

from ffun.scores import entities, operations

count_rules_per_user = operations.count_rules_per_user


def get_score_rules(rules: Iterable[entities.Rule], tags: set[int]) -> list[entities.Rule]:
    score_rules = []

    for rule in rules:
        if rule.excluded_tags & tags:
            continue

        if rule.required_tags <= tags:
            score_rules.append(rule)

    return score_rules


def get_score_contributions(rules: Iterable[entities.Rule], tags: set[int]) -> tuple[int, dict[int, int]]:
    score = 0
    contributions: dict[int, int] = {}

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
