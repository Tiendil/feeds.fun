import uuid
from unittest.mock import AsyncMock, MagicMock

import fastapi
import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from ffun.core import errors, json, logging
from ffun.core.middlewares import (
    _existed_route_urls,
    _handle_api_error,
    _handle_unexpected_error,
    _normalize_path,
    request_id_middleware,
)
from ffun.core.tests.helpers import capture_logs

logger = logging.get_module_logger()


class FakeError(errors.Error):
    pass


class TestHandleAPIError:

    @pytest.mark.asyncio
    async def test(self, mocker: MockerFixture) -> None:
        capture_exception = mocker.patch("sentry_sdk.capture_exception")

        error = errors.APIError(code="some.error.code", message="some message")

        request = MagicMock()

        with capture_logs() as logs:
            response = await _handle_api_error(request, error)

        assert request.state.api_error_code == "some.error.code"

        capture_exception.assert_not_called()

        assert logs == [
            {
                "event": "api_error",
                "log_level": "info",
                "module": "ffun.core.middlewares",
                "code": "some.error.code",
                "message": "some message",
            }
        ]

        assert response.status_code == 200

        assert json.parse(response.body.decode()) == {
            "status": "error",
            "code": "some.error.code",
            "message": "some message",
            "data": None,
        }


class TestHandleUnexpectedError:

    @pytest.mark.asyncio
    async def test(self, mocker: MockerFixture) -> None:
        capture_exception = mocker.patch("sentry_sdk.capture_exception")

        error = FakeError(message="some message")

        request = MagicMock()

        with capture_logs() as logs:
            response = await _handle_unexpected_error(request, error)

        assert request.state.internal_error_code == "FakeError"

        capture_exception.assert_called_once_with(error)

        assert logs == [
            {
                "event": "FakeError",
                "log_level": "error",
                "exc_info": True,
                "module": "ffun.core.middlewares",
                "sentry_skip": True,
            }
        ]

        assert response.status_code == 500
        assert json.parse(response.body.decode()) == {
            "status": "error",
            "code": "FakeError",
            "message": "An unexpected error appeared. We are working on fixing it.",
            "data": None,
        }


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

    @pytest.mark.parametrize(
        "url, expected",
        [
            ("/test", "/test"),
            ("/test/", "/test"),
            ("/test//", "/test"),
            ("/test/b", "/test/b"),
            ("/test/b/", "/test/b"),
            ("/test/b//", "/test/b"),
            ("/test//test", None),
            ("/test//test/", None),
        ],
    )
    def test(self, url: str, expected: str) -> None:
        assert _normalize_path(url) == expected


class TestExistedRouteUrls:

    @pytest.mark.asyncio
    async def test(self, app: fastapi.FastAPI) -> None:
        assert _existed_route_urls(app) == {
            "/api/get-rules",
            "/api/get-collections",
            "/api/add-opml",
            "/api/delete-rule",
            "/api/add-feed",
            "/api/unsubscribe",
            "/api/docs",
            "/api/get-entries-by-ids",
            "/api/get-last-entries",
            "/api/subscribe-to-collections",
            "/api/test/ok",
            "/api/set-user-setting",
            "/api/test/internal-error",
            "/api/test/expected-error",
            "/api/get-collection-feeds",
            "/api/set-marker",
            "/api/get-score-details",
            "/api/discover-feeds",
            "/api/get-user-settings",
            "/api/get-resource-history",
            "/api/create-or-update-rule",
            "/api/get-feeds",
            "/api/get-info",
            "/api/get-tags-info",
            "/api/update-rule",
            "/api/openapi.json",
            "/api/remove-marker",
            "/api/track-event",
        }


class TestRequestMeasureMiddleware:

    @pytest.mark.asyncio
    async def test(self, client: AsyncClient) -> None:
        with capture_logs() as logs:
            await client.post("/api/test/ok")

        assert logs == [
            {
                "module": "ffun.core.middlewares",
                "m_kind": "measure",
                "m_value": logs[0]["m_value"],
                "event": "request_time",
                "request_uid": logs[0]["request_uid"],
                "m_labels": {"http_path": "/api/test/ok", "result": "success", "status_code": 200, "error_code": None},
                "log_level": "info",
            }
        ]

    @pytest.mark.asyncio
    async def test_other_status_code(self, client: AsyncClient) -> None:
        with capture_logs() as logs:
            await client.get("/api/test/ok")

        assert logs == [
            {
                "module": "ffun.core.middlewares",
                "m_kind": "measure",
                "m_value": logs[0]["m_value"],
                "event": "request_time",
                "request_uid": logs[0]["request_uid"],
                "m_labels": {"http_path": "/api/test/ok", "result": "success", "status_code": 405, "error_code": None},
                "log_level": "info",
            }
        ]

    @pytest.mark.asyncio
    async def test_wrong_url(self, client: AsyncClient) -> None:
        with capture_logs() as logs:
            await client.post("/api/bla-bla-bla")

        assert logs == [
            {
                "module": "ffun.core.middlewares",
                "m_kind": "measure",
                "m_value": logs[0]["m_value"],
                "event": "request_time",
                "request_uid": logs[0]["request_uid"],
                "m_labels": {"http_path": "wrong", "result": "success", "status_code": 404, "error_code": None},
                "log_level": "info",
            }
        ]

    @pytest.mark.asyncio
    async def test_internal_error(self, client: AsyncClient) -> None:
        with capture_logs() as logs:
            await client.post("/api/test/internal-error")

        assert logs[1] == {
            "module": "ffun.core.middlewares",
            "m_kind": "measure",
            "m_value": logs[1]["m_value"],
            "event": "request_time",
            "request_uid": logs[1]["request_uid"],
            "m_labels": {
                "http_path": "/api/test/internal-error",
                "result": "internal_error",
                "status_code": 500,
                "error_code": "Exception",
            },
            "log_level": "info",
        }

    @pytest.mark.asyncio
    async def test_expected_error(self, client: AsyncClient) -> None:
        with capture_logs() as logs:
            await client.post("/api/test/expected-error")

        assert logs[1] == {
            "module": "ffun.core.middlewares",
            "m_kind": "measure",
            "m_value": logs[1]["m_value"],
            "event": "request_time",
            "request_uid": logs[1]["request_uid"],
            "m_labels": {
                "http_path": "/api/test/expected-error",
                "result": "api_error",
                "status_code": 200,
                "error_code": "expected_test_error",
            },
            "log_level": "info",
        }
