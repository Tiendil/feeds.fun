from typing import Type
from unittest.mock import MagicMock

import openai
import pytest
from pytest_mock import MockerFixture

from ffun.llms_framework import errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, LLMTokens
from ffun.llms_framework.keys_statuses import Statuses
from ffun.openai.provider_interface import OpenAIChatRequest, OpenAIInterface, track_key_status


class FakeOpenAIResponses:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def create(self, **kwargs: object) -> object:
        raise self.error


class FakeOpenAIClient:
    def __init__(self, error: Exception) -> None:
        self.responses = FakeOpenAIResponses(error)


class TestTrackKeyStatus:
    def test_works(self, api_key_statuses: Statuses) -> None:
        with track_key_status("key_1", api_key_statuses):
            pass

        assert api_key_statuses.get("key_1") == KeyStatus.works

    @pytest.mark.parametrize("exception", [openai.AuthenticationError, openai.PermissionDeniedError])
    def test_authentication_error(self, exception: Type[Exception], api_key_statuses: Statuses) -> None:
        with pytest.raises(exception):
            with track_key_status("key_1", api_key_statuses):
                raise exception(message="test-message", response=MagicMock(), body=MagicMock())  # type: ignore

        assert api_key_statuses.get("key_1") == KeyStatus.broken

    @pytest.mark.parametrize("exception", [openai.RateLimitError])
    def test_quota_error(self, exception: Type[Exception], api_key_statuses: Statuses) -> None:
        with pytest.raises(exception):
            with track_key_status("key_1", api_key_statuses):
                raise exception(message="test-message", response=MagicMock(), body=MagicMock())  # type: ignore

        assert api_key_statuses.get("key_1") == KeyStatus.quota


class TestOpenAIInterface:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    @pytest.mark.parametrize(
        "exception",
        [openai.AuthenticationError, openai.PermissionDeniedError, openai.RateLimitError],
    )
    @pytest.mark.asyncio
    async def test_rejected_request_errors(
        self, mocker: MockerFixture, llm_config: LLMConfiguration, exception: Type[Exception]
    ) -> None:
        rejected_error = exception(message="test-message", response=MagicMock(), body=MagicMock())  # type: ignore
        mocker.patch("ffun.openai.provider_interface._client", return_value=FakeOpenAIClient(rejected_error))

        with pytest.raises(errors.RequestWasRejected):
            await OpenAIInterface().chat_request(
                config=llm_config,
                api_key="test-key",
                request=OpenAIChatRequest(system="system prompt", user="user prompt"),
            )
