from ffun.core import json
import pytest
from structlog.testing import capture_logs
from unittest.mock import MagicMock
from pytest_mock import MockerFixture
from ffun.core.middlewares import ( _handle_expected_error, _handle_unexpected_error, final_errors_middleware, initialize_error_processors, request_id_middleware, _normalize_path, _existed_route_urls, request_measure_middleware)
from ffun.core import errors
from ffun.core.tests.helpers import assert_logs
from fastapi.responses import JSONResponse


class FakeError(errors.Error):
    pass


class TestHandleExpectedError:

    @pytest.mark.asyncio
    async def test(self, mocker: MockerFixture) -> None:
        capture_exception = mocker.patch("sentry_sdk.capture_exception")

        error = FakeError(message="some message")

        with capture_logs() as logs:
            response = await _handle_expected_error(MagicMock(), error)

        capture_exception.assert_called_once_with(error)

        assert logs == [{"event": "FakeError", "log_level": "error", "exc_info": True, "module": "ffun.core.middlewares", "sentry_skip": True}]

        assert response.status_code == 500
        assert json.parse(response.body) == {"status":"error","code":"FakeError","message":"Unknown error","data":None}


class TestHandleUnexpectedError:

    @pytest.mark.asyncio
    async def test(self, mocker: MockerFixture) -> None:
        capture_exception = mocker.patch("sentry_sdk.capture_exception")

        error = Exception("some message")

        with capture_logs() as logs:
            response = await _handle_unexpected_error(MagicMock(), error)

        capture_exception.assert_called_once_with(error)

        assert logs == [{"event": "Exception", "log_level": "error", "exc_info": True, "module": "ffun.core.middlewares", "sentry_skip": True}]

        assert response.status_code == 500
        assert json.parse(response.body) == {"status":"error","code":"Exception","message":"An unexpected error appeared. We are working on fixing it.","data":None}
