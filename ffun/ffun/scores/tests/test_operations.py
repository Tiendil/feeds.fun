import pytest

from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.domain.domain import new_rule_id
from ffun.domain.entities import UserId
from ffun.scores import domain, errors, operations


class TestCreateOrUpdateRule:
    @pytest.mark.asyncio
    async def test_create_new_rule(
        self, internal_user_id: UserId, five_tags_ids: tuple[int, int, int, int, int]
    ) -> None:
        required_tags = five_tags_ids[:3]
        excluded_tags = five_tags_ids[3:]

        with capture_logs() as logs:
            async with TableSizeDelta("s_rules", delta=1):
                created_rule = await operations.create_or_update_rule(
                    internal_user_id, score=13, required_tags=required_tags, excluded_tags=excluded_tags
                )

        rules = await domain.get_rules(internal_user_id)

        assert rules == [created_rule]

        assert created_rule.user_id == internal_user_id
        assert created_rule.required_tags == set(required_tags)
        assert created_rule.excluded_tags == set(excluded_tags)
        assert created_rule.score == 13

        assert_logs_has_business_event(
            logs,
            "rule_created",
            user_id=internal_user_id,
            rule_id=str(created_rule.id),
            required_tags=list(required_tags),
            excluded_tags=list(excluded_tags),
            score=13,
        )
        assert_logs_has_no_business_event(logs, "rule_updated")

    @pytest.mark.asyncio
    async def test_tags_order_does_not_affect_creation(
        self, internal_user_id: UserId, five_tags_ids: tuple[int, int, int, int, int]
    ) -> None:
        required_tags = list(five_tags_ids[:3])
        excluded_tags = list(five_tags_ids[3:])

        async with TableSizeDelta("s_rules", delta=1):
            created_rule_1 = await operations.create_or_update_rule(
                internal_user_id, required_tags=required_tags, excluded_tags=excluded_tags, score=13
            )

            created_rule_2 = await operations.create_or_update_rule(
                internal_user_id,
                required_tags=reversed(required_tags),
                excluded_tags=reversed(excluded_tags),
                score=17,
            )

        assert created_rule_1.required_tags == created_rule_2.required_tags
        assert created_rule_1.excluded_tags == created_rule_2.excluded_tags

        rules = await domain.get_rules(internal_user_id)

        assert rules == [created_rule_2]

    @pytest.mark.asyncio
    async def test_update_scores_of_existed_rule(
        self, internal_user_id: UserId, five_tags_ids: tuple[int, int, int, int, int]
    ) -> None:
        required_tags = list(five_tags_ids[:3])
        excluded_tags = list(five_tags_ids[3:])

        await operations.create_or_update_rule(
            internal_user_id, score=13, required_tags=required_tags, excluded_tags=excluded_tags
        )

        with capture_logs() as logs:
            async with TableSizeNotChanged("s_rules"):
                updated_rule = await operations.create_or_update_rule(
                    internal_user_id, score=17, required_tags=required_tags, excluded_tags=excluded_tags
                )

        rules = await domain.get_rules(internal_user_id)

        assert rules == [updated_rule]

        assert updated_rule.user_id == internal_user_id
        assert updated_rule.required_tags == set(required_tags)
        assert updated_rule.excluded_tags == set(excluded_tags)
        assert updated_rule.score == 17

        assert_logs_has_business_event(
            logs,
            "rule_updated",
            user_id=internal_user_id,
            rule_id=str(updated_rule.id),
            required_tags=required_tags,
            excluded_tags=excluded_tags,
            score=17,
        )
        assert_logs_has_no_business_event(logs, "rule_created")

    @pytest.mark.asyncio
    async def test_multiple_entities(
        self, internal_user_id: UserId, another_internal_user_id: UserId, five_tags_ids: tuple[int, int, int, int, int]
    ) -> None:
        await operations.create_or_update_rule(
            internal_user_id, required_tags=five_tags_ids[:2], excluded_tags=five_tags_ids[-2:], score=3
        )
        await operations.create_or_update_rule(
            another_internal_user_id, required_tags=five_tags_ids[:2], excluded_tags=five_tags_ids[-2:], score=5
        )
        await operations.create_or_update_rule(
            another_internal_user_id, required_tags=five_tags_ids[1:], excluded_tags=five_tags_ids[:1], score=7
        )
        await operations.create_or_update_rule(
            internal_user_id, required_tags=five_tags_ids[:2], excluded_tags=five_tags_ids[-2:], score=11
        )

        rules = await domain.get_rules(internal_user_id)

        assert len(rules) == 1

        assert rules[0].user_id == internal_user_id
        assert rules[0].required_tags == set(five_tags_ids[:2])
        assert rules[0].excluded_tags == set(five_tags_ids[-2:])
        assert rules[0].score == 11

        rules = await domain.get_rules(another_internal_user_id)

        rules.sort(key=lambda r: r.score)

        assert len(rules) == 2

        assert rules[0].user_id == another_internal_user_id
        assert rules[0].required_tags == set(five_tags_ids[:2])
        assert rules[0].excluded_tags == set(five_tags_ids[-2:])
        assert rules[0].score == 5

        assert rules[1].user_id == another_internal_user_id
        assert rules[1].required_tags == set(five_tags_ids[1:])
        assert rules[1].excluded_tags == set(five_tags_ids[:1])
        assert rules[1].score == 7

    @pytest.mark.asyncio
    async def test_tags_intersection(
        self, internal_user_id: UserId, five_tags_ids: tuple[int, int, int, int, int]
    ) -> None:
        required_tags = five_tags_ids[:3]
        excluded_tags = five_tags_ids[2:]

        assert len(set(required_tags) & set(excluded_tags)) == 1

        with capture_logs() as logs:
            with pytest.raises(errors.TagsIntersection):
                async with TableSizeNotChanged("s_rules"):
                    await operations.create_or_update_rule(
                        internal_user_id, required_tags=required_tags, excluded_tags=excluded_tags, score=13
                    )

        rules = await domain.get_rules(internal_user_id)

        assert rules == []

        assert_logs_has_no_business_event(logs, "rule_created")


