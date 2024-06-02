from typing import AsyncGenerator

import fastapi
import pytest_asyncio

from ffun.application import application
from ffun.core import migrations
from ffun.feeds.tests.fixtures import *  # noqa
from ffun.feeds_collections.tests.fixtures import *  # noqa
from ffun.librarian.tests.fixtures import *  # noqa
from ffun.library.tests.fixtures import *  # noqa
from ffun.ontology.tests.fixtures import *  # noqa
from ffun.openai.tests.fixtures import *  # noqa
from ffun.users.tests.fixtures import *  # noqa


@pytest_asyncio.fixture(scope="session", autouse=True)
async def app() -> AsyncGenerator[fastapi.FastAPI, None]:
    async with application.with_app() as app:
        yield app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db(
    app: AsyncGenerator[fastapi.FastAPI, None],
) -> AsyncGenerator[None, None]:
    # database migrations may be in an inconsistent state
    await migrations.rollback_all()

    await migrations.apply_all()
    yield
    await migrations.rollback_all()
