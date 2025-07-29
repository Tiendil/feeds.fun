import uuid

import pytest
import pytest_asyncio

from ffun.domain.entities import TagId, TagUid
from ffun.ontology.domain import get_ids_by_uids
from ffun.ontology.entities import ProcessorTag


@pytest_asyncio.fixture
async def three_tags_by_uids() -> dict[TagUid, TagId]:
    return await get_ids_by_uids([uuid.uuid4().hex for _ in range(3)])  # type: ignore


@pytest.fixture
def three_tags_by_ids(three_tags_by_uids: dict[TagUid, TagId]) -> dict[TagId, TagUid]:
    return {v: k for k, v in three_tags_by_uids.items()}


@pytest.fixture
def three_tags_ids(three_tags_by_uids: dict[TagUid, TagId]) -> tuple[TagId, TagId, TagId]:
    return tuple(three_tags_by_uids.values())  # type: ignore


@pytest.fixture
def three_processor_tags(three_tags_by_ids: dict[TagId, TagUid]) -> tuple[ProcessorTag, ProcessorTag, ProcessorTag]:
    return tuple(ProcessorTag(raw_uid=tag) for tag in three_tags_by_ids.values())  # type: ignore


@pytest_asyncio.fixture
async def five_tags_by_uids() -> dict[TagUid, TagId]:
    return await get_ids_by_uids([uuid.uuid4().hex for _ in range(5)])  # type: ignore


@pytest.fixture
def five_tags_by_ids(five_tags_by_uids: dict[TagUid, TagId]) -> dict[TagId, TagUid]:
    return {v: k for k, v in five_tags_by_uids.items()}


@pytest.fixture
def five_tags_ids(five_tags_by_uids: dict[TagUid, TagId]) -> tuple[TagId, TagId, TagId, TagId, TagId]:
    return tuple(five_tags_by_uids.values())  # type: ignore


@pytest.fixture
def five_processor_tags(
    five_tags_by_ids: dict[TagId, TagUid],
) -> tuple[ProcessorTag, ProcessorTag, ProcessorTag, ProcessorTag, ProcessorTag]:
    return tuple(ProcessorTag(raw_uid=tag) for tag in five_tags_by_ids.values())  # type: ignore
