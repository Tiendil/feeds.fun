import uuid
from typing import Any

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from ffun.domain.datetime_intervals import month_interval_start
from ffun.resources import domain as r_domain
from ffun.user_settings import domain as us_domain


class MockedOpenAIClient:
    def __init__(self, check_api_key: Any, request: Any) -> None:
        self.check_api_key = check_api_key
        self.request = request


# async def _fake_check_api_key(api_key: str) -> KeyStatus:
#     statuses.set(api_key, KeyStatus.works)
#     return KeyStatus.works


# # TODO: change to session scope
# @pytest.fixture(autouse=True)
# def mocked_openai_client(mocker: MockerFixture) -> MockedOpenAIClient:
#     """Protection from calling OpenAI API during tests."""
#     check_api_key = mocker.patch("ffun.openai.client.check_api_key", _fake_check_api_key)

#     request = mocker.patch("ffun.openai.client.request")

#     return MockedOpenAIClient(check_api_key=check_api_key, request=request)


@pytest.fixture
def openai_key() -> str:
    return uuid.uuid4().hex


# TODO: refactor
# @pytest.fixture(autouse=True, scope="session")
# def collections_api_key_must_be_turned_off_in_tests_by_default() -> None:
#     assert settings.collections_api_key is None, "collections_api_key must be turned off in tests by default"


# TODO: refactor
# @pytest.fixture(autouse=True, scope="session")
# def general_api_key_must_be_turned_off_in_tests_by_default() -> None:
#     assert settings.general_api_key is None, "general_api_key must be turned off in tests by default"
