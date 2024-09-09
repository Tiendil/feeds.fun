from decimal import Decimal

import pytest
from pytest_mock import MockerFixture

from ffun.llms_framework import errors
from ffun.llms_framework.entities import (
    KeyStatus,
    LLMApiKey,
    LLMConfiguration,
    LLMProvider,
    LLMTokens,
    ModelInfo,
    USDCost,
)
from ffun.llms_framework.provider_interface import ProviderTest


class TestBaseProviderInterfaceClass:
    """Test concrete methods of the abstract ProviderInterface class."""

    def test_different_storages_for_keys(self, fake_llm_api_key: LLMApiKey) -> None:
        provider_1 = ProviderTest()
        provider_2 = ProviderTest()

        assert provider_1.api_keys_statuses is not provider_2.api_keys_statuses

        provider_1.api_keys_statuses.set(fake_llm_api_key, KeyStatus.works)
        provider_2.api_keys_statuses.set(fake_llm_api_key, KeyStatus.broken)

        assert provider_1.api_keys_statuses.get(fake_llm_api_key) == KeyStatus.works
        assert provider_2.api_keys_statuses.get(fake_llm_api_key) == KeyStatus.broken

    def test_get_model(self, fake_llm_provider: ProviderTest, mocker: MockerFixture) -> None:
        config_1 = LLMConfiguration(
            model="test-model-1",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            text_parts_intersection=100,
            temperature=0,
            top_p=0,
            presence_penalty=0,
            frequency_penalty=0,
        )

        assert fake_llm_provider.get_model(config_1) == ModelInfo(
            provider=LLMProvider.test,
            name="test-model-1",
            max_context_size=LLMTokens(12800),
            max_return_tokens=LLMTokens(4096),
            max_tokens_per_entry=LLMTokens(300000),
            input_1m_tokens_cost=USDCost(Decimal("0.3")),
            output_1m_tokens_cost=USDCost(Decimal("0.7")),
        )

        config_2 = config_1.replace(model="test-model-2")

        assert fake_llm_provider.get_model(config_2) == ModelInfo(
            provider=LLMProvider.test,
            name="test-model-2",
            max_context_size=LLMTokens(14212),
            max_return_tokens=LLMTokens(1024),
            max_tokens_per_entry=LLMTokens(300000),
            input_1m_tokens_cost=USDCost(Decimal("0.7")),
            output_1m_tokens_cost=USDCost(Decimal("0.3")),
        )

        mocker.patch.object(fake_llm_provider, "provider", LLMProvider.openai)

        config_3 = config_1.replace(provider=LLMProvider.openai, model="chatgpt-4o-latest")

        assert fake_llm_provider.get_model(config_3) == ModelInfo(
            provider=LLMProvider.openai,
            name="chatgpt-4o-latest",
            max_context_size=LLMTokens(128000),
            max_return_tokens=LLMTokens(16384),
            max_tokens_per_entry=LLMTokens(300000),
            input_1m_tokens_cost=USDCost(Decimal("5")),
            output_1m_tokens_cost=USDCost(Decimal("15")),
        )

    def test_wrong_provider(self, fake_llm_provider: ProviderTest, mocker: MockerFixture) -> None:

        config = LLMConfiguration(
            model="chatgpt-4o-latest",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            text_parts_intersection=100,
            temperature=0,
            top_p=0,
            presence_penalty=0,
            frequency_penalty=0,
        )

        with pytest.raises(errors.ModelDoesNotFound):
            fake_llm_provider.get_model(config)

        mocker.patch.object(fake_llm_provider, "provider", LLMProvider.openai)

        assert fake_llm_provider.get_model(config) is not None

    def test_wrong_model(self, fake_llm_provider: ProviderTest, mocker: MockerFixture) -> None:
        config_1 = LLMConfiguration(
            model="test-model-wrong",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            text_parts_intersection=100,
            temperature=0,
            top_p=0,
            presence_penalty=0,
            frequency_penalty=0,
        )

        with pytest.raises(errors.ModelDoesNotFound):
            fake_llm_provider.get_model(config_1)

        config_2 = config_1.replace(model="test-model-1")

        assert fake_llm_provider.get_model(config_2) is not None
