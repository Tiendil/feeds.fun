import uuid

import pytest
import pytest_asyncio
from ffun.ontology.domain import get_ids_by_uids


@pytest_asyncio.fixture
async def three_tags_by_uids() -> dict[str, int]:
    return await get_ids_by_uids([uuid.uuid4().hex for _ in range(3)])


@pytest.fixture
def three_tags_by_ids(three_tags_by_uids: dict[str, int]) -> dict[int, str]:
    return {v: k for k, v in three_tags_by_uids.items()}


@pytest.fixture
def three_tags_ids(three_tags_by_uids: dict[str, int]) -> tuple[int, int, int]:
    return tuple(three_tags_by_uids.values())  # type: ignore
