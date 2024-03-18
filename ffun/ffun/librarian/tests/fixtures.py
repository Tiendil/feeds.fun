import pytest
import pytest_asyncio
from ffun.librarian.entities import ProcessorPointer


@pytest.fixture
def fake_processor_id() -> int:
    return 11042
