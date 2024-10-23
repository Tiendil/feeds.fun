import uuid
import fastapi
from ffun.core import json
import pytest
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs
from unittest.mock import MagicMock, AsyncMock
from pytest_mock import MockerFixture
from ffun.core.middlewares import ( _handle_expected_error, _handle_unexpected_error, final_errors_middleware, initialize_error_processors, request_id_middleware, _normalize_path, _existed_route_urls, request_measure_middleware)
from ffun.core import errors
from ffun.core.tests.helpers import assert_logs
from fastapi.responses import JSONResponse
from ffun.core import logging
from ffun.core.tests.helpers import assert_log_context_vars

logger = logging.get_module_logger()



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


class TestRequestIdMiddleware:

    @pytest.mark.asyncio
    async def test(self, mocker: MockerFixture) -> None:
        bound_log_args = mocker.patch("ffun.core.logging.bound_log_args")

        await request_id_middleware(MagicMock(), AsyncMock())
        logger.info("request_id_test")

        assert bound_log_args.call_count == 1

        call = bound_log_args.call_args_list[0]

        assert uuid.UUID(call[1]["request_uid"])

    @pytest.mark.asyncio
    async def test_uniqueness(self, mocker: MockerFixture) -> None:
        bound_log_args = mocker.patch("ffun.core.logging.bound_log_args")

        await request_id_middleware(MagicMock(), AsyncMock())
        await request_id_middleware(MagicMock(), AsyncMock())

        logger.info("request_id_test")

        assert bound_log_args.call_count == 2

        call_1 = bound_log_args.call_args_list[0]
        call_2 = bound_log_args.call_args_list[1]

        assert call_1[1]["request_uid"] != call_2[1]["request_uid"]


class TestNormalizePath:

    @pytest.mark.parametrize("url, expected", [
        ("/test", "/test"),
        ("/test/", "/test"),
        ("/test//", "/test"),
        ("/test/b", "/test/b"),
        ("/test/b/", "/test/b"),
        ("/test/b//", "/test/b"),
        ("/test//test", None),
        ("/test//test/", None),
    ])
    def test(self, url: str, expected: str) -> None:
        assert _normalize_path(url) == expected


class TestExistedRouteUrls:

    @pytest.mark.asyncio
    async def test(self, app: fastapi.FastAPI) -> None:
        assert _existed_route_urls(app) == {'/api/get-rules',
                                            '/api/get-collections',
                                            '/api/add-opml',
                                            '/api/delete-rule',
                                            '/api/add-feed',
                                            '/api/unsubscribe',
                                            '/api/docs',
                                            '/api/get-entries-by-ids',
                                            '/api/get-last-entries',
                                            '/api/subscribe-to-collections',
                                            '/api/ok',
                                            '/api/set-user-setting',
                                            '/api/error',
                                            '/api/get-collection-feeds',
                                            '/api/set-marker',
                                            '/api/get-score-details',
                                            '/api/discover-feeds',
                                            '/api/get-user-settings',
                                            '/api/get-resource-history',
                                            '/api/create-or-update-rule',
                                            '/api/get-feeds',
                                            '/api/get-info',
                                            '/api/get-tags-info',
                                            '/api/update-rule',
                                            '/api/openapi.json',
                                            '/api/remove-marker'}


# class TestRequestMeasureMiddleware:

#     @pytest.mark.asyncio
#     async def test(self, client: AsyncClient) -> None:
#         bound_measure_labels = mocker.patch("ffun.core.logging.bound_measure_labels")

#         with capture_logs() as logs:
#             response = await client.get("/api/ok")

#         assert logs == [{"event": "request_time", "log_level": "info", "http_path": "/api/ok", "success": "success"}]

    # @pytest.mark.asyncio
    # async def test_wrong_path(self, mocker: MockerFixture) -> None:
    #     app = MagicMock()
    #     app.routes = [MagicMock(path="/test")]

    #     request = MagicMock()
    #     request.scope = {"app": app, "path": "/wrong"}

    #     with capture_logs() as logs:
    #         await request_measure_middleware(request, AsyncMock())

    #     assert logs == [{"event": "request_time", "log_level": "info", "http_path": "wrong", "success": "success"}]

    # @pytest.mark.asyncio
    # async def test_exception(self, mocker: MockerFixture) -> None:
    #     app = MagicMock()
    #     app.routes = [MagicMock(path="/test")]

    #     request = MagicMock()
    #     request.scope = {"app": app, "path": "/test"}

    #     with capture_logs() as logs:
    #         await request_measure_middleware(request, AsyncMock(side_effect=Exception()))

    #     assert logs == [{"event": "request_time", "log_level": "info", "http_path": "/test", "success": "exception"}]
