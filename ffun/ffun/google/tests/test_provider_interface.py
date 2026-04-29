from typing import Type

import pytest
from pytest_mock import MockerFixture

from ffun.google import errors
from ffun.google.entities import ChatMessage, GoogleChatRequest
from ffun.google.provider_interface import GoogleInterface, track_key_status
from ffun.llms_framework import errors as llmsf_errors
from ffun.llms_framework.entities import KeyStatus, LLMConfiguration, LLMTokens
from ffun.llms_framework.keys_statuses import Statuses


class TestTrackKeyStatus:

    def test_works(self, api_key_statuses: Statuses) -> None:
        with track_key_status("key_1", api_key_statuses):
            pass

        assert api_key_statuses.get("key_1") == KeyStatus.works

    @pytest.mark.parametrize("exception", [errors.AuthError])
    def test_authentication_error(self, exception: Type[Exception], api_key_statuses: Statuses) -> None:
        with pytest.raises(exception):
            with track_key_status("key_1", api_key_statuses):
                raise exception()

        assert api_key_statuses.get("key_1") == KeyStatus.broken

    @pytest.mark.parametrize("exception", [errors.QuotaError])
    def test_quota_error(self, exception: Type[Exception], api_key_statuses: Statuses) -> None:
        with pytest.raises(exception):
            with track_key_status("key_1", api_key_statuses):
                raise exception()

        assert api_key_statuses.get("key_1") == KeyStatus.quota

    def test_unknown_client_error(self, api_key_statuses: Statuses) -> None:

        class FakeError(errors.ClientError):
            pass

        with pytest.raises(FakeError):
            with track_key_status("key_1", api_key_statuses):
                raise FakeError()

        assert api_key_statuses.get("key_1") == KeyStatus.unknown

    def test_non_google_error(self, api_key_statuses: Statuses) -> None:
        class FakeError(Exception):
            pass

        with pytest.raises(FakeError):
            with track_key_status("key_1", api_key_statuses):
                raise FakeError()

        assert api_key_statuses.get("key_1") == KeyStatus.unknown


class TestGoogleInterface:

    @pytest.fixture  # type: ignore
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(
            model="test-model",
            system="system prompt",
            max_return_tokens=LLMTokens(143),
            temperature=0,
            top_p=0,
        )

    @pytest.mark.parametrize("exception", [errors.AuthError, errors.QuotaError])
    @pytest.mark.asyncio
    async def test_rejected_request_errors(
        self, mocker: MockerFixture, llm_config: LLMConfiguration, exception: Type[Exception]
    ) -> None:
        mocker.patch("ffun.google.provider_interface.Client.generate_content", side_effect=exception())

        with pytest.raises(llmsf_errors.RequestWasRejected):
            await GoogleInterface().chat_request(
                config=llm_config,
                api_key="test-key",
                request=GoogleChatRequest(
                    system=ChatMessage(text="system prompt"), messages=[ChatMessage(role="user", text="user prompt")]
                ),
            )