class TestDeleteRule:
    @pytest.mark.asyncio
    async def test_delete_rule(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        rule_to_delete = await operations.create_or_update_rule(
            internal_user_id, required_tags=three_tags_ids, excluded_tags=[], score=13
        )
        rule_2 = await operations.create_or_update_rule(
            internal_user_id, required_tags=three_tags_ids[:2], excluded_tags=[], score=17
        )
        rule_3 = await operations.create_or_update_rule(
            another_internal_user_id, required_tags=[], excluded_tags=three_tags_ids, score=19
        )

        with capture_logs() as logs:
            async with TableSizeDelta("s_rules", delta=-1):
                await operations.delete_rule(internal_user_id, rule_to_delete.id)

        assert_logs_has_business_event(logs, "rule_deleted", user_id=internal_user_id, rule_id=str(rule_to_delete.id))

        rules = await domain.get_rules(internal_user_id)

        assert rules == [rule_2]

        rules = await domain.get_rules(another_internal_user_id)

        assert rules == [rule_3]

    @pytest.mark.asyncio
    async def test_delete_not_existed_rule(self, internal_user_id: UserId) -> None:
        with capture_logs() as logs:
            async with TableSizeNotChanged("s_rules"):
                await operations.delete_rule(internal_user_id, new_rule_id())

        assert_logs_has_no_business_event(logs, "rule_deleted")

    @pytest.mark.asyncio
    async def test_delete_for_wrong_user(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        rule_to_delete = await operations.create_or_update_rule(
            internal_user_id, required_tags=three_tags_ids, excluded_tags=[], score=13
        )

        async with TableSizeNotChanged("s_rules"):
            await operations.delete_rule(another_internal_user_id, rule_to_delete.id)


class TestUpdateRule:
    @pytest.mark.asyncio
    async def test_update_rule(self, internal_user_id: UserId, five_tags_ids: tuple[int, int, int, int, int]) -> None:
        required_tags = list(five_tags_ids[:3])
        excluded_tags = list(five_tags_ids[3:])

        rule_to_update = await operations.create_or_update_rule(
            internal_user_id, required_tags=required_tags, excluded_tags=excluded_tags, score=13
        )

        with capture_logs() as logs:
            async with TableSizeNotChanged("s_rules"):
                updated_rule = await operations.update_rule(
                    internal_user_id,
                    rule_to_update.id,
                    required_tags=five_tags_ids[:4],
                    excluded_tags=five_tags_ids[4:],
                    score=17,
                )

        assert updated_rule.id == rule_to_update.id
        assert updated_rule.user_id == internal_user_id
        assert updated_rule.required_tags == set(five_tags_ids[:4])
        assert updated_rule.excluded_tags == set(five_tags_ids[4:])
        assert updated_rule.score == 17

        rules = await domain.get_rules(internal_user_id)

        assert rules == [updated_rule]

        assert_logs_has_business_event(
            logs,
            "rule_updated",
            user_id=internal_user_id,
            rule_id=str(rule_to_update.id),
            required_tags=list(five_tags_ids[:4]),
            excluded_tags=list(five_tags_ids[4:]),
            score=17,
        )

    @pytest.mark.asyncio
    async def test_update_not_existed_rule(
        self, internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        with capture_logs() as logs:
            async with TableSizeNotChanged("s_rules"):
                with pytest.raises(errors.NoRuleFound):
                    await operations.update_rule(
                        internal_user_id,
                        new_rule_id(),
                        required_tags=three_tags_ids[:2],
                        excluded_tags=three_tags_ids[2:],
                        score=17,
                    )

        assert_logs_has_no_business_event(logs, "rule_updated")

    @pytest.mark.asyncio
    async def test_wrong_user(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        rule_to_update = await operations.create_or_update_rule(
            internal_user_id, required_tags=three_tags_ids[:2], excluded_tags=[], score=13
        )

        async with TableSizeNotChanged("s_rules"):
            with pytest.raises(errors.NoRuleFound):
                await operations.update_rule(
                    another_internal_user_id,
                    rule_to_update.id,
                    required_tags=three_tags_ids[2:],
                    excluded_tags=[],
                    score=17,
                )

        rules = await domain.get_rules(internal_user_id)

        assert rules == [rule_to_update]

    @pytest.mark.asyncio
    async def test_tags_intersection(
        self, internal_user_id: UserId, five_tags_ids: tuple[int, int, int, int, int]
    ) -> None:
        rule_to_update = await operations.create_or_update_rule(
            internal_user_id, required_tags=five_tags_ids[:3], excluded_tags=[], score=13
        )

        assert set(five_tags_ids[:3]) & set(five_tags_ids[2:])

        with capture_logs() as logs:
            with pytest.raises(errors.TagsIntersection):
                await operations.update_rule(
                    internal_user_id,
                    rule_to_update.id,
                    required_tags=five_tags_ids[:3],
                    excluded_tags=five_tags_ids[2:],
                    score=17,
                )

        rules = await domain.get_rules(internal_user_id)

        assert rules == [rule_to_update]

        assert_logs_has_no_business_event(logs, "rule_updated")


# most of the logic of this function is validated in other tests
class TestGetRules:
    @pytest.mark.asyncio
    async def test_no_rules(self, internal_user_id: UserId) -> None:
        rules = await domain.get_rules(internal_user_id)

        assert rules == []


class TestCountRulesPerUser:

    @pytest.mark.asyncio
    async def test_count_rules(self, internal_user_id: UserId, another_internal_user_id: UserId) -> None:

        numbers_before = await operations.count_rules_per_user()

        await operations.create_or_update_rule(internal_user_id, required_tags=[1, 2], excluded_tags=[], score=3)
        await operations.create_or_update_rule(internal_user_id, required_tags=[], excluded_tags=[2, 3], score=5)
        await operations.create_or_update_rule(
            another_internal_user_id, required_tags=[1, 2], excluded_tags=[3, 4], score=7
        )

        numbers_after = await operations.count_rules_per_user()

        assert numbers_after[internal_user_id] == numbers_before.get(internal_user_id, 0) + 2
        assert numbers_after[another_internal_user_id] == numbers_before.get(another_internal_user_id, 0) + 1
