import uuid

import pytest
import pytest_asyncio

from ffun.core import utils
from ffun.feeds.domain import get_feed, mark_feed_as_loaded, save_feed
from ffun.feeds.entities import Feed, FeedState


def fake_title() -> str:
    return f"Title: {uuid.uuid4().hex}"


def fake_description() -> str:
    return f"Description: {uuid.uuid4().hex}"


def fake_body() -> str:
    return f"Body: {uuid.uuid4().hex}"


@pytest.fixture
def new_feed(fake_url: str) -> Feed:
    return Feed(
        id=uuid.uuid4(),
        url=fake_url,
        state=FeedState.loaded,
        last_error=None,
        load_attempted_at=None,
        loaded_at=None,
        title=fake_title(),
        description=fake_description(),
    )


@pytest_asyncio.fixture
async def saved_feed_id(new_feed: Feed) -> uuid.UUID:
    return await save_feed(new_feed)


@pytest_asyncio.fixture
async def loaded_feed_id(saved_feed_id: uuid.UUID) -> uuid.UUID:
    await mark_feed_as_loaded(saved_feed_id)
    return saved_feed_id
