import datetime
from typing import Type
from unittest.mock import MagicMock

import pytest
import openai

from ffun.llms_framework.entities import KeyStatus
from ffun.llms_framework.keys_statuses import Statuses
from ffun.openai.provider_interface import track_key_status


class TestTrackKeyStatus:
    def test_works(self, statuses: Statuses) -> None:
        with track_key_status("key_1", statuses):
            pass

        assert statuses.get("key_1") == KeyStatus.works

    @pytest.mark.parametrize("exception", [openai.AuthenticationError, openai.PermissionDeniedError])
    def test_authentication_error(self, exception: Type[Exception], statuses: Statuses) -> None:
        with pytest.raises(exception):
            with track_key_status("key_1", statuses):
                raise exception(message="test-message", response=MagicMock(), body=MagicMock())  # type: ignore

        assert statuses.get("key_1") == KeyStatus.broken

    @pytest.mark.parametrize("exception", [openai.RateLimitError])
    def test_quota_error(self, exception: Type[Exception], statuses: Statuses) -> None:
        with pytest.raises(exception):
            with track_key_status("key_1", statuses):
                raise exception(message="test-message", response=MagicMock(), body=MagicMock())  # type: ignore

        assert statuses.get("key_1") == KeyStatus.quota
