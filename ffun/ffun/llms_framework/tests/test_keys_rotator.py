import datetime
import decimal
import uuid
from typing import Any

import pytest
from pytest_mock import MockerFixture

from ffun.application.resources import Resource as AppResource
from ffun.domain.datetime_intervals import month_interval_start
from ffun.feeds.entities import FeedId
from ffun.feeds_links import domain as fl_domain
from ffun.llms_framework import errors
from ffun.llms_framework.entities import (
    APIKeyUsage,
    KeyStatus,
    LLMConfiguration,
    Provider,
    SelectKeyContext,
    UserKeyInfo,
)
from ffun.llms_framework.provider_interface import ProviderTest, ProviderInterface
from ffun.llms_framework.keys_rotator import (
    _api_key_is_working,
    _choose_collections_key,
    _choose_general_key,
    _choose_user,
    _choose_user_key,
    _filter_out_users_for_whome_entry_is_too_old,
    _filter_out_users_with_overused_keys,
    _filter_out_users_with_wrong_keys,
    _filter_out_users_without_keys,
    _filters,
    _find_best_user_with_key,
    _get_candidates,
    _get_user_key_infos,
    _key_selectors,
    choose_api_key,
    use_api_key,
)
from ffun.llms_framework.providers import llm_providers
from ffun.resources import domain as r_domain
from ffun.resources import entities as r_entities
from ffun.user_settings import domain as us_domain

_llm_config = LLMConfiguration(
    model="test-model",
    system="some system prompt",
    max_return_tokens=1017,
    text_parts_intersection=113,
    temperature=decimal.Decimal("0.3"),
    top_p=decimal.Decimal("0.9"),
    presence_penalty=decimal.Decimal("0.5"),
    frequency_penalty=decimal.Decimal("0.75"),
)


class TestAPIKeyIsWorking:
    @pytest.mark.asyncio
    async def test_is_working(self, fake_llm_provider: ProviderTest, fake_api_key: str) -> None:
        fake_llm_provider.api_keys_statuses.set(fake_api_key, KeyStatus.works)
        assert await _api_key_is_working(fake_llm_provider, _llm_config, fake_api_key)

    @pytest.mark.parametrize(
        "status", [status for status in KeyStatus if status not in [KeyStatus.works, KeyStatus.unknown]]
    )
    @pytest.mark.asyncio
    async def test_guaranted_broken(self, fake_llm_provider: ProviderTest, status: KeyStatus, fake_api_key: str) -> None:
        fake_llm_provider.api_keys_statuses.set(fake_api_key, status)
        assert not await _api_key_is_working(fake_llm_provider, _llm_config, fake_api_key)

    @pytest.mark.parametrize("status, expected_result", [(KeyStatus.works, True), (KeyStatus.broken, False)])
    @pytest.mark.asyncio
    async def test_unknown(
        self, fake_llm_provider: ProviderTest, status: KeyStatus, expected_result: bool, mocker: MockerFixture, fake_api_key: str
    ) -> None:
        assert fake_llm_provider.api_keys_statuses.get(fake_api_key) == KeyStatus.unknown

        mocker.patch("ffun.llms_framework.provider_interface.ProviderTest.check_api_key", return_value=status)

        assert await _api_key_is_working(fake_llm_provider, _llm_config, fake_api_key) == expected_result


