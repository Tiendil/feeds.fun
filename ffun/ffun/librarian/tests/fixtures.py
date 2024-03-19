import pytest

from ffun.librarian.background_processors import EntriesProcessor, ProcessorInfo
from ffun.librarian.processors.base import AlwaysConstantProcessor


@pytest.fixture
def fake_processor_id() -> int:
    return 11042


@pytest.fixture
def another_fake_processor_id() -> int:
    return 11043


@pytest.fixture
def fake_processor_info(fake_processor_id: int) -> ProcessorInfo:
    return ProcessorInfo(
        id=fake_processor_id,
        processor=AlwaysConstantProcessor(
            name="fake_constant_processor", tags=["fake-constant-tag-1", "fake-constant-tag-2"]
        ),
        concurrency=3,
    )


@pytest.fixture
def fake_entries_processor(fake_processor_info: ProcessorInfo) -> EntriesProcessor:
    return EntriesProcessor(processor_info=fake_processor_info, name="fake_entries_processor", delay_between_runs=0.1)
