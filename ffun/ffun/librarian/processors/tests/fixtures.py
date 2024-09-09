import pytest

from ffun.librarian.background_processors import processors
from ffun.librarian.entities import ProcessorType
from ffun.librarian.processors.llm_general import Processor as LLMGeneralProcessor


@pytest.fixture(scope="session", autouse=True)
def do_not_use_real_collection_api_keys_in_tests() -> None:

    for processor in processors:
        if processor.type != ProcessorType.llm_general:
            continue

        tags_processor = processor.processor

        assert isinstance(tags_processor, LLMGeneralProcessor)

        assert tags_processor.collections_api_key is None, "You should disable the real API keys processors' settings"


@pytest.fixture(scope="session", autouse=True)
def do_not_use_real_general_api_keys_in_tests() -> None:

    for processor in processors:
        if processor.type != ProcessorType.llm_general:
            continue

        tags_processor = processor.processor

        assert isinstance(tags_processor, LLMGeneralProcessor)

        assert tags_processor.general_api_key is None, "You should disable the real API keys processors' settings"
