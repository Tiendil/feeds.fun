from typing import Type

import pytest

from ffun.google import errors
from ffun.google.provider_interface import track_key_status
from ffun.llms_framework.entities import KeyStatus
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
