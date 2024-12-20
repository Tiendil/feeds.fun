import pytest

from ffun.scores import domain, entities


def rule(score: int, required_tags: set[int], excluded_tags: set[int]) -> entities.BaseRule:
    return entities.BaseRule(score=score, required_tags=required_tags, excluded_tags=excluded_tags)


class TestGetScoreRules:

    def test_no_rules(self) -> None:
        assert domain.get_score_rules([], set()) == []
        assert domain.get_score_rules([], {1, 2, 3}) == []

    def test_only_required_tags(self) -> None:
        rules = [ rule(2, {1, 2, 3}, set()),
                  rule(3, {1, 3}, set()),
                  rule(5, {2}, set()) ]

        assert domain.get_score_rules(rules, set()) == []
        assert domain.get_score_rules(rules, {1, 2, 3}) == rules
        assert domain.get_score_rules(rules, {1, 2, 3, 4}) == rules
        assert domain.get_score_rules(rules, {1, 3}) == [rules[1]]
        assert domain.get_score_rules(rules, {2, 3}) == [rules[2]]
        assert domain.get_score_rules(rules, {2}) == [rules[2]]

    def test_only_excluded_tags(self) -> None:
        rules = [ rule(2, set(), {1, 2, 3}),
                  rule(3, set(), {1, 3}),
                  rule(5, set(), {2}) ]

        assert domain.get_score_rules(rules, set()) == rules
        assert domain.get_score_rules(rules, {1, 2, 3}) == []
        assert domain.get_score_rules(rules, {1, 2, 3, 4}) == []
        assert domain.get_score_rules(rules, {1, 3}) == [rules[2]]
        assert domain.get_score_rules(rules, {2, 3}) == []
        assert domain.get_score_rules(rules, {2}) == [rules[1]]
        assert domain.get_score_rules(rules, {1}) == [rules[2]]

    def test_required_and_excluded_tags(self) -> None:
        rules = [ rule(2, {1, 2, 3}, {4}),
                  rule(3, {1, 3}, {2}),
                  rule(5, {2}, {1, 3}) ]

        assert domain.get_score_rules(rules, set()) == []
        assert domain.get_score_rules(rules, {1, 2, 3}) == [rules[0]]
        assert domain.get_score_rules(rules, {1, 2, 3, 4}) == []
        assert domain.get_score_rules(rules, {1, 3}) == [rules[1]]
        assert domain.get_score_rules(rules, {2, 3}) == []
        assert domain.get_score_rules(rules, {2}) == [rules[2]]
        assert domain.get_score_rules(rules, {1, 3, 4}) == [rules[1]]


# class TestGetScore:
#     @pytest.mark.parametrize(
#         "rules, tags, contributions",
#         [
#             [[], set(), (0, {})],
#             [[], {1, 2, 3}, (0, {})],
#             [[rule(1, {1, 2, 3})], set(), (0, {})],
#             [[rule(2, {1, 2, 3})], {1, 2, 3}, (2, {1: 2, 2: 2, 3: 2})],
#             [[rule(3, {1, 2, 3})], {1, 2, 3, 4}, (3, {1: 3, 2: 3, 3: 3})],
#             [[rule(4, {1, 2}), rule(5, {1, 3})], {1, 2, 3, 4}, (9, {1: 9, 2: 4, 3: 5})],
#             [[rule(6, {1, 2}), rule(-7, {3, 5}), rule(8, {1, 4})], {2, 3, 4}, (0, {})],
#             [[rule(9, {1, 2}), rule(-10, {3, 5}), rule(11, {4, 5})], {2, 3, 4, 5}, (1, {3: -10, 4: 11, 5: 1})],
#             [[rule(9, {1, 2}), rule(-10, {3, 5}), rule(11, {4})], {2, 3, 4, 5}, (1, {3: -10, 4: 11, 5: -10})],
#             [[rule(12, {1, 2}), rule(-12, {2, 3})], {1, 2, 3, 4, 5}, (0, {1: 12, 2: 0, 3: -12})],
#         ],
#     )
#     def test(self, rules: list[entities.BaseRule], tags: set[int], contributions: tuple[int, dict[int, int]]) -> None:
#         assert domain.get_score_contributions(rules, tags) == contributions
