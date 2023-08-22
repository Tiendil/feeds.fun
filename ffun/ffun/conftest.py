import asyncio
import datetime
import uuid
from typing import AsyncGenerator, Generator

import fastapi
import pytest
import pytest_asyncio

from ffun.application import application
from ffun.core import migrations, utils
from ffun.feeds.entities import Feed, FeedState
from ffun.library.entities import Entry
from ffun.tests_framework import utils as tf_utils
from ffun.tests_framework.fixtures.base import *  # noqa
from ffun.tests_framework.fixtures.feeds import *  # noqa


@pytest.fixture(scope="session", autouse=True)
def event_loop() -> Generator[asyncio.AbstractEventLoop, asyncio.AbstractEventLoop, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def app() -> AsyncGenerator[fastapi.FastAPI, None]:
    async with application.with_app() as app:
        yield app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db(
    app: AsyncGenerator[fastapi.FastAPI, None],
    event_loop: asyncio.AbstractEventLoop,
) -> AsyncGenerator[None, None]:
    await migrations.apply_all()
    yield
    await migrations.rollback_all()


# TODO: replace with fixture of real entry from the DB
@pytest.fixture
def fake_entry(loaded_feed_id: uuid.UUID) -> Entry:
    return Entry(
        id=uuid.uuid4(),
        feed_id=loaded_feed_id,
        title=fake_title(),
        body=fake_body(),
        external_id=uuid.uuid4().hex,
        external_url=tf_utils.fake_url(),
        external_tags={uuid.uuid4().hex, uuid.uuid4().hex},
        published_at=utils.now(),
        cataloged_at=utils.now(),
    )