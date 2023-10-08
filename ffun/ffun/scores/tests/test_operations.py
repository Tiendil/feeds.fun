import uuid

import pytest

from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.scores import domain, operations
from ffun.scores.entities import Rule


class TestCreateOrUpdateRule:

    @pytest.mark.asyncio
    async def test_create_new_rule(self, internal_user_id: uuid.UUID, tree_tags_ids: tuple[int, int, int]) -> None:
        async with TableSizeDelta('s_rules', delta=1):
            await operations.create_or_update_rule(internal_user_id, tree_tags_ids, 13)

        rules = await domain.get_rules(internal_user_id)

        assert len(rules) == 1

        assert rules[0].user_id == internal_user_id
        assert rules[0].tags == set(tree_tags_ids)
        assert rules[0].score == 13

    @pytest.mark.asyncio
    async def test_update_scores_of_existed_rule(self, internal_user_id: uuid.UUID, tree_tags_ids: tuple[int, int, int]) -> None:
        await operations.create_or_update_rule(internal_user_id, tree_tags_ids, 13)

        async with TableSizeNotChanged('s_rules'):
            await operations.create_or_update_rule(internal_user_id, tree_tags_ids, 17)

        rules = await domain.get_rules(internal_user_id)

        assert len(rules) == 1

        assert rules[0].user_id == internal_user_id
        assert rules[0].tags == set(tree_tags_ids)
        assert rules[0].score == 17

    @pytest.mark.asyncio
    async def test_multiple_entities(self,
                                     internal_user_id: uuid.UUID,
                                     another_internal_user_id: uuid.UUID,
                                     tree_tags_ids: tuple[int, int, int]) -> None:

        await operations.create_or_update_rule(internal_user_id, tree_tags_ids[:2], 3)
        await operations.create_or_update_rule(another_internal_user_id, tree_tags_ids[:2], 5)
        await operations.create_or_update_rule(another_internal_user_id, tree_tags_ids[1:], 7)
        await operations.create_or_update_rule(internal_user_id, tree_tags_ids[:2], 11)

        rules = await domain.get_rules(internal_user_id)

        assert len(rules) == 1

        assert rules[0].user_id == internal_user_id
        assert rules[0].tags == set(tree_tags_ids[:2])
        assert rules[0].score == 11

        rules = await domain.get_rules(another_internal_user_id)

        rules.sort(key=lambda r: r.score)

        assert len(rules) == 2

        assert rules[0].user_id == another_internal_user_id
        assert rules[0].tags == set(tree_tags_ids[:2])
        assert rules[0].score == 5

        assert rules[1].user_id == another_internal_user_id
        assert rules[1].tags == set(tree_tags_ids[1:])
        assert rules[1].score == 7
