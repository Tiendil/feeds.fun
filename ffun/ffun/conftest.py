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

# Replacing the event_loop fixture with a custom implementation is deprecated
# and will lead to errors in the future.
# If you want to request an asyncio event loop with a scope other than function
# scope, use the "scope" argument to the asyncio mark when marking the tests.
# If you want to return different types of event loops, use the event_loop_policy
# fixture.

# For more information see https://pluggy.readthedocs.io/en/stable/api_reference.html#pluggy.PluggyTeardownRaisedWarning
# @pytest.fixture(scope="session", autouse=True)
# def event_loop() -> Generator[asyncio.AbstractEventLoop, asyncio.AbstractEventLoop, None]:
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def app() -> AsyncGenerator[fastapi.FastAPI, None]:
    async with application.with_app() as app:
        yield app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db(
    app: AsyncGenerator[fastapi.FastAPI, None],
    # event_loop: asyncio.AbstractEventLoop,
) -> AsyncGenerator[None, None]:
    # database migrations may be in an inconsistent state
    await migrations.rollback_all()

    await migrations.apply_all()
    yield
    await migrations.rollback_all()
