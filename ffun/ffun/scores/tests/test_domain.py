import pytest

from ffun.scores import domain, entities


def rule(score: int, tags: set[int]) -> entities.BaseRule:
    return entities.BaseRule(score=score, tags=tags)


class TestGetScore:
    @pytest.mark.parametrize(
        "rules, tags, contributions",
        [
            [[], set(), (0, {})],
            [[], {1, 2, 3}, (0, {})],
            [[rule(1, {1, 2, 3})], set(), (0, {})],
            [[rule(2, {1, 2, 3})], {1, 2, 3}, (2, {1: 2, 2: 2, 3: 2})],
            [[rule(3, {1, 2, 3})], {1, 2, 3, 4}, (3, {1: 3, 2: 3, 3: 3})],
            [[rule(4, {1, 2}), rule(5, {1, 3})], {1, 2, 3, 4}, (9, {1: 9, 2: 4, 3: 5})],
            [[rule(6, {1, 2}), rule(-7, {3, 5}), rule(8, {1, 4})], {2, 3, 4}, (0, {})],
            [[rule(9, {1, 2}), rule(-10, {3, 5}), rule(11, {4, 5})], {2, 3, 4, 5}, (1, {3: -10, 4: 11, 5: 1})],
            [[rule(9, {1, 2}), rule(-10, {3, 5}), rule(11, {4})], {2, 3, 4, 5}, (1, {3: -10, 4: 11, 5: -10})],
            [[rule(12, {1, 2}), rule(-12, {2, 3})], {1, 2, 3, 4, 5}, (0, {1: 12, 2: 0, 3: -12})],
        ],
    )
    def test(self, rules: list[entities.BaseRule], tags: set[int], contributions: dict[int, int]) -> None:
        assert domain.get_score_contributions(rules, tags) == contributions
