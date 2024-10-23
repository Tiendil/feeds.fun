import pytest
from typing import AsyncGenerator, Generator
from pytest_mock import MockerFixture
import fastapi
import pytest_asyncio
from unittest import mock
from fastapi.testclient import TestClient
from ffun.application import application
from ffun.core import migrations
from ffun.feeds.tests.fixtures import *  # noqa
from ffun.feeds_collections.tests.fixtures import *  # noqa
from ffun.librarian.processors.tests.fixtures import *  # noqa
from ffun.librarian.tests.fixtures import *  # noqa
from ffun.library.tests.fixtures import *  # noqa
from ffun.llms_framework.tests.fixtures import *  # noqa
from ffun.ontology.tests.fixtures import *  # noqa
from ffun.users.tests.fixtures import *  # noqa


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db(
    # app: AsyncGenerator[fastapi.FastAPI, None],
) -> AsyncGenerator[None, None]:
    # database migrations may be in an inconsistent state
    await migrations.rollback_all()

    await migrations.apply_all()
    yield
    await migrations.rollback_all()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def app(prepare_db: None) -> AsyncGenerator[fastapi.FastAPI, None]:
    with mock.patch('ffun.application.settings.settings.enable_api', True):
        async with application.with_app() as app:
            yield app


@pytest.fixture
def client(app: fastapi.FastAPI) -> Generator[TestClient, None, None]:
    yield TestClient(app, raise_server_exceptions=True, follow_redirects=False)
