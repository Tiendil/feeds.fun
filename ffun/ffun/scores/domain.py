from . import entities, operations


def get_score(rules: list[entities.Rule], tags: set[int]) -> int:
    total = 0

    for rule in rules:
        if rule.tags <= tags:
            total += rule.score

    return total


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
