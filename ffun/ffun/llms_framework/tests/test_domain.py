from decimal import Decimal

import pytest

from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import FeedId, UserId
from ffun.feeds_links import domain as fl_domain
from ffun.library.entities import Entry
from ffun.llms_framework import errors
from ffun.llms_framework.domain import (
    _estimate_reserved_cost,
    _llm_call_result_cost,
    call_llm,
    collection_api_key_usage,
    cut_text_to_max_tokens,
    general_api_key_usage,
    search_for_user_api_key,
    split_text,
    split_text_according_to_tokens,
)
from ffun.llms_framework.entities import (
    APIKeyUsage,
    LLMApiKey,
    LLMCollectionApiKey,
    LLMConfiguration,
    LLMGeneralApiKey,
    LLMTokens,
    USDCost,
    UserKeyInfo,
)
from ffun.llms_framework.keys_rotator import _cost_points
from ffun.llms_framework.provider_interface import ChatRequestTest, ChatResponseTest, ProviderTest
from ffun.product.resources import Resource as AppResource
from ffun.resources import domain as r_domain

_text_parts_intersection = 100


class TestSplitText:

    @pytest.mark.parametrize("parts_number", [-100, -1, 0])
    def test_wrong_parts_number(self, parts_number: int) -> None:
        with pytest.raises(errors.TextPartsMustBePositive):
            split_text("some-text", parts=parts_number, intersection=0)

    @pytest.mark.parametrize("intersection", [-100, -1])
    def test_intersection_size(self, intersection: int) -> None:
        with pytest.raises(errors.TextIntersectionMustBePositiveOrZero):
            split_text("some-text", parts=1, intersection=intersection)

    def test_text_is_empty(self) -> None:
        with pytest.raises(errors.TextIsEmpty):
            split_text("", parts=1, intersection=0)

    def test_text_is_too_short(self) -> None:
        with pytest.raises(errors.TextIsTooShort):
            split_text("short", parts=len("short") + 1, intersection=0)

        with pytest.raises(errors.TextIsTooShort):
            split_text("some-text", parts=4, intersection=0)

    @pytest.mark.parametrize("text", ["small-text", "long-long-text " * 10**6], ids=["small", "big"])
    def test_single_part(self, text: str) -> None:
        for intersection in [0, 1, 100, 1000, 10000]:
            assert split_text(text, parts=1, intersection=intersection) == [text]

    @pytest.mark.parametrize(
        "text, parts, intersection, expected",
        [
            ("some-text", 1, 0, ["some-text"]),
            ("some-text", 2, 0, ["some-", "text"]),
            ("some-text", 3, 0, ["s" + "o" + "m", "e-t", "ext"]),  # go around codespell fixing strings
            ("some-text", 1, 1, ["some-text"]),
            ("some-text", 2, 1, ["some-t", "-text"]),
            ("some-text", 3, 1, ["some", "me-te", "text"]),
            ("some-text", 1, 2, ["some-text"]),
            ("some-text", 2, 2, ["some-te", "e-text"]),
            ("some-text", 3, 2, ["some-", "ome-tex", "-text"]),
            ("some-text", 1, 3, ["some-text"]),
            ("some-text", 2, 3, ["some-tex", "me-text"]),
            ("some-text", 3, 3, ["some-t", "some-text", "e-text"]),
        ],
    )
    def test_split(self, text: str, parts: int, intersection: int, expected: list[str]) -> None:
        assert split_text(text, parts=parts, intersection=intersection) == expected


