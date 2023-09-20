import datetime
import uuid
from typing import Any

import pytest
from pytest_mock import MockerFixture

from ffun.application.resources import Resource as AppResource
from ffun.application.user_settings import UserSetting
from ffun.feeds_links import domain as fl_domain
from ffun.openai import errors
from ffun.openai.entities import APIKeyUsage, KeyStatus, UserKeyInfo
from ffun.openai.keys_rotator import (
    _api_key_is_working,
    _choose_user,
    _filter_out_users_for_whome_entry_is_too_old,
    _filter_out_users_with_overused_keys,
    _filter_out_users_with_wrong_keys,
    _filter_out_users_without_keys,
    _filters,
    _find_best_user_with_key,
    _get_candidates,
    _get_user_key_infos,
    _use_key,
    _users_for_feed,
    api_key_for_feed_entry,
)
from ffun.openai.keys_statuses import Statuses, statuses
from ffun.resources import domain as r_domain
from ffun.resources import entities as r_entities
from ffun.user_settings import domain as us_domain


class TestAPIKeyIsWorking:
    @pytest.mark.asyncio
    async def test_is_working(self, openai_key: str) -> None:
        statuses.set(openai_key, KeyStatus.works)
        assert await _api_key_is_working(openai_key)

    @pytest.mark.parametrize(
        "status", [status for status in KeyStatus if status not in [KeyStatus.works, KeyStatus.unknown]]
    )
    @pytest.mark.asyncio
    async def test_guaranted_broken(self, status: KeyStatus, openai_key: str) -> None:
        statuses.set(openai_key, status)
        assert not await _api_key_is_working(openai_key)

    @pytest.mark.parametrize("status, expected_result", [(KeyStatus.works, True), (KeyStatus.broken, False)])
    @pytest.mark.asyncio
    async def test_unknown(
        self, status: KeyStatus, expected_result: bool, statuses: Statuses, mocker: MockerFixture, openai_key: str
    ) -> None:
        assert statuses.get(openai_key) == KeyStatus.unknown

        mocker.patch("ffun.openai.client.check_api_key", return_value=status)

        assert await _api_key_is_working(openai_key) == expected_result


class TestFilterOutUsersWithWrongKeys:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        assert await _filter_out_users_with_wrong_keys([]) == []

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        assert five_user_key_infos[1].api_key
        assert five_user_key_infos[3].api_key

        statuses.set(five_user_key_infos[1].api_key, KeyStatus.broken)
        statuses.set(five_user_key_infos[3].api_key, KeyStatus.quota)

        infos = await _filter_out_users_with_wrong_keys(five_user_key_infos)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersWithoutKeys:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        assert await _filter_out_users_without_keys([]) == []

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        five_user_key_infos[1].api_key = None
        five_user_key_infos[3].api_key = None

        infos = await _filter_out_users_without_keys(five_user_key_infos)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersForWhomeEntryIsTooOld:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        assert await _filter_out_users_for_whome_entry_is_too_old([], datetime.timedelta(days=1)) == []

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        for info, days in zip(five_user_key_infos, [5, 2, 3, 1, 4]):
            info.process_entries_not_older_than = datetime.timedelta(days=days)

        infos = await _filter_out_users_for_whome_entry_is_too_old(five_user_key_infos, datetime.timedelta(days=3))

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersWithOverusedKeys:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        assert await _filter_out_users_with_overused_keys([], 100) == []

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        for info, max_tokens_in_month in zip(five_user_key_infos, [201, 100, 300, 200, 500]):
            info.tokens_used = 50
            info.max_tokens_in_month = max_tokens_in_month

        infos = await _filter_out_users_with_overused_keys(five_user_key_infos, 150)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestUsersForFeed:
    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        assert await _users_for_feed(feed_id=uuid.uuid4()) == set()

    @pytest.mark.asyncio
    async def test_linked_users(self, five_internal_user_ids: list[uuid.UUID], saved_feed_id: uuid.UUID) -> None:
        indexes = [1, 3]

        for i in indexes:
            await fl_domain.add_link(five_internal_user_ids[i], saved_feed_id)

        assert await _users_for_feed(feed_id=saved_feed_id) == {five_internal_user_ids[i] for i in indexes}

    @pytest.mark.asyncio
    async def test_collections(
        self, five_internal_user_ids: list[uuid.UUID], saved_collection_feed_id: uuid.UUID
    ) -> None:
        indexes = [1, 3]

        await us_domain.remove_setting_for_all_users(UserSetting.openai_allow_use_key_for_collections)

        for i in indexes:
            await us_domain.save_setting(
                user_id=five_internal_user_ids[i], kind=UserSetting.openai_allow_use_key_for_collections, value=True
            )

        assert await _users_for_feed(feed_id=saved_collection_feed_id) == {five_internal_user_ids[i] for i in indexes}

    @pytest.mark.asyncio
    async def test_merging_users(
        self, five_internal_user_ids: list[uuid.UUID], saved_collection_feed_id: uuid.UUID
    ) -> None:
        await us_domain.remove_setting_for_all_users(UserSetting.openai_allow_use_key_for_collections)

        await fl_domain.add_link(five_internal_user_ids[1], saved_collection_feed_id)

        await us_domain.save_setting(
            user_id=five_internal_user_ids[3], kind=UserSetting.openai_allow_use_key_for_collections, value=True
        )

        assert await _users_for_feed(feed_id=saved_collection_feed_id) == {five_internal_user_ids[i] for i in [1, 3]}


