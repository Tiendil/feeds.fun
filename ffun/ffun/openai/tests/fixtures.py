from typing import Any

import pytest
from pytest_mock import MockerFixture


class MockedOpenAIClient:

    def __init__(self, check_api_key: Any, request: Any) -> None:
        self.check_api_key = check_api_key
        self.request = request


# TODO: change to session scope
@pytest.fixture(autouse=True)
def mocked_openai_client(mocker: MockerFixture) -> MockedOpenAIClient:
    """Protection from calling OpenAI API during tests."""
    check_api_key = mocker.patch("ffun.openai.client.check_api_key")
    request = mocker.patch("ffun.openai.client.request")

    return MockedOpenAIClient(check_api_key=check_api_key,
                              request=request)
