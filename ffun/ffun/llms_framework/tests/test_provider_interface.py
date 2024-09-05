
import pytest

from pytest_mock import MockerFixture

from ffun.llms_framework.entities import ModelInfo, Provider, LLMConfiguration, KeyStatus
from ffun.llms_framework.provider_interface import ProviderTest
from ffun.llms_framework import errors


class TestBaseProviderInterfaceClass:
    """Test concrete methods of the abstract ProviderInterface class."""

    def test_different_storages_for_keys(self, fake_api_key: str) -> None:
        provider_1 = ProviderTest()
        provider_2 = ProviderTest()

        assert provider_1.api_keys_statuses is not provider_2.api_keys_statuses

        provider_1.api_keys_statuses.set(fake_api_key, KeyStatus.works)
        provider_2.api_keys_statuses.set(fake_api_key, KeyStatus.broken)

        assert provider_1.api_keys_statuses.get(fake_api_key) == KeyStatus.works
        assert provider_2.api_keys_statuses.get(fake_api_key) == KeyStatus.broken

    def test_get_model(self, fake_llm_provider: ProviderTest, mocker: MockerFixture) -> None:
        config_1 = LLMConfiguration(model='test-model-1',
                                    system="system prompt",
                                    max_return_tokens=143,
                                    text_parts_intersection=100,
                                    temperature=0,
                                    top_p=0,
                                    presence_penalty=0,
                                    frequency_penalty=0)

        assert fake_llm_provider.get_model(config_1) == ModelInfo(provider=Provider.test,
                                                                  name='test-model-1',
                                                                  max_context_size=12800,
                                                                  max_return_tokens=4096,
                                                                  max_tokens_per_entry=300000)

        config_2 = config_1.replace(model='test-model-2')

        assert fake_llm_provider.get_model(config_2) == ModelInfo(provider=Provider.test,
                                                         name='test-model-2',
                                                         max_context_size=14212,
                                                         max_return_tokens=1024,
                                                                  max_tokens_per_entry=300000)

        mocker.patch.object(fake_llm_provider, 'provider', Provider.openai)

        config_3 = config_1.replace(provider=Provider.openai,
                                    model='chatgpt-4o-latest')

        assert fake_llm_provider.get_model(config_3) == ModelInfo(provider=Provider.openai,
                                                         name='chatgpt-4o-latest',
                                                         max_context_size=128000,
                                                         max_return_tokens=16384,
                                                                  max_tokens_per_entry=300000)

    def test_wrong_provider(self, fake_llm_provider: ProviderTest, mocker: MockerFixture) -> None:

        config = LLMConfiguration(model='chatgpt-4o-latest',
                                  system="system prompt",
                                  max_return_tokens=143,
                                  text_parts_intersection=100,
                                  temperature=0,
                                  top_p=0,
                                  presence_penalty=0,
                                  frequency_penalty=0)

        with pytest.raises(errors.ModelDoesNotFound):
            fake_llm_provider.get_model(config)

        mocker.patch.object(fake_llm_provider, 'provider', Provider.openai)

        assert fake_llm_provider.get_model(config) is not None

    def test_wrong_model(self, fake_llm_provider: ProviderTest, mocker: MockerFixture) -> None:
        config_1 = LLMConfiguration(model='test-model-wrong',
                                    system="system prompt",
                                    max_return_tokens=143,
                                    text_parts_intersection=100,
                                    temperature=0,
                                    top_p=0,
                                    presence_penalty=0,
                                    frequency_penalty=0)

        with pytest.raises(errors.ModelDoesNotFound):
            fake_llm_provider.get_model(config_1)

        config_2 = config_1.replace(model='test-model-1')

        assert fake_llm_provider.get_model(config_2) is not None
