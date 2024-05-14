import uuid

import pytest
import pytest_asyncio

from ffun.ontology.domain import get_ids_by_uids
from ffun.ontology.entities import ProcessorTag


@pytest_asyncio.fixture
async def three_tags_by_uids() -> dict[str, int]:
    return await get_ids_by_uids([uuid.uuid4().hex for _ in range(3)])


@pytest.fixture
def three_tags_by_ids(three_tags_by_uids: dict[str, int]) -> dict[int, str]:
    return {v: k for k, v in three_tags_by_uids.items()}


@pytest.fixture
def three_tags_ids(three_tags_by_uids: dict[str, int]) -> tuple[int, int, int]:
    return tuple(three_tags_by_uids.values())  # type: ignore


@pytest.fixture
def three_processor_tags(three_tags_by_ids: dict[int, str]) -> tuple[ProcessorTag, ProcessorTag, ProcessorTag]:
    return tuple(ProcessorTag(raw_uid=tag) for tag in three_tags_by_ids.values())  # type: ignore
