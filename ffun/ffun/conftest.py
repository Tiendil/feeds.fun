from contextlib import AbstractAsyncContextManager
from typing import AsyncGenerator, cast
from unittest import mock

import fastapi
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pyleak import no_event_loop_blocking, no_task_leaks
from pyleak.base import LeakAction

from ffun.application import application
from ffun.auth.tests.fixtures import *  # noqa
from ffun.core import migrations
from ffun.feeds.tests.fixtures import *  # noqa
from ffun.feeds_collections.tests.fixtures import *  # noqa
from ffun.librarian.processors.tests.fixtures import *  # noqa
from ffun.librarian.tests.fixtures import *  # noqa
from ffun.library.tests.fixtures import *  # noqa
from ffun.llms_framework.tests.fixtures import *  # noqa
from ffun.ontology.tests.fixtures import *  # noqa
from ffun.parsers.tests.fixtures import *  # noqa
from ffun.resources.tests.fixtures import *  # noqa
from ffun.users.tests.fixtures import *  # noqa


@pytest_asyncio.fixture(autouse=True)  # type: ignore
async def detect_async_leaks(pytestconfig: pytest.Config) -> AsyncGenerator[None, None]:
    if not cast(bool, pytestconfig.getoption("detect_async_leaks")):
        yield
        return

    async with cast(AbstractAsyncContextManager[object], no_task_leaks(action=LeakAction.RAISE)):
        # TODO: Replace Rich exception rendering with a lightweight alternative; large tracebacks
        # can synchronously block the event loop long enough to trigger this detector.
        async with cast(
            AbstractAsyncContextManager[object],
            no_event_loop_blocking(action=LeakAction.RAISE, threshold=5.0),
        ):
            yield


@pytest_asyncio.fixture(scope="session", autouse=True)  # type: ignore
async def prepare_db(
    # app: AsyncGenerator[fastapi.FastAPI, None],
) -> AsyncGenerator[None, None]:
    # database migrations may be in an inconsistent state
    await migrations.rollback_all()

    await migrations.apply_all()
    yield
    await migrations.rollback_all()


@pytest_asyncio.fixture(scope="session", autouse=True)  # type: ignore
async def app(prepare_db: None) -> AsyncGenerator[fastapi.FastAPI, None]:
    with mock.patch("ffun.application.settings.settings.enable_api_spa", True):
        async with application.with_app() as app:
            yield app


@pytest_asyncio.fixture()  # type: ignore
async def client(app: fastapi.FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
