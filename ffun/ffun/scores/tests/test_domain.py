import pytest

from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
)
from ffun.domain.entities import TagId, UserId
from ffun.scores import domain, entities
from ffun.scores.tests.helpers import rule


def get_score_rules(rules: list[entities.Rule], tags: set[int]) -> list[entities.Rule]:
    return domain.get_score_rules(rules, {TagId(t) for t in tags})


def get_score_contributions(rules: list[entities.Rule], tags: set[int]) -> tuple[int, dict[int, int]]:
    score, contributions = domain.get_score_contributions(rules, {TagId(t) for t in tags})
    return score, {int(k): v for k, v in contributions.items()}


class TestGetScoreRules:

    def test_no_rules(self) -> None:
        assert get_score_rules([], set()) == []
        assert get_score_rules([], {1, 2, 3}) == []

    def test_only_required_tags(self) -> None:
        rules = [rule(2, {1, 2, 3}, set()), rule(3, {1, 3}, set()), rule(5, {2}, set())]

        assert get_score_rules(rules, set()) == []
        assert get_score_rules(rules, {1, 2, 3}) == rules
        assert get_score_rules(rules, {1, 2, 3, 4}) == rules
        assert get_score_rules(rules, {1, 3}) == [rules[1]]
        assert get_score_rules(rules, {2, 3}) == [rules[2]]
        assert get_score_rules(rules, {2}) == [rules[2]]

    def test_only_excluded_tags(self) -> None:
        rules = [rule(2, set(), {1, 2, 3}), rule(3, set(), {1, 3}), rule(5, set(), {2})]

        assert get_score_rules(rules, set()) == rules
        assert get_score_rules(rules, {1, 2, 3}) == []
        assert get_score_rules(rules, {1, 2, 3, 4}) == []
        assert get_score_rules(rules, {1, 3}) == [rules[2]]
        assert get_score_rules(rules, {2, 3}) == []
        assert get_score_rules(rules, {2}) == [rules[1]]
        assert get_score_rules(rules, {1}) == [rules[2]]

    def test_required_and_excluded_tags(self) -> None:
        rules = [rule(2, {1, 2, 3}, {4}), rule(3, {1, 3}, {2}), rule(5, {2}, {1, 3})]

        assert get_score_rules(rules, set()) == []
        assert get_score_rules(rules, {1, 2, 3}) == [rules[0]]
        assert get_score_rules(rules, {1, 2, 3, 4}) == []
        assert get_score_rules(rules, {1, 3}) == [rules[1]]
        assert get_score_rules(rules, {2, 3}) == []
        assert get_score_rules(rules, {2}) == [rules[2]]
        assert get_score_rules(rules, {1, 3, 4}) == [rules[1]]


class TestGetScore:

    def test_no_rules(self) -> None:
        assert get_score_contributions([], set()) == (0, {})
        assert get_score_contributions([], {1, 2, 3}) == (0, {})

    def test_only_required_tags(self) -> None:
        rules = [rule(2, {1, 2, 3}, set()), rule(3, {1, 3}, set()), rule(5, {2}, set())]

        assert get_score_contributions(rules, set()) == (0, {})
        assert get_score_contributions(rules, {1, 2, 3}) == (10, {1: 5, 2: 7, 3: 5})
        assert get_score_contributions(rules, {1, 2, 3, 4}) == (10, {1: 5, 2: 7, 3: 5})
        assert get_score_contributions(rules, {1, 3}) == (3, {1: 3, 3: 3})
        assert get_score_contributions(rules, {2, 3}) == (5, {2: 5})
        assert get_score_contributions(rules, {2}) == (5, {2: 5})

    def test_only_excluded_tags(self) -> None:
        rules = [rule(2, set(), {1, 2, 3}), rule(3, set(), {1, 3}), rule(5, set(), {2})]

        assert get_score_contributions(rules, set()) == (10, {})
        assert get_score_contributions(rules, {1, 2, 3}) == (0, {})
        assert get_score_contributions(rules, {1, 2, 3, 4}) == (0, {})
        assert get_score_contributions(rules, {1, 3}) == (5, {})
        assert get_score_contributions(rules, {2, 3}) == (0, {})
        assert get_score_contributions(rules, {2}) == (3, {})
        assert get_score_contributions(rules, {1}) == (5, {})

    def test_required_and_excluded_tags(self) -> None:
        rules = [rule(2, {1, 2, 3}, {4}), rule(3, {1, 3}, {2}), rule(5, {2}, {1, 3})]

        assert get_score_contributions(rules, set()) == (0, {})
        assert get_score_contributions(rules, {1, 2, 3}) == (2, {1: 2, 2: 2, 3: 2})
        assert get_score_contributions(rules, {1, 2, 3, 4}) == (0, {})
        assert get_score_contributions(rules, {1, 3}) == (3, {1: 3, 3: 3})
        assert get_score_contributions(rules, {2, 3}) == (0, {})
        assert get_score_contributions(rules, {2}) == (5, {2: 5})
        assert get_score_contributions(rules, {1, 3, 4}) == (3, {1: 3, 3: 3})


