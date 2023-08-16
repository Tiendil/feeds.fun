import datetime
import uuid

import pytest

from ffun.core import utils
from ffun.feeds.entities import Feed, FeedState
from ffun.library.entities import Entry


def fake_title() -> str:
    return f"Title: {uuid.uuid4().hex}"


def fake_description() -> str:
    return f"Description: {uuid.uuid4().hex}"


def fake_body() -> str:
    return f"Body: {uuid.uuid4().hex}"


def fake_url() -> str:
    return f"https://{uuid.uuid4().hex}.com"


@pytest.fixture(name="fake_url")
def fixture_fake_url() -> str:
    return fake_url()


# TODO: replace with fixture of real entry from the DB
@pytest.fixture
def fake_feed(fake_url: str) -> Feed:
    loaded_at = utils.now()

    return Feed(
        id=uuid.uuid4(),
        url=fake_url,
        state=FeedState.loaded,
        last_error=None,
        load_attempted_at=loaded_at,
        loaded_at=loaded_at,
        title=fake_title(),
        description=fake_description(),
    )


# TODO: replace with fixture of real entry from the DB
@pytest.fixture
def fake_entry(fake_feed: Feed) -> Entry:
    return Entry(
        id=uuid.uuid4(),
        feed_id=fake_feed.id,
        title=fake_title(),
        body=fake_body(),
        external_id=uuid.uuid4().hex,
        external_url=fake_url(),
        external_tags={uuid.uuid4().hex, uuid.uuid4().hex},
        published_at=utils.now(),
        cataloged_at=utils.now(),
    )