class TestSplitTextAccordingToTokens:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    def test_single_part(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        text = "some text"

        parts = split_text_according_to_tokens(
            llm=fake_llm_provider,
            llm_config=llm_config,
            text=text,
            text_parts_intersection=_text_parts_intersection,
        )

        assert parts == [text]

    def test_multiple_parts(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        # We test that algorithm will pass a few iterations before finding the right split
        # => for this test, text must be splittable to 3 parts

        model = fake_llm_provider.get_model(llm_config)

        size = int(model.max_context_size * 2.5)

        text = "a" * size

        parts = split_text_according_to_tokens(
            llm=fake_llm_provider,
            llm_config=llm_config,
            text=text,
            text_parts_intersection=_text_parts_intersection,
        )

        assert len(parts) == 3

        assert size < sum(len(part) for part in parts) < size + 2 * 2 * _text_parts_intersection + 1

        assert abs(len(parts[0]) - len(parts[1])) <= _text_parts_intersection + 1
        assert abs(len(parts[1]) - len(parts[2])) <= _text_parts_intersection + 1
        assert abs(len(parts[0]) - len(parts[2])) <= 1

    def test_uses_requested_intersection_size(
        self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration
    ) -> None:
        model = fake_llm_provider.get_model(llm_config)

        text = "a" * (model.max_context_size - llm_config.max_return_tokens)

        assert split_text_according_to_tokens(
            llm=fake_llm_provider,
            llm_config=llm_config,
            text=text,
            text_parts_intersection=2,
        ) == split_text(text, parts=2, intersection=2)


class TestSearchForUserAPIKey:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    @pytest.mark.asyncio
    async def test_key_found(
        self,
        fake_llm_provider: ProviderTest,
        llm_config: LLMConfiguration,
        loaded_feed_id: FeedId,
        cataloged_entry: Entry,
        user_key_info: UserKeyInfo,
    ) -> None:
        text = "some-text"

        requests = fake_llm_provider.prepare_requests(
            llm_config, text, text_parts_intersection=_text_parts_intersection
        )

        assert user_key_info.api_key is not None

        await fl_domain.add_link(user_key_info.user_id, loaded_feed_id)

        key_usage = await search_for_user_api_key(
            llm=fake_llm_provider,
            llm_config=llm_config,
            entry=cataloged_entry,
            requests=requests,
        )

        assert key_usage is not None

        assert key_usage.api_key == user_key_info.api_key

    @pytest.mark.asyncio
    async def test_key_not_found(
        self,
        fake_llm_provider: ProviderTest,
        llm_config: LLMConfiguration,
        cataloged_entry: Entry,
    ) -> None:
        text = "some-text"

        requests = fake_llm_provider.prepare_requests(
            llm_config, text, text_parts_intersection=_text_parts_intersection
        )

        key_usage = await search_for_user_api_key(
            llm=fake_llm_provider,
            llm_config=llm_config,
            entry=cataloged_entry,
            requests=requests,
        )

        assert key_usage is None


class TestCutTextToMaxTokens:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    @pytest.mark.parametrize(
        "text, max_tokens, expected",
        [
            ("some text", LLMTokens(len("some text")), "some text"),
            ("some text", LLMTokens(len("some text") * 10), "some text"),
            ("", LLMTokens(1), ""),
            ("a", LLMTokens(1), "a"),
            ("a", LLMTokens(2), "a"),
            ("abcdefghij", LLMTokens(4), "abcd"),
            ("abcdefghij", LLMTokens(1), "a"),
            ("some text", LLMTokens(len("some text") - 1), "some tex"),
        ],
    )
    def test_cut_text(
        self,
        fake_llm_provider: ProviderTest,
        llm_config: LLMConfiguration,
        text: str,
        max_tokens: LLMTokens,
        expected: str,
    ) -> None:
        assert (
            cut_text_to_max_tokens(
                llm=fake_llm_provider,
                llm_config=llm_config,
                text=text,
                max_tokens=max_tokens,
            )
            == expected
        )

    def test_max_tokens_must_be_positive(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        with pytest.raises(errors.MaxTokensMustBePositive):
            cut_text_to_max_tokens(
                llm=fake_llm_provider,
                llm_config=llm_config,
                text="some text",
                max_tokens=LLMTokens(0),
            )


class TestEstimateReservedCost:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    def test_empty_requests(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        assert _estimate_reserved_cost(llm=fake_llm_provider, llm_config=llm_config, requests=[]) == 0

    def test_counts_max_request_cost_per_request(
        self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration
    ) -> None:
        model = fake_llm_provider.get_model(llm_config)

        requests = [ChatRequestTest(text="abcd"), ChatRequestTest(text="efgh1234"), ChatRequestTest(text="99")]

        assert _estimate_reserved_cost(llm=fake_llm_provider, llm_config=llm_config, requests=requests) == USDCost(
            len(requests) * model.max_request_cost
        )


class TestGeneralAPIKeyUsage:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    def test_constructs_usage(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        api_key = LLMGeneralApiKey(LLMApiKey("general-api-key"))
        requests = [ChatRequestTest(text="abcd"), ChatRequestTest(text="efgh1234")]
        reserved_cost = _estimate_reserved_cost(llm=fake_llm_provider, llm_config=llm_config, requests=requests)

        key_usage = general_api_key_usage(
            llm=fake_llm_provider, llm_config=llm_config, api_key=api_key, requests=requests
        )

        assert key_usage == APIKeyUsage(
            provider=fake_llm_provider.provider,
            user_id=None,
            api_key=api_key,
            reserved_cost=reserved_cost,
            used_cost=None,
            interval_started_at=month_interval_start(),
        )


class TestCollectionAPIKeyUsage:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    def test_constructs_usage(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        api_key = LLMCollectionApiKey(LLMApiKey("collection-api-key"))
        requests = [ChatRequestTest(text="abcd"), ChatRequestTest(text="efgh1234")]
        reserved_cost = _estimate_reserved_cost(llm=fake_llm_provider, llm_config=llm_config, requests=requests)

        key_usage = collection_api_key_usage(
            llm=fake_llm_provider, llm_config=llm_config, api_key=api_key, requests=requests
        )

        assert key_usage == APIKeyUsage(
            provider=fake_llm_provider.provider,
            user_id=None,
            api_key=api_key,
            reserved_cost=reserved_cost,
            used_cost=None,
            interval_started_at=month_interval_start(),
        )


class TestLLMCallResultCost:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    def test_successful_response(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        model = fake_llm_provider.get_model(llm_config)
        response = ChatResponseTest(content="abcd")

        assert _llm_call_result_cost(model, response) == model.tokens_cost(
            input_tokens=LLMTokens(4), output_tokens=LLMTokens(4)
        )

    def test_temporary_error(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        model = fake_llm_provider.get_model(llm_config)

        result = errors.TemporaryError(message="some error")

        assert _llm_call_result_cost(model, result) == model.max_request_cost

    def test_rejected_request(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        model = fake_llm_provider.get_model(llm_config)

        result = errors.RequestWasRejected(message="some error")

        assert _llm_call_result_cost(model, result) == 0


class TestCallLLM:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    @pytest.mark.asyncio
    async def test_counts_tokens(
        self,
        fake_llm_provider: ProviderTest,
        llm_config: LLMConfiguration,
        internal_user_id: UserId,
        fake_llm_api_key: LLMApiKey,
    ) -> None:

        model = fake_llm_provider.get_model(llm_config)

        interval_started_at = month_interval_start()

        key_usage = APIKeyUsage(
            provider=fake_llm_provider.provider,
            user_id=internal_user_id,
            api_key=fake_llm_api_key,
            reserved_cost=USDCost(Decimal(1005)),
            used_cost=None,
            interval_started_at=interval_started_at,
        )

        await r_domain.try_to_reserve(
            user_id=internal_user_id,
            kind=AppResource.tokens_cost,
            interval_started_at=interval_started_at,
            amount=_cost_points.to_points(key_usage.reserved_cost),
            limit=_cost_points.to_points(USDCost(Decimal(124512512))),
        )

        requests = [ChatRequestTest(text="abcd"), ChatRequestTest(text="efgh1234"), ChatRequestTest(text="99")]

        responses = await call_llm(
            llm=fake_llm_provider, llm_config=llm_config, api_key_usage=key_usage, requests=requests
        )

        assert responses == [ChatResponseTest(content=request.text) for request in requests]

        resources = await r_domain.load_resources(
            user_ids=[internal_user_id], kind=AppResource.tokens_cost, interval_started_at=interval_started_at
        )

        cost = USDCost(
            Decimal(
                sum(
                    model.tokens_cost(
                        input_tokens=LLMTokens(len(request.text)), output_tokens=LLMTokens(len(request.text))
                    )
                    for request in requests
                )
            )
        )

        assert resources[internal_user_id].used == _cost_points.to_points(cost)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario",
        [
            (["abcd", "raise TemporaryError", "99"], LLMTokens(6), 1),
            (["raise TemporaryError 1", "abcd", "raise TemporaryError 2", "99"], LLMTokens(6), 2),
        ],
        ids=["single-error", "multiple-errors"],
    )
    async def test_registers_used_cost_before_reraising_request_error(
        self,
        fake_llm_provider: ProviderTest,
        llm_config: LLMConfiguration,
        internal_user_id: UserId,
        fake_llm_api_key: LLMApiKey,
        scenario: tuple[list[str], LLMTokens, int],
    ) -> None:

        request_texts, successful_tokens, failed_requests = scenario

        model = fake_llm_provider.get_model(llm_config)

        interval_started_at = month_interval_start()

        key_usage = APIKeyUsage(
            provider=fake_llm_provider.provider,
            user_id=internal_user_id,
            api_key=fake_llm_api_key,
            reserved_cost=USDCost(Decimal(1005)),
            used_cost=None,
            interval_started_at=interval_started_at,
        )

        await r_domain.try_to_reserve(
            user_id=internal_user_id,
            kind=AppResource.tokens_cost,
            interval_started_at=interval_started_at,
            amount=_cost_points.to_points(key_usage.reserved_cost),
            limit=_cost_points.to_points(USDCost(Decimal(124512512))),
        )

        requests = [ChatRequestTest(text=text) for text in request_texts]

        with pytest.raises(errors.TemporaryError):
            await call_llm(llm=fake_llm_provider, llm_config=llm_config, api_key_usage=key_usage, requests=requests)

        resources = await r_domain.load_resources(
            user_ids=[internal_user_id], kind=AppResource.tokens_cost, interval_started_at=interval_started_at
        )

        cost = USDCost(
            model.tokens_cost(input_tokens=successful_tokens, output_tokens=successful_tokens)
            + failed_requests * model.max_request_cost
        )

        assert key_usage.used_cost == cost
        assert resources[internal_user_id].used == _cost_points.to_points(cost)

    @pytest.mark.asyncio
    async def test_rejected_requests_are_not_billed(
        self,
        fake_llm_provider: ProviderTest,
        llm_config: LLMConfiguration,
        internal_user_id: UserId,
        fake_llm_api_key: LLMApiKey,
    ) -> None:

        model = fake_llm_provider.get_model(llm_config)

        interval_started_at = month_interval_start()

        key_usage = APIKeyUsage(
            provider=fake_llm_provider.provider,
            user_id=internal_user_id,
            api_key=fake_llm_api_key,
            reserved_cost=USDCost(Decimal(1005)),
            used_cost=None,
            interval_started_at=interval_started_at,
        )

        await r_domain.try_to_reserve(
            user_id=internal_user_id,
            kind=AppResource.tokens_cost,
            interval_started_at=interval_started_at,
            amount=_cost_points.to_points(key_usage.reserved_cost),
            limit=_cost_points.to_points(USDCost(Decimal(124512512))),
        )

        requests = [
            ChatRequestTest(text="raise RequestWasRejected 1"),
            ChatRequestTest(text="abcd"),
            ChatRequestTest(text="raise RequestWasRejected 2"),
            ChatRequestTest(text="99"),
        ]

        with pytest.raises(errors.RequestWasRejected):
            await call_llm(llm=fake_llm_provider, llm_config=llm_config, api_key_usage=key_usage, requests=requests)

        resources = await r_domain.load_resources(
            user_ids=[internal_user_id], kind=AppResource.tokens_cost, interval_started_at=interval_started_at
        )

        cost = model.tokens_cost(input_tokens=LLMTokens(6), output_tokens=LLMTokens(6))

        assert key_usage.used_cost == cost
        assert resources[internal_user_id].used == _cost_points.to_points(cost)
