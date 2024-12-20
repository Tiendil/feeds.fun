from typing import Sequence

from ffun.scores import entities, operations

count_rules_per_user = operations.count_rules_per_user


# TODO: support excluded tags
def get_score_rules(rules: list[entities.Rule], tags: set[int]) -> list[entities.Rule]:
    score_rules = []

    for rule in rules:
        if rule.excluded_tags & tags:
            continue

        if rule.required_tags <= tags:
            score_rules.append(rule)

    return score_rules


# TODO: support excluded tags
def get_score_contributions(rules: Sequence[entities.BaseRule], tags: set[int]) -> tuple[int, dict[int, int]]:
    score = 0
    contributions: dict[int, int] = {}

    for rule in get_score_rules(rules, tags):
        score += rule.score
        for tag in rule.tags:
            contributions[tag] = contributions.get(tag, 0) + rule.score

    return score, contributions


create_or_update_rule = operations.create_or_update_rule
delete_rule = operations.delete_rule
get_rules = operations.get_rules
update_rule = operations.update_rule