class TestCloneRulesForeReplacements:

    @pytest.mark.asyncio
    async def test_no_replacements(self, internal_user_id: UserId, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:
        await domain.create_or_update_rule(
            internal_user_id, required_tags={three_tags_ids[0]}, excluded_tags=set(), score=2
        )
        await domain.create_or_update_rule(
            internal_user_id, required_tags=set(), excluded_tags={three_tags_ids[1]}, score=2
        )
        async with TableSizeNotChanged("s_rules"):
            await domain.clone_rules_for_replacements({})

    @pytest.mark.asyncio
    async def test_no_rules_for_tags(
        self, internal_user_id: UserId, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:
        await domain.create_or_update_rule(
            internal_user_id, required_tags={three_tags_ids[1]}, excluded_tags=set(), score=2
        )
        await domain.create_or_update_rule(
            internal_user_id, required_tags=set(), excluded_tags={three_tags_ids[2]}, score=2
        )
        async with TableSizeNotChanged("s_rules"):
            await domain.clone_rules_for_replacements({three_tags_ids[0]: three_tags_ids[1]})

    @pytest.mark.asyncio
    async def test_clone_rules(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId],
    ) -> None:
        tag_1, tag_2, tag_3, tag_4, tag_5 = five_tags_ids

        await domain.create_or_update_rule(internal_user_id, required_tags={tag_1}, excluded_tags=set(), score=1)
        await domain.create_or_update_rule(
            internal_user_id,
            required_tags={tag_2},
            excluded_tags={
                tag_4,
                tag_1,
            },
            score=2,
        )
        await domain.create_or_update_rule(
            another_internal_user_id, required_tags=set(), excluded_tags={tag_2}, score=3
        )
        await domain.create_or_update_rule(
            another_internal_user_id, required_tags={tag_2}, excluded_tags={tag_5}, score=4
        )
        await domain.create_or_update_rule(
            another_internal_user_id, required_tags={tag_3}, excluded_tags={tag_2}, score=5
        )

        async with TableSizeDelta("s_rules", delta=3):
            await domain.clone_rules_for_replacements({tag_1: tag_3, tag_5: tag_3})

        rules_1 = await domain.get_rules_for_user(internal_user_id)
        rules_1.sort(key=lambda r: (r.score, sorted(r.required_tags), sorted(r.excluded_tags)))

        rules_1[0].soft_compare(internal_user_id, {tag_1}, set(), 1)
        rules_1[1].soft_compare(internal_user_id, {tag_3}, set(), 1)
        rules_1[2].soft_compare(internal_user_id, {tag_2}, {tag_4, tag_1}, 2)
        rules_1[3].soft_compare(internal_user_id, {tag_2}, {tag_4, tag_3}, 2)

        rules_2 = await domain.get_rules_for_user(another_internal_user_id)
        rules_2.sort(key=lambda r: (r.score, sorted(r.required_tags), sorted(r.excluded_tags)))

        rules_2[0].soft_compare(another_internal_user_id, set(), {tag_2}, 3)
        rules_2[1].soft_compare(another_internal_user_id, {tag_2}, {tag_5}, 4)
        rules_2[2].soft_compare(another_internal_user_id, {tag_2}, {tag_3}, 4)
        rules_2[3].soft_compare(another_internal_user_id, {tag_3}, {tag_2}, 5)


class TestRemoveRulesWithTags:

    @pytest.mark.asyncio
    async def test_no_tags(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:
        await domain.create_or_update_rule(
            internal_user_id, required_tags={three_tags_ids[0]}, excluded_tags=set(), score=2
        )
        await domain.create_or_update_rule(
            another_internal_user_id, required_tags=set(), excluded_tags={three_tags_ids[1]}, score=2
        )

        async with TableSizeNotChanged("s_rules"):
            await domain.remove_rules_with_tags({})

    @pytest.mark.asyncio
    async def test_no_rules_for_tags(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:
        await domain.create_or_update_rule(
            internal_user_id, required_tags={three_tags_ids[0]}, excluded_tags=set(), score=2
        )
        await domain.create_or_update_rule(
            another_internal_user_id, required_tags=set(), excluded_tags={three_tags_ids[1]}, score=2
        )

        async with TableSizeNotChanged("s_rules"):
            await domain.remove_rules_with_tags({three_tags_ids[2]})

    @pytest.mark.asyncio
    async def test_remove_rules(  # pylint: disable=too-many-locals
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId],
    ) -> None:

        tag_1, tag_2, tag_3, tag_4, tag_5 = five_tags_ids

        rule_1_1 = await domain.create_or_update_rule(  # pylint: disable=W0612 # noqa: F841
            internal_user_id, required_tags={tag_1}, excluded_tags=set(), score=1
        )
        rule_1_2 = await domain.create_or_update_rule(
            internal_user_id,
            required_tags={tag_2},
            excluded_tags={
                tag_4,
                tag_3,
            },
            score=2,
        )
        rule_2_1 = await domain.create_or_update_rule(
            another_internal_user_id, required_tags=set(), excluded_tags={tag_2}, score=3
        )
        rule_2_2 = await domain.create_or_update_rule(  # pylint: disable=W0612 # noqa: F841
            another_internal_user_id, required_tags={tag_2}, excluded_tags={tag_5}, score=4
        )
        rule_2_3 = await domain.create_or_update_rule(
            another_internal_user_id, required_tags={tag_3}, excluded_tags={tag_2}, score=5
        )

        async with TableSizeDelta("s_rules", delta=-2):
            await domain.remove_rules_with_tags({tag_1, tag_5})

        rules_1 = await domain.get_rules_for_user(internal_user_id)
        assert {r.id for r in rules_1} == {rule_1_2.id}

        rules_2 = await domain.get_rules_for_user(another_internal_user_id)
        assert {r.id for r in rules_2} == {rule_2_1.id, rule_2_3.id}
