from decimal import Decimal

import pytest

from ffun.application.resources import Resource as AppResource
from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import UserId
from ffun.library.entities import Entry
from ffun.llms_framework import errors
from ffun.llms_framework.domain import call_llm, search_for_api_key, split_text, split_text_according_to_tokens
from ffun.llms_framework.entities import APIKeyUsage, LLMApiKey, LLMConfiguration, LLMGeneralApiKey, LLMTokens, USDCost
from ffun.llms_framework.keys_rotator import _cost_points
from ffun.llms_framework.provider_interface import ChatRequestTest, ChatResponseTest, ProviderTest
from ffun.resources import domain as r_domain


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
            ("some-text", 3, 0, ["som", "e-t", "ext"]),
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

    @pytest.fixture
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            text_parts_intersection=100,
            temperature=0,
            top_p=0,
            presence_penalty=0,
            frequency_penalty=0,
        )

    def test_single_part(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        text = "some text"

        parts = split_text_according_to_tokens(llm=fake_llm_provider, llm_config=llm_config, text=text)

        assert parts == [text]

    def test_multiple_parts(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        # We test that algorithm will pass a few iterations before finding the right split
        # => for this test, text must be splittable to 3 parts

        model = fake_llm_provider.get_model(llm_config)

        size = int(model.max_context_size * 2.5)

        text = "a" * size

        parts = split_text_according_to_tokens(llm=fake_llm_provider, llm_config=llm_config, text=text)

        assert len(parts) == 3

        assert size < sum(len(part) for part in parts) < size + 2 * 2 * llm_config.text_parts_intersection + 1

        assert abs(len(parts[0]) - len(parts[1])) <= llm_config.text_parts_intersection + 1
        assert abs(len(parts[1]) - len(parts[2])) <= llm_config.text_parts_intersection + 1
        assert abs(len(parts[0]) - len(parts[2])) <= 1

    def test_too_many_tokens_for_entry(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        model = fake_llm_provider.get_model(llm_config)

        text = "a" * (model.max_tokens_per_entry + 1)

        with pytest.raises(errors.TooManyTokensForEntry):
            split_text_according_to_tokens(llm=fake_llm_provider, llm_config=llm_config, text=text)


class TestSearchForAPIKey:

    @pytest.fixture
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            text_parts_intersection=100,
            temperature=0,
            top_p=0,
            presence_penalty=0,
            frequency_penalty=0,
        )

    @pytest.mark.asyncio
    async def test_key_found(
        self,
        fake_llm_api_key: LLMApiKey,
        fake_llm_provider: ProviderTest,
        llm_config: LLMConfiguration,
        cataloged_entry: Entry,
    ) -> None:
        # Here we test meta logic => we can check the simplest case (general api key)
        # plus check the all parameters passed to selection function

        text = "some-text"

        requests = fake_llm_provider.prepare_requests(llm_config, text)

        key_usage = await search_for_api_key(
            llm=fake_llm_provider,
            llm_config=llm_config,
            entry=cataloged_entry,
            requests=requests,
            collections_api_key=None,
            general_api_key=LLMGeneralApiKey(fake_llm_api_key),
        )

        assert key_usage is not None

        assert key_usage.api_key == fake_llm_api_key

    @pytest.mark.asyncio
    async def test_key_not_found(
        self,
        fake_llm_provider: ProviderTest,
        llm_config: LLMConfiguration,
        cataloged_entry: Entry,
    ) -> None:
        # Here we test meta logic => we can check the simplest case (general api key)
        # plus check the all parameters passed to selection function

        text = "some-text"

        requests = fake_llm_provider.prepare_requests(llm_config, text)

        key_usage = await search_for_api_key(
            llm=fake_llm_provider,
            llm_config=llm_config,
            entry=cataloged_entry,
            requests=requests,
            collections_api_key=None,
            general_api_key=None,
        )

        assert key_usage is None


class TestCallLLM:

    @pytest.fixture
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            text_parts_intersection=100,
            temperature=0,
            top_p=0,
            presence_penalty=0,
            frequency_penalty=0,
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
            input_tokens=None,
            output_tokens=None,
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
