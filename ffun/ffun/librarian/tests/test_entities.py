import pydantic
import pytest

from ffun.librarian.entities import LLMGeneralProcessor
from ffun.librarian.tag_extractors import dog_tags_extractor
from ffun.librarian.text_cleaners import clear_nothing
from ffun.llms_framework.entities import LLMApiKey, LLMConfiguration, LLMGeneralApiKey, LLMProvider, LLMTokens


class TestLLMGeneralProcessor:

    @pytest.fixture
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model",
            system="some system prompt",
            max_return_tokens=LLMTokens(1017),
            text_parts_intersection=113,
            temperature=0.3,
            top_p=0.9,
            presence_penalty=0.5,
            frequency_penalty=0.75,
        )

    def test_api_key_is_required_if_collections_enbabled(self, llm_config: LLMConfiguration) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            LLMGeneralProcessor(
                id=666,
                enabled=True,
                workers=1,
                name="test-processor",
                allowed_for_collections=True,
                allowed_for_users=False,
                llm_provider=LLMProvider.test,
                llm_config=llm_config,
                entry_template="<h1>{entry.title}</h1><a href='{entry.external_url}'>full article</a>{entry.body}",
                text_cleaner=clear_nothing,
                tags_extractor=dog_tags_extractor,
                collections_api_key=None,
                general_api_key=None,
            )

        assert exc_info.value.errors()[0]["type"] == "collections_or_general_key_required_for_collections"

    @pytest.mark.parametrize("key_warning", [None, "wrong warning"])
    def test_general_api_key_warning_check__failed(
        self, llm_config: LLMConfiguration, key_warning: str | None
    ) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            LLMGeneralProcessor(
                id=666,
                enabled=True,
                workers=1,
                name="test-processor",
                allowed_for_collections=False,
                allowed_for_users=False,
                llm_provider=LLMProvider.test,
                llm_config=llm_config,
                entry_template="<h1>{entry.title}</h1><a href='{entry.external_url}'>full article</a>{entry.body}",
                text_cleaner=clear_nothing,
                tags_extractor=dog_tags_extractor,
                collections_api_key=None,
                general_api_key=LLMGeneralApiKey(LLMApiKey("some key")),
                general_api_key_warning=key_warning,
            )

        assert exc_info.value.errors()[0]["type"] == "you_must_confirm_general_api_key_usage"
