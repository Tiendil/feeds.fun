import uuid

import pytest
import pytest_asyncio

from ffun.ontology.domain import get_ids_by_uids


@pytest_asyncio.fixture
async def tree_tags_by_uids() -> dict[str, int]:
    return await get_ids_by_uids([uuid.uuid4().hex for _ in range(3)])


@pytest.fixture
def tree_tags_by_ids(tree_tags_by_uids: dict[str, int]) -> dict[int, str]:
    return {v: k for k, v in tree_tags_by_uids.items()}


@pytest.fixture
def tree_tags_ids(tree_tags_by_uids: dict[str, int]) -> tuple[int, int, int]:
    return tuple(tree_tags_by_uids.values())  # type: ignore
