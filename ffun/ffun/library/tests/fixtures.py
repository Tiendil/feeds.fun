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
from ffun.feeds.tests.fixtures import *  # noqa
from ffun.library.entities import Entry

from . import make


# TODO: replace with fixture of real entry from the DB
@pytest.fixture
def fake_entry(loaded_feed_id: uuid.UUID) -> Entry:
    return make.fake_entry(loaded_feed_id)