class TestFilterOutUsersWithWrongKeys:
    @pytest.mark.asyncio
    async def test_empty_list(self, fake_llm_provider: ProviderTest) -> None:
        assert await _filter_out_users_with_wrong_keys(fake_llm_provider, _llm_config, []) == []

    @pytest.mark.asyncio
    async def test_all_working(self, fake_llm_provider: ProviderTest, five_user_key_infos: list[UserKeyInfo]) -> None:
        assert five_user_key_infos[1].api_key
        assert five_user_key_infos[3].api_key

        fake_llm_provider.api_keys_statuses.set(five_user_key_infos[1].api_key, KeyStatus.broken)
        fake_llm_provider.api_keys_statuses.set(five_user_key_infos[3].api_key, KeyStatus.quota)

        infos = await _filter_out_users_with_wrong_keys(fake_llm_provider, _llm_config, five_user_key_infos)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersWithoutKeys:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        assert await _filter_out_users_without_keys([]) == []

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        five_user_key_infos[1] = five_user_key_infos[1].replace(api_key=None)
        five_user_key_infos[3] = five_user_key_infos[3].replace(api_key=None)

        infos = await _filter_out_users_without_keys(five_user_key_infos)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersForWhomeEntryIsTooOld:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        assert await _filter_out_users_for_whome_entry_is_too_old([], datetime.timedelta(days=1)) == []

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        # for info, days in zip(five_user_key_infos, [5, 2, 3, 1, 4]):
        #     info.process_entries_not_older_than = datetime.timedelta(days=days)

        for i, days in enumerate([5, 2, 3, 1, 4]):
            five_user_key_infos[i] = five_user_key_infos[i].replace(
                process_entries_not_older_than=datetime.timedelta(days=days)
            )

        infos = await _filter_out_users_for_whome_entry_is_too_old(five_user_key_infos, datetime.timedelta(days=3))

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestFilterOutUsersWithOverusedKeys:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        assert await _filter_out_users_with_overused_keys([], 100) == []

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        # for info, max_tokens_in_month in zip(five_user_key_infos, [201, 100, 300, 200, 500]):
        #     info.tokens_used = 50
        #     info.max_tokens_in_month = max_tokens_in_month

        for i, max_tokens_in_month in enumerate([201, 100, 300, 200, 500]):
            five_user_key_infos[i] = five_user_key_infos[i].replace(
                tokens_used=50, max_tokens_in_month=max_tokens_in_month
            )

        infos = await _filter_out_users_with_overused_keys(five_user_key_infos, 150)

        assert infos == [five_user_key_infos[i] for i in [0, 2, 4]]


