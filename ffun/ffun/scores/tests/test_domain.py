from ffun.core import utils
from ffun.domain.domain import new_rule_id, new_user_id
from ffun.scores import domain, entities


def rule(score: int, required_tags: set[int], excluded_tags: set[int]) -> entities.Rule:
    return entities.Rule(
        id=new_rule_id(),
        user_id=new_user_id(),
        score=score,
        required_tags=required_tags,
        excluded_tags=excluded_tags,
        created_at=utils.now(),
        updated_at=utils.now(),
    )


class TestGetScoreRules:

    def test_no_rules(self) -> None:
        assert domain.get_score_rules([], set()) == []
        assert domain.get_score_rules([], {1, 2, 3}) == []

    def test_only_required_tags(self) -> None:
        rules = [rule(2, {1, 2, 3}, set()), rule(3, {1, 3}, set()), rule(5, {2}, set())]

        assert domain.get_score_rules(rules, set()) == []
        assert domain.get_score_rules(rules, {1, 2, 3}) == rules
        assert domain.get_score_rules(rules, {1, 2, 3, 4}) == rules
        assert domain.get_score_rules(rules, {1, 3}) == [rules[1]]
        assert domain.get_score_rules(rules, {2, 3}) == [rules[2]]
        assert domain.get_score_rules(rules, {2}) == [rules[2]]

    def test_only_excluded_tags(self) -> None:
        rules = [rule(2, set(), {1, 2, 3}), rule(3, set(), {1, 3}), rule(5, set(), {2})]

        assert domain.get_score_rules(rules, set()) == rules
        assert domain.get_score_rules(rules, {1, 2, 3}) == []
        assert domain.get_score_rules(rules, {1, 2, 3, 4}) == []
        assert domain.get_score_rules(rules, {1, 3}) == [rules[2]]
        assert domain.get_score_rules(rules, {2, 3}) == []
        assert domain.get_score_rules(rules, {2}) == [rules[1]]
        assert domain.get_score_rules(rules, {1}) == [rules[2]]

    def test_required_and_excluded_tags(self) -> None:
        rules = [rule(2, {1, 2, 3}, {4}), rule(3, {1, 3}, {2}), rule(5, {2}, {1, 3})]

        assert domain.get_score_rules(rules, set()) == []
        assert domain.get_score_rules(rules, {1, 2, 3}) == [rules[0]]
        assert domain.get_score_rules(rules, {1, 2, 3, 4}) == []
        assert domain.get_score_rules(rules, {1, 3}) == [rules[1]]
        assert domain.get_score_rules(rules, {2, 3}) == []
        assert domain.get_score_rules(rules, {2}) == [rules[2]]
        assert domain.get_score_rules(rules, {1, 3, 4}) == [rules[1]]


class TestGetScore:

    def test_no_rules(self) -> None:
        assert domain.get_score_contributions([], set()) == (0, {})
        assert domain.get_score_contributions([], {1, 2, 3}) == (0, {})

    def test_only_required_tags(self) -> None:
        rules = [rule(2, {1, 2, 3}, set()), rule(3, {1, 3}, set()), rule(5, {2}, set())]

        assert domain.get_score_contributions(rules, set()) == (0, {})
        assert domain.get_score_contributions(rules, {1, 2, 3}) == (10, {1: 5, 2: 7, 3: 5})
        assert domain.get_score_contributions(rules, {1, 2, 3, 4}) == (10, {1: 5, 2: 7, 3: 5})
        assert domain.get_score_contributions(rules, {1, 3}) == (3, {1: 3, 3: 3})
        assert domain.get_score_contributions(rules, {2, 3}) == (5, {2: 5})
        assert domain.get_score_contributions(rules, {2}) == (5, {2: 5})

    def test_only_excluded_tags(self) -> None:
        rules = [rule(2, set(), {1, 2, 3}), rule(3, set(), {1, 3}), rule(5, set(), {2})]

        assert domain.get_score_contributions(rules, set()) == (10, {})
        assert domain.get_score_contributions(rules, {1, 2, 3}) == (0, {})
        assert domain.get_score_contributions(rules, {1, 2, 3, 4}) == (0, {})
        assert domain.get_score_contributions(rules, {1, 3}) == (5, {})
        assert domain.get_score_contributions(rules, {2, 3}) == (0, {})
        assert domain.get_score_contributions(rules, {2}) == (3, {})
        assert domain.get_score_contributions(rules, {1}) == (5, {})

    def test_required_and_excluded_tags(self) -> None:
        rules = [rule(2, {1, 2, 3}, {4}), rule(3, {1, 3}, {2}), rule(5, {2}, {1, 3})]

        assert domain.get_score_contributions(rules, set()) == (0, {})
        assert domain.get_score_contributions(rules, {1, 2, 3}) == (2, {1: 2, 2: 2, 3: 2})
        assert domain.get_score_contributions(rules, {1, 2, 3, 4}) == (0, {})
        assert domain.get_score_contributions(rules, {1, 3}) == (3, {1: 3, 3: 3})
        assert domain.get_score_contributions(rules, {2, 3}) == (0, {})
        assert domain.get_score_contributions(rules, {2}) == (5, {2: 5})
        assert domain.get_score_contributions(rules, {1, 3, 4}) == (3, {1: 3, 3: 3})
