from typing import Type
from unittest.mock import MagicMock

import pytest

from google.api_core import exceptions as google_core_exceptions

from ffun.llms_framework.entities import KeyStatus
from ffun.llms_framework.keys_statuses import Statuses
from ffun.google.provider_interface import track_key_status


class TestTrackKeyStatus:
    def test_works(self, api_key_statuses: Statuses) -> None:
        with track_key_status("key_1", api_key_statuses):
            pass

        assert api_key_statuses.get("key_1") == KeyStatus.works

    @pytest.mark.parametrize("exception, reason", [(google_core_exceptions.InvalidArgument, 'API_KEY_INVALID')])
    def test_authentication_error(self, exception: Type[Exception], reason: str, api_key_statuses: Statuses) -> None:
        with pytest.raises(exception):
            with track_key_status("key_1", api_key_statuses):
                raise exception("test-message", error_info=MagicMock(reason=reason))

        assert api_key_statuses.get("key_1") == KeyStatus.broken

    def test_unknown_argument_error(self, api_key_statuses: Statuses) -> None:
        with pytest.raises(google_core_exceptions.InvalidArgument):
            with track_key_status("key_1", api_key_statuses):
                raise google_core_exceptions.InvalidArgument("test-message", error_info=MagicMock(reason='XXX'))

        assert api_key_statuses.get("key_1") == KeyStatus.unknown

    @pytest.mark.parametrize("exception", [google_core_exceptions.TooManyRequests])
    def test_quota_error(self, exception: Type[Exception], api_key_statuses: Statuses) -> None:
        with pytest.raises(exception):
            with track_key_status("key_1", api_key_statuses):
                raise exception(message="test-message")  # type: ignore

        assert api_key_statuses.get("key_1") == KeyStatus.quota

    def test_unknown_google_error(self, api_key_statuses: Statuses) -> None:

        class FakeError(google_core_exceptions.GoogleAPIError):
            pass

        with pytest.raises(FakeError):
            with track_key_status("key_1", api_key_statuses):
                raise FakeError("test-message")

        assert api_key_statuses.get("key_1") == KeyStatus.unknown

    def test_non_google_error(self, api_key_statuses: Statuses) -> None:
        class FakeError(Exception):
            pass

        with pytest.raises(FakeError):
            with track_key_status("key_1", api_key_statuses):
                raise FakeError()

        assert api_key_statuses.get("key_1") == KeyStatus.unknown