class TestChooseUser:
    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        interval_started_at = month_interval_start()

        assert await _choose_user(infos=[], reserved_tokens=0, interval_started_at=interval_started_at) is None

    @pytest.mark.asyncio
    async def test_no_users_with_resources(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        interval_started_at = month_interval_start()

        info = await _choose_user(
            infos=five_user_key_infos,
            reserved_tokens=max(info.max_tokens_in_month for info in five_user_key_infos) + 1,
            interval_started_at=interval_started_at,
        )

        assert info is None

    @pytest.mark.asyncio
    async def test_all_working(self, five_user_key_infos: list[UserKeyInfo]) -> None:
        interval_started_at = month_interval_start()

        max_tokens = max(info.max_tokens_in_month for info in five_user_key_infos) + 1

        five_user_key_infos[2] = five_user_key_infos[2].replace(
            max_tokens_in_month=max_tokens + five_user_key_infos[2].tokens_used
        )

        info = await _choose_user(
            infos=five_user_key_infos, reserved_tokens=max_tokens, interval_started_at=interval_started_at
        )

        assert info == five_user_key_infos[2]


class TestGetUserKeyInfos:
    @pytest.mark.asyncio
    async def test_no_users(self) -> None:
        interval_started_at = month_interval_start()

        assert await _get_user_key_infos(user_ids=[], interval_started_at=interval_started_at) == []

    @pytest.mark.asyncio
    async def test_works(self, five_internal_user_ids: list[uuid.UUID]) -> None:
        from ffun.application.resources import Resource as AppResource
        from ffun.application.user_settings import UserSetting

        interval_started_at = month_interval_start()

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
    async def test_no_users(self, fake_llm_provider: ProviderTest, saved_feed_id: FeedId) -> None:
        interval_started_at = month_interval_start()

        assert (
            await _get_candidates(
                llm=fake_llm_provider,
                llm_config=_llm_config,
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
    async def test_filters_used(self, fake_llm_provider: ProviderTest, saved_feed_id: FeedId, five_internal_user_ids: list[uuid.UUID]) -> None:
        for user_id in five_internal_user_ids:
            await fl_domain.add_link(user_id, saved_feed_id)

        interval_started_at = month_interval_start()

        filter_1_users = [five_internal_user_ids[0], five_internal_user_ids[2], five_internal_user_ids[4]]
        filter_2_users = five_internal_user_ids
        filter_3_users = five_internal_user_ids[1:]

        def create_filter(filter_users: list[uuid.UUID]) -> Any:
            async def _filter(infos: list[UserKeyInfo], **kwargs: Any) -> list[UserKeyInfo]:
                return [info for info in infos if info.user_id in filter_users]

            return _filter

        infos = await _get_candidates(
            llm=fake_llm_provider,
            llm_config=_llm_config,
            feed_id=saved_feed_id,
            interval_started_at=interval_started_at,
            entry_age=datetime.timedelta(days=1),
            reserved_tokens=100,
            filters=(create_filter(filter_1_users), create_filter(filter_2_users), create_filter(filter_3_users)),
        )

        assert {info.user_id for info in infos} == {five_internal_user_ids[2], five_internal_user_ids[4]}

    @pytest.mark.asyncio
    async def test_all_users_excluded(self, fake_llm_provider: ProviderTest, saved_feed_id: FeedId, five_internal_user_ids: list[uuid.UUID]) -> None:
        for user_id in five_internal_user_ids:
            await fl_domain.add_link(user_id, saved_feed_id)

        interval_started_at = month_interval_start()

        filter_1_users = [five_internal_user_ids[0], five_internal_user_ids[2], five_internal_user_ids[4]]

        def create_filter(filter_users: list[uuid.UUID]) -> Any:
            async def _filter(infos: list[UserKeyInfo], **kwargs: Any) -> list[UserKeyInfo]:
                return [info for info in infos if info.user_id in filter_users]

            return _filter

        async def _filter_3(infos: list[UserKeyInfo], **kwargs: Any) -> list[UserKeyInfo]:
            raise Exception("Should not be called")

        infos = await _get_candidates(
            llm=fake_llm_provider,
            llm_config=_llm_config,
            feed_id=saved_feed_id,
            interval_started_at=interval_started_at,
            entry_age=datetime.timedelta(days=1),
            reserved_tokens=100,
            filters=(create_filter(filter_1_users), create_filter([]), _filter_3),
        )

        assert infos == []


class TestFindBestUserWithKey:
    @pytest.mark.asyncio
    async def test_no_users(self, fake_llm_provider: ProviderTest, saved_feed_id: FeedId) -> None:
        info = await _find_best_user_with_key(
            llm=fake_llm_provider,
            llm_config=_llm_config,
            feed_id=saved_feed_id,
            entry_age=datetime.timedelta(days=1),
            interval_started_at=month_interval_start(),
            reserved_tokens=100,
        )

        assert info is None

    @pytest.mark.asyncio
    async def test_works(self, fake_llm_provider: ProviderTest, saved_feed_id: FeedId, five_user_key_infos: list[UserKeyInfo]) -> None:
        for user_key_info in five_user_key_infos:
            await fl_domain.add_link(user_key_info.user_id, saved_feed_id)

        chosen_users: set[uuid.UUID] = set()

        interval_started_at = month_interval_start()

        used_tokens = 7

        for _ in range(len(five_user_key_infos)):
            info = await _find_best_user_with_key(
                llm=fake_llm_provider,
                llm_config=_llm_config,
                feed_id=saved_feed_id,
                entry_age=datetime.timedelta(days=0),
                interval_started_at=interval_started_at,
                reserved_tokens=used_tokens,
            )

            assert info is not None
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
            llm=fake_llm_provider,
            llm_config=_llm_config,
            feed_id=saved_feed_id,
            entry_age=datetime.timedelta(days=0),
            interval_started_at=interval_started_at,
            reserved_tokens=used_tokens,
        )

        assert info is not None
        assert info.tokens_used == five_user_key_infos[0].tokens_used + used_tokens


@pytest.fixture
def select_key_context(saved_feed_id: FeedId) -> SelectKeyContext:
    return SelectKeyContext(
        llm_config=_llm_config,
        collections_api_key=None,
        general_api_key=None,
        feed_id=saved_feed_id,
        entry_age=datetime.timedelta(seconds=0),
        reserved_tokens=0,
    )


class TestChooseGeneralKey:

    @pytest.mark.asyncio
    async def test_no_general_key_specified(self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext) -> None:
        # mocker.patch("ffun.openai.settings.settings.general_api_key", None)

        assert select_key_context.general_api_key is None

        assert await _choose_general_key(fake_llm_provider, select_key_context) is None

    @pytest.mark.asyncio
    async def test_general_key_specified(self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext) -> None:
        key = uuid.uuid4().hex

        select_key_context = select_key_context.replace(general_api_key=key)

        usage = await _choose_general_key(fake_llm_provider, select_key_context)

        assert usage == APIKeyUsage(
            user_id=None,
            api_key=key,
            reserved_tokens=select_key_context.reserved_tokens,
            used_tokens=None,
            interval_started_at=select_key_context.interval_started_at,
        )


class TestChooseCollectionsKey:

    @pytest.mark.asyncio
    async def test_no_collections_key_specified(self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext) -> None:
        assert select_key_context.collections_api_key is None

        assert await _choose_collections_key(fake_llm_provider, select_key_context) is None

    @pytest.mark.asyncio
    async def test_collections_key_specified__in_collection(
        self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext, mocker: MockerFixture
    ) -> None:
        key = uuid.uuid4().hex

        select_key_context = select_key_context.replace(collections_api_key=key)

        # TODO: remove mocking after collections will be reworked in https://github.com/Tiendil/feeds.fun/issues/246
        mocker.patch("ffun.feeds_collections.domain.is_feed_in_collections", return_value=True)

        usage = await _choose_collections_key(fake_llm_provider, select_key_context)

        assert usage == APIKeyUsage(
            user_id=None,
            api_key=key,
            reserved_tokens=select_key_context.reserved_tokens,
            used_tokens=None,
            interval_started_at=select_key_context.interval_started_at,
        )

    @pytest.mark.asyncio
    async def test_collections_key_specified__not_in_collection(
        self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext, mocker: MockerFixture
    ) -> None:
        key = uuid.uuid4().hex

        select_key_context = select_key_context.replace(collections_api_key=key)

        # TODO: remove mocking after collections will be reworked in
        mocker.patch("ffun.feeds_collections.domain.is_feed_in_collections", return_value=False)

        assert await _choose_collections_key(fake_llm_provider, select_key_context) is None


class TestChooseUserKey:

    @pytest.mark.asyncio
    async def test_no_users(self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext) -> None:
        assert await _choose_user_key(fake_llm_provider, select_key_context) is None

    @pytest.mark.asyncio
    async def test_found_user(
        self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext, saved_feed_id: FeedId, five_user_key_infos: list[UserKeyInfo]
    ) -> None:
        info = five_user_key_infos[0]

        assert info.api_key is not None

        await fl_domain.add_link(info.user_id, saved_feed_id)

        usage = await _choose_user_key(fake_llm_provider, select_key_context)

        assert usage == APIKeyUsage(
            user_id=info.user_id,
            api_key=info.api_key,
            reserved_tokens=select_key_context.reserved_tokens,
            used_tokens=None,
            interval_started_at=select_key_context.interval_started_at,
        )


class TestKeySelectors:

    def test_order(self) -> None:
        """Just double protection from overriding this constant"""
        assert _key_selectors == (_choose_general_key, _choose_collections_key, _choose_user_key)


class TestChooseApiKey:

    def create_selector(self, api_key: str | None) -> Any:
        async def success_selector(llm: ProviderInterface, context: SelectKeyContext) -> APIKeyUsage:
            assert api_key is not None

            return APIKeyUsage(
                user_id=uuid.uuid4(),
                api_key=api_key,
                reserved_tokens=context.reserved_tokens,
                used_tokens=None,
                interval_started_at=context.interval_started_at,
            )

        async def fail_selector(llm: ProviderInterface, context: SelectKeyContext) -> None:
            return None

        return success_selector if api_key is not None else fail_selector

    @pytest.mark.asyncio
    async def test_no_selectors(self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext) -> None:
        key_usage = await choose_api_key(fake_llm_provider, select_key_context, selectors=[])
        assert key_usage is None

    @pytest.mark.asyncio
    async def test_key_not_found(self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext) -> None:
        selectors = [self.create_selector(None), self.create_selector(None), self.create_selector(None)]

        key_usage = await choose_api_key(fake_llm_provider, select_key_context, selectors=selectors)

        assert key_usage is None

    @pytest.mark.asyncio
    async def test_choose_first(self, fake_llm_provider: ProviderTest, select_key_context: SelectKeyContext) -> None:
        expected_key = uuid.uuid4().hex

        selectors = [
            self.create_selector(None),
            self.create_selector(expected_key),
            self.create_selector(None),
            self.create_selector(uuid.uuid4().hex),
            self.create_selector(None),
        ]

        usage = await choose_api_key(fake_llm_provider, select_key_context, selectors=selectors)

        assert usage.api_key == expected_key


class TestUseApiKey:

    @pytest.mark.asyncio
    async def test_success(self, internal_user_id: uuid.UUID, fake_api_key: str) -> None:

        interval_started_at = month_interval_start()

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

        key_usage = APIKeyUsage(
            user_id=internal_user_id,
            api_key=fake_api_key,
            reserved_tokens=reserved_tokens,
            used_tokens=None,
            interval_started_at=interval_started_at,
        )

        async with use_api_key(key_usage):
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
    async def test_no_used_tokens_specified(self, internal_user_id: uuid.UUID, fake_api_key: str) -> None:

        interval_started_at = month_interval_start()

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

        key_usage = APIKeyUsage(
            user_id=internal_user_id,
            api_key=fake_api_key,
            reserved_tokens=reserved_tokens,
            used_tokens=None,
            interval_started_at=interval_started_at,
        )

        with pytest.raises(errors.UsedTokensHasNotSpecified):
            async with use_api_key(key_usage):
                assert key_usage.used_tokens is None

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

    @pytest.mark.asyncio
    async def test_exception_in_child_code(self, internal_user_id: uuid.UUID, fake_api_key: str) -> None:

        interval_started_at = month_interval_start()

        reserved_tokens = 567

        await r_domain.try_to_reserve(
            user_id=internal_user_id,
            # TODO: differentiate tokens in all places
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

        key_usage = APIKeyUsage(
            user_id=internal_user_id,
            api_key=fake_api_key,
            reserved_tokens=reserved_tokens,
            used_tokens=None,
            interval_started_at=interval_started_at,
        )

        with pytest.raises(FakeError):
            async with use_api_key(key_usage):
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

    @pytest.mark.asyncio
    async def test_no_user_in_key_usage(self, fake_api_key: str) -> None:

        interval_started_at = month_interval_start()

        reserved_tokens = 567
        used_tokens = 214

        key_usage = APIKeyUsage(
            user_id=None,
            api_key=fake_api_key,
            reserved_tokens=reserved_tokens,
            used_tokens=None,
            interval_started_at=interval_started_at,
        )

        async with use_api_key(key_usage):
            key_usage.used_tokens = used_tokens
