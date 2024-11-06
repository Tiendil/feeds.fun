import uuid

import pytest

from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.domain.entities import UserId
from ffun.scores import domain, errors, operations


class TestCreateOrUpdateRule:
    @pytest.mark.asyncio
    async def test_create_new_rule(self, internal_user_id: UserId, three_tags_ids: tuple[int, int, int]) -> None:
        with capture_logs() as logs:
            async with TableSizeDelta("s_rules", delta=1):
                created_rule = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        rules = await domain.get_rules(internal_user_id)

        assert rules == [created_rule]

        assert created_rule.user_id == internal_user_id
        assert created_rule.tags == set(three_tags_ids)
        assert created_rule.score == 13

        assert_logs_has_business_event(
            logs,
            "rule_created",
            user_id=internal_user_id,
            rule_id=str(created_rule.id),
            tags=list(three_tags_ids),
            score=13,
        )
        assert_logs_has_no_business_event(logs, "rule_updated")

    @pytest.mark.asyncio
    async def test_tags_order_does_not_affect_creation(
        self, internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        async with TableSizeDelta("s_rules", delta=1):
            created_rule_1 = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)
            created_rule_2 = await operations.create_or_update_rule(internal_user_id, reversed(three_tags_ids), 17)

        assert created_rule_1.tags == created_rule_2.tags

        rules = await domain.get_rules(internal_user_id)

        assert rules == [created_rule_2]

    @pytest.mark.asyncio
    async def test_update_scores_of_existed_rule(
        self, internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        with capture_logs() as logs:
            async with TableSizeNotChanged("s_rules"):
                updated_rule = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 17)

        rules = await domain.get_rules(internal_user_id)

        assert rules == [updated_rule]

        assert updated_rule.user_id == internal_user_id
        assert updated_rule.tags == set(three_tags_ids)
        assert updated_rule.score == 17

        assert_logs_has_business_event(
            logs,
            "rule_updated",
            user_id=internal_user_id,
            rule_id=str(updated_rule.id),
            tags=list(three_tags_ids),
            score=17,
        )
        assert_logs_has_no_business_event(logs, "rule_created")

    @pytest.mark.asyncio
    async def test_multiple_entities(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        await operations.create_or_update_rule(internal_user_id, three_tags_ids[:2], 3)
        await operations.create_or_update_rule(another_internal_user_id, three_tags_ids[:2], 5)
        await operations.create_or_update_rule(another_internal_user_id, three_tags_ids[1:], 7)
        await operations.create_or_update_rule(internal_user_id, three_tags_ids[:2], 11)

        rules = await domain.get_rules(internal_user_id)

        assert len(rules) == 1

        assert rules[0].user_id == internal_user_id
        assert rules[0].tags == set(three_tags_ids[:2])
        assert rules[0].score == 11

        rules = await domain.get_rules(another_internal_user_id)

        rules.sort(key=lambda r: r.score)

        assert len(rules) == 2

        assert rules[0].user_id == another_internal_user_id
        assert rules[0].tags == set(three_tags_ids[:2])
        assert rules[0].score == 5

        assert rules[1].user_id == another_internal_user_id
        assert rules[1].tags == set(three_tags_ids[1:])
        assert rules[1].score == 7


class TestDeleteRule:
    @pytest.mark.asyncio
    async def test_delete_rule(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        rule_to_delete = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)
        rule_2 = await operations.create_or_update_rule(internal_user_id, three_tags_ids[:2], 17)
        rule_3 = await operations.create_or_update_rule(another_internal_user_id, three_tags_ids, 19)

        with capture_logs() as logs:
            async with TableSizeDelta("s_rules", delta=-1):
                await operations.delete_rule(internal_user_id, rule_to_delete.id)

        assert_logs_has_business_event(logs, "rule_deleted", user_id=internal_user_id, rule_id=str(rule_to_delete.id))

        rules = await domain.get_rules(internal_user_id)

        assert rules == [rule_2]

        rules = await domain.get_rules(another_internal_user_id)

        assert rules == [rule_3]

    @pytest.mark.asyncio
    async def test_delete_not_existed_rule(
        self, internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        with capture_logs() as logs:
            async with TableSizeNotChanged("s_rules"):
                await operations.delete_rule(internal_user_id, uuid.uuid4())

        assert_logs_has_no_business_event(logs, "rule_deleted")

    @pytest.mark.asyncio
    async def test_delete_for_wrong_user(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        rule_to_delete = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        async with TableSizeNotChanged("s_rules"):
            await operations.delete_rule(another_internal_user_id, rule_to_delete.id)


class TestUpdateRule:
    @pytest.mark.asyncio
    async def test_update_rule(self, internal_user_id: UserId, three_tags_ids: tuple[int, int, int]) -> None:
        rule_to_update = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        with capture_logs() as logs:
            async with TableSizeNotChanged("s_rules"):
                updated_rule = await operations.update_rule(
                    internal_user_id, rule_to_update.id, three_tags_ids[:2], 17
                )

        assert updated_rule.id == rule_to_update.id
        assert updated_rule.user_id == internal_user_id
        assert updated_rule.tags == set(three_tags_ids[:2])
        assert updated_rule.score == 17

        rules = await domain.get_rules(internal_user_id)

        assert rules == [updated_rule]

        assert_logs_has_business_event(
            logs,
            "rule_updated",
            user_id=internal_user_id,
            rule_id=str(rule_to_update.id),
            tags=list(three_tags_ids[:2]),
            score=17,
        )

    @pytest.mark.asyncio
    async def test_update_not_existed_rule(
        self, internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        with capture_logs() as logs:
            async with TableSizeNotChanged("s_rules"):
                with pytest.raises(errors.NoRuleFound):
                    await operations.update_rule(internal_user_id, uuid.uuid4(), three_tags_ids[:2], 17)

        assert_logs_has_no_business_event(logs, "rule_updated")

    @pytest.mark.asyncio
    async def test_wrong_user(
        self, internal_user_id: UserId, another_internal_user_id: UserId, three_tags_ids: tuple[int, int, int]
    ) -> None:
        rule_to_update = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        async with TableSizeNotChanged("s_rules"):
            with pytest.raises(errors.NoRuleFound):
                await operations.update_rule(another_internal_user_id, rule_to_update.id, three_tags_ids, 17)

        rules = await domain.get_rules(internal_user_id)

        assert rules == [rule_to_update]


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

        await operations.create_or_update_rule(internal_user_id, [1, 2], 3)
        await operations.create_or_update_rule(internal_user_id, [2, 3], 5)
        await operations.create_or_update_rule(another_internal_user_id, [1, 2], 7)

        numbers_after = await operations.count_rules_per_user()

        assert numbers_after[internal_user_id] == numbers_before.get(internal_user_id, 0) + 2
        assert numbers_after[another_internal_user_id] == numbers_before.get(another_internal_user_id, 0) + 1
