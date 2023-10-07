from collections import defaultdict
from typing import Sequence

from ffun.scores import entities, operations


def get_score_contributions(rules: Sequence[entities.BaseRule], tags: set[int]) -> tuple[int, dict[int, int]]:
    score = 0
    contributions: dict[int, int] = defaultdict(int)

    for rule in rules:
        if rule.tags <= tags:
            score += rule.score
            for tag in rule.tags:
                contributions[tag] += rule.score

    return score, contributions


def get_score_rules(rules: list[entities.Rule], tags: set[int]) -> list[entities.Rule]:
    score_rules = []

    for rule in rules:
        if rule.tags <= tags:
            score_rules.append(rule)

    return score_rules


create_or_update_rule = operations.create_or_update_rule
delete_rule = operations.delete_rule
get_rules = operations.get_rules
update_rule = operations.update_rule
