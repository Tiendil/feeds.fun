from collections import defaultdict

from . import entities, operations


def get_score_contributions(rules: list[entities.BaseRule], tags: set[int]) -> tuple[int, dict[int, int]]:
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


create_rule = operations.create_rule
delete_rule = operations.delete_rule
get_rules = operations.get_rules
update_rule = operations.update_rule
