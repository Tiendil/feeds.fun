import pytest

from ffun.librarian.background_processors import processors
from ffun.librarian.entities import ProcessorType
from ffun.librarian.processors.llm_general import Processor as LLMGeneralProcessor


@pytest.fixture(scope="session", autouse=True)
def do_not_use_real_configured_api_keys_in_tests() -> None:

    for processor in processors:
        if processor.type != ProcessorType.llm_general:
            continue

        tags_processor = processor.processor

        assert isinstance(tags_processor, LLMGeneralProcessor)  # type: ignore

        for route in tags_processor.routes_by_id.values():
            assert route.api_key is None, "You should disable the real API keys processors' settings"