class TestChooseUser:
    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        interval_started_at = r_domain.month_interval_start()

        with pytest.raises(errors.NoKeyFoundForFeed):
            assert await _choose_user(infos=[], reserved_tokens=0, interval_started_at=interval_started_at)

    @pytest.mark.asyncio
    async def test_no_users_with_resources(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        interval_started_at = r_domain.month_interval_start()

        with pytest.raises(errors.NoKeyFoundForFeed):
            assert await _choose_user(
                infos=five_user_key_infos,
                reserved_tokens=max(info.max_tokens_in_month for info in five_user_key_infos) + 1,
                interval_started_at=interval_started_at,
            )

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        interval_started_at = r_domain.month_interval_start()

        max_tokens = max(info.max_tokens_in_month for info in five_user_key_infos) + 1

        five_user_key_infos[2].max_tokens_in_month = max_tokens + five_user_key_infos[2].tokens_used

        info = await _choose_user(
            infos=five_user_key_infos, reserved_tokens=max_tokens, interval_started_at=interval_started_at
        )

        assert info == five_user_key_infos[2]


class TestUseKey:
    @pytest.mark.asyncio
    async def test_success(self, internal_user_id: uuid.UUID, openai_key: str) -> None:
        interval_started_at = r_domain.month_interval_start()

        reserved_tokens = 567

        await r_domain.try_to_reserve(
            user_id=internal_user_id,
            kind=AppResource.openai_tokens,
            interval_started_at=interval_started_at,
            amount=reserved_tokens,
            limit=1000,
        )

        resources = await r_domain.load_resources(
            user_ids=[internal_user_id], kind=AppResource.openai_tokens, interval_started_at=interval_started_at
        )

        used_tokens = 132

        async with _use_key(
            user_id=internal_user_id,
            api_key=openai_key,
            reserved_tokens=reserved_tokens,
            interval_started_at=interval_started_at,
        ) as key_usage:
            assert key_usage == APIKeyUsage(user_id=internal_user_id, api_key=openai_key, used_tokens=None)
            key_usage.used_tokens = used_tokens

        resources = await r_domain.load_resources(
            user_ids=[internal_user_id], kind=AppResource.openai_tokens, interval_started_at=interval_started_at
        )

        assert resources == {
            internal_user_id: r_entities.Resource(
                user_id=internal_user_id,
                kind=AppResource.openai_tokens,
                interval_started_at=interval_started_at,
                used=used_tokens,
                reserved=0,
            )
        }

    @pytest.mark.asyncio
    async def test_error(self, internal_user_id: uuid.UUID, openai_key: str) -> None:
        interval_started_at = r_domain.month_interval_start()

        reserved_tokens = 567

        await r_domain.try_to_reserve(
            user_id=internal_user_id,
            kind=AppResource.openai_tokens,
            interval_started_at=interval_started_at,
            amount=reserved_tokens,
            limit=1000,
        )

        resources = await r_domain.load_resources(
            user_ids=[internal_user_id], kind=AppResource.openai_tokens, interval_started_at=interval_started_at
        )

        class FakeError(Exception):
            pass

        with pytest.raises(FakeError):
            async with _use_key(
                user_id=internal_user_id,
                api_key=openai_key,
                reserved_tokens=reserved_tokens,
                interval_started_at=interval_started_at,
            ):
                raise FakeError()

        resources = await r_domain.load_resources(
            user_ids=[internal_user_id], kind=AppResource.openai_tokens, interval_started_at=interval_started_at
        )

        assert resources == {
            internal_user_id: r_entities.Resource(
                user_id=internal_user_id,
                kind=AppResource.openai_tokens,
                interval_started_at=interval_started_at,
                used=reserved_tokens,
                reserved=0,
            )
        }


class TestGetUserKeyInfos:
    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        interval_started_at = r_domain.month_interval_start()

        assert await _get_user_key_infos(user_ids=[], interval_started_at=interval_started_at) == []

    @pytest.mark.asyncio
    async def test_works(self, five_internal_user_ids: list[uuid.UUID]) -> None:
        from ffun.application.resources import Resource as AppResource
        from ffun.application.user_settings import UserSetting

        interval_started_at = r_domain.month_interval_start()

        keys = [uuid.uuid4().hex for _ in range(5)]
        max_tokens_in_month = [(i + 1) * 1000 for i in range(5)]
        days = list(range(5))
        used_tokens = [i * 100 for i in range(5)]
        reserved_tokens = [i * 10 for i in range(5)]

        for i, user_id in enumerate(five_internal_user_ids):
            await us_domain.save_setting(user_id=user_id, kind=UserSetting.openai_api_key, value=keys[i])

            await us_domain.save_setting(
                user_id=user_id, kind=UserSetting.openai_max_tokens_in_month, value=max_tokens_in_month[i]
            )

            await us_domain.save_setting(
                user_id=user_id, kind=UserSetting.openai_process_entries_not_older_than, value=days[i]
            )

            await r_domain.try_to_reserve(
                user_id=user_id,
                kind=AppResource.openai_tokens,
                interval_started_at=interval_started_at,
                amount=reserved_tokens[i],
                limit=max_tokens_in_month[i],
            )

            await r_domain.convert_reserved_to_used(
                user_id=user_id,
                kind=AppResource.openai_tokens,
                interval_started_at=interval_started_at,
                used=used_tokens[i],
                reserved=0,
            )

        infos = await _get_user_key_infos(five_internal_user_ids, interval_started_at)

        assert infos == [
            UserKeyInfo(
                user_id=five_internal_user_ids[i],
                api_key=keys[i],
                max_tokens_in_month=max_tokens_in_month[i],
                process_entries_not_older_than=datetime.timedelta(days=days[i]),
                tokens_used=used_tokens[i] + reserved_tokens[i],
            )
            for i in range(5)
        ]


class TestGetCandidates:
    @pytest.mark.asyncio
    async def test_no_users(self, saved_feed_id: uuid.UUID) -> None:
        interval_started_at = r_domain.month_interval_start()

        assert (
            await _get_candidates(
                feed_id=saved_feed_id,
                interval_started_at=interval_started_at,
                entry_age=datetime.timedelta(days=1),
                reserved_tokens=100,
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_default_filters(self) -> None:
        assert _filters == (
            _filter_out_users_without_keys,
            _filter_out_users_for_whome_entry_is_too_old,
            _filter_out_users_with_wrong_keys,
            _filter_out_users_with_overused_keys,
        )

    @pytest.mark.asyncio
    async def test_filters_used(self, saved_feed_id: uuid.UUID, five_internal_user_ids: list[uuid.UUID]) -> None:
        for user_id in five_internal_user_ids:
            await fl_domain.add_link(user_id, saved_feed_id)

        interval_started_at = r_domain.month_interval_start()

        filter_1_users = [five_internal_user_ids[0], five_internal_user_ids[2], five_internal_user_ids[4]]
        filter_2_users = five_internal_user_ids
        filter_3_users = five_internal_user_ids[1:]

        def create_filter(filter_users: list[uuid.UUID]) -> Any:
            async def _filter(infos: list[UserKeyInfo], **kwargs: Any) -> list[UserKeyInfo]:
                return [info for info in infos if info.user_id in filter_users]

            return _filter

        infos = await _get_candidates(
            feed_id=saved_feed_id,
            interval_started_at=interval_started_at,
            entry_age=datetime.timedelta(days=1),
            reserved_tokens=100,
            filters=(create_filter(filter_1_users), create_filter(filter_2_users), create_filter(filter_3_users)),
        )

        assert {info.user_id for info in infos} == {five_internal_user_ids[2], five_internal_user_ids[4]}

    @pytest.mark.asyncio
    async def test_all_users_excluded(self, saved_feed_id: uuid.UUID, five_internal_user_ids: list[uuid.UUID]) -> None:
        for user_id in five_internal_user_ids:
            await fl_domain.add_link(user_id, saved_feed_id)

        interval_started_at = r_domain.month_interval_start()

        filter_1_users = [five_internal_user_ids[0], five_internal_user_ids[2], five_internal_user_ids[4]]

        def create_filter(filter_users: list[uuid.UUID]) -> Any:
            async def _filter(infos: list[UserKeyInfo], **kwargs: Any) -> list[UserKeyInfo]:
                return [info for info in infos if info.user_id in filter_users]

            return _filter

        async def _filter_3(infos: list[UserKeyInfo], **kwargs: Any) -> list[UserKeyInfo]:
            raise Exception("Should not be called")

        infos = await _get_candidates(
            feed_id=saved_feed_id,
            interval_started_at=interval_started_at,
            entry_age=datetime.timedelta(days=1),
            reserved_tokens=100,
            filters=(create_filter(filter_1_users), create_filter([]), _filter_3),
        )

        assert infos == []


class TestFindBestUserWithKey:
    @pytest.mark.asyncio
    async def test_no_users(self, saved_feed_id: uuid.UUID) -> None:
        with pytest.raises(errors.NoKeyFoundForFeed):
            await _find_best_user_with_key(
                feed_id=saved_feed_id,
                entry_age=datetime.timedelta(days=1),
                interval_started_at=r_domain.month_interval_start(),
                reserved_tokens=100,
            )

    @pytest.mark.asyncio
    async def test_works(self, saved_feed_id: uuid.UUID, five_user_key_infos: list[UserKeyInfo]) -> None:
        for info in five_user_key_infos:
            await fl_domain.add_link(info.user_id, saved_feed_id)

        chosen_users: set[uuid.UUID] = set()

        interval_started_at = r_domain.month_interval_start()

        used_tokens = 7

        for _ in range(len(five_user_key_infos)):
            info = await _find_best_user_with_key(
                feed_id=saved_feed_id,
                entry_age=datetime.timedelta(days=0),
                interval_started_at=interval_started_at,
                reserved_tokens=used_tokens,
            )

            assert info.tokens_used == five_user_key_infos[0].tokens_used

            chosen_users.add(info.user_id)

            await r_domain.convert_reserved_to_used(
                user_id=info.user_id,
                kind=AppResource.openai_tokens,
                interval_started_at=interval_started_at,
                used=used_tokens,
                reserved=used_tokens,
            )

        assert chosen_users == {info.user_id for info in five_user_key_infos}

        # next user will have more used tokens
        info = await _find_best_user_with_key(
            feed_id=saved_feed_id,
            entry_age=datetime.timedelta(days=0),
            interval_started_at=interval_started_at,
            reserved_tokens=used_tokens,
        )

        assert info.tokens_used == five_user_key_infos[0].tokens_used + used_tokens


class TestApiKeyForFeedEntry:
    @pytest.mark.asyncio
    async def test_no_users(self, saved_feed_id: uuid.UUID) -> None:
        with pytest.raises(errors.NoKeyFoundForFeed):
            async with api_key_for_feed_entry(
                feed_id=saved_feed_id, entry_age=datetime.timedelta(days=0), reserved_tokens=1
            ):
                pass

    @pytest.mark.asyncio
    async def test_works(self, saved_feed_id: uuid.UUID, five_user_key_infos: list[UserKeyInfo]) -> None:
        for info in five_user_key_infos:
            await fl_domain.add_link(info.user_id, saved_feed_id)

        chosen_users: set[uuid.UUID] = set()

        interval_started_at = r_domain.month_interval_start()

        used_tokens = 7

        for _ in range(len(five_user_key_infos)):
            async with api_key_for_feed_entry(
                feed_id=saved_feed_id, entry_age=datetime.timedelta(days=0), reserved_tokens=13
            ) as key_usage:
                key_usage.used_tokens = used_tokens
                chosen_users.add(key_usage.user_id)

        assert chosen_users == {info.user_id for info in five_user_key_infos}

        # next user will have more used tokens
        info = await _find_best_user_with_key(
            feed_id=saved_feed_id,
            entry_age=datetime.timedelta(days=0),
            interval_started_at=interval_started_at,
            reserved_tokens=1,
        )

        assert info.tokens_used == five_user_key_infos[0].tokens_used + used_tokens
