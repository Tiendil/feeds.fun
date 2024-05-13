import uuid

import pytest

from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.scores import domain, errors, operations


class TestCreateOrUpdateRule:
    @pytest.mark.asyncio
    async def test_create_new_rule(self, internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]) -> None:
        async with TableSizeDelta("s_rules", delta=1):
            created_rule = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        rules = await domain.get_rules(internal_user_id)

        assert rules == [created_rule]

        assert created_rule.user_id == internal_user_id
        assert created_rule.tags == set(three_tags_ids)
        assert created_rule.score == 13

    @pytest.mark.asyncio
    async def test_tags_order_does_not_affect_creation(
        self, internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]
    ) -> None:
        async with TableSizeDelta("s_rules", delta=1):
            created_rule_1 = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)
            created_rule_2 = await operations.create_or_update_rule(internal_user_id, reversed(three_tags_ids), 17)

        assert created_rule_1.tags == created_rule_2.tags

        rules = await domain.get_rules(internal_user_id)

        assert rules == [created_rule_2]

    @pytest.mark.asyncio
    async def test_update_scores_of_existed_rule(
        self, internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]
    ) -> None:
        await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        async with TableSizeNotChanged("s_rules"):
            updated_rule = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 17)

        rules = await domain.get_rules(internal_user_id)

        assert rules == [updated_rule]

        assert updated_rule.user_id == internal_user_id
        assert updated_rule.tags == set(three_tags_ids)
        assert updated_rule.score == 17

    @pytest.mark.asyncio
    async def test_multiple_entities(
        self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]
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
        self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]
    ) -> None:
        rule_to_delete = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)
        rule_2 = await operations.create_or_update_rule(internal_user_id, three_tags_ids[:2], 17)
        rule_3 = await operations.create_or_update_rule(another_internal_user_id, three_tags_ids, 19)

        async with TableSizeDelta("s_rules", delta=-1):
            await operations.delete_rule(internal_user_id, rule_to_delete.id)

        rules = await domain.get_rules(internal_user_id)

        assert rules == [rule_2]

        rules = await domain.get_rules(another_internal_user_id)

        assert rules == [rule_3]

    @pytest.mark.asyncio
    async def test_delete_not_existed_rule(
        self, internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]
    ) -> None:
        async with TableSizeNotChanged("s_rules"):
            await operations.delete_rule(internal_user_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_delete_for_wrong_user(
        self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]
    ) -> None:
        rule_to_delete = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        async with TableSizeNotChanged("s_rules"):
            await operations.delete_rule(another_internal_user_id, rule_to_delete.id)


class TestUpdateRule:
    @pytest.mark.asyncio
    async def test_update_rule(self, internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]) -> None:
        rule_to_update = await operations.create_or_update_rule(internal_user_id, three_tags_ids, 13)

        async with TableSizeNotChanged("s_rules"):
            updated_rule = await operations.update_rule(internal_user_id, rule_to_update.id, three_tags_ids[:2], 17)

        assert updated_rule.id == rule_to_update.id
        assert updated_rule.user_id == internal_user_id
        assert updated_rule.tags == set(three_tags_ids[:2])
        assert updated_rule.score == 17

        rules = await domain.get_rules(internal_user_id)

        assert rules == [updated_rule]

    @pytest.mark.asyncio
    async def test_update_not_existed_rule(
        self, internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]
    ) -> None:
        async with TableSizeNotChanged("s_rules"):
            with pytest.raises(errors.NoRuleFound):
                await operations.update_rule(internal_user_id, uuid.uuid4(), three_tags_ids[:2], 17)

    @pytest.mark.asyncio
    async def test_wrong_user(
        self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID, three_tags_ids: tuple[int, int, int]
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
    async def test_no_rules(self, internal_user_id: uuid.UUID) -> None:
        rules = await domain.get_rules(internal_user_id)

        assert rules == []
