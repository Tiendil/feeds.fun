
from . import entities, operations


def get_score(rules: list[entities.Rule], tags: set[int]) -> int:
    total = 0

    for rule in rules:
        if rule.tags <= tags:
            total += rule.score

    return total


create_rule = operations.create_rule
delete_rule = operations.delete_rule
get_rules = operations.get_rules
