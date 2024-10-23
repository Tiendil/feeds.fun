import functools
import uuid
from typing import Any

import fastapi
from fastapi.responses import JSONResponse
from sentry_sdk import capture_exception

from ffun.core import api, logging
from ffun.core.errors import Error

logger = logging.get_module_logger()


async def _handle_expected_error(_: fastapi.Request, error: Error) -> JSONResponse:
    # TODO: improve error processing
    api_error = api.APIError(code=error.__class__.__name__)

    capture_exception(error)

    logger.exception(error.__class__.__name__, sentry_skip=True)

    return JSONResponse(status_code=500, content=api_error.dict())


async def _handle_unexpected_error(_: fastapi.Request, error: Exception) -> JSONResponse:
    # TODO: improve error processing
    api_error = api.APIError(
        code=error.__class__.__name__, message="An unexpected error appeared. We are working on fixing it."
    )

    capture_exception(error)

    logger.exception(error.__class__.__name__, sentry_skip=True)

    return JSONResponse(status_code=500, content=api_error.dict())


# TODO: move somewhere?
def initialize_error_processors(app: fastapi.FastAPI) -> fastapi.FastAPI:
    app.exception_handler(Error)(_handle_expected_error)
    return app


async def final_errors_middleware(request: fastapi.Request, call_next: Any) -> fastapi.Response:
    try:
        return await call_next(request)  # type: ignore
    except Error as e:
        return await _handle_expected_error(request, e)
    except Exception as e:
        return await _handle_unexpected_error(request, e)


# TODO: test
async def request_id_middleware(request: fastapi.Request, call_next: Any) -> fastapi.Response:
    with logging.bound_log_args(request_uid=uuid.uuid4().hex):
        return await call_next(request)  # type: ignore


# TODO: tests
def _normalize_path(url: str) -> str:
    return url.lower().rstrip("/")


# TODO: test
@functools.cache
def _existed_route_urls() -> set[str]:
    # TODO: move somewhere?
    from ffun.application.application import app

    urls = set()

    for route in app.routes:
        url = _normalize_path(route.path)

        if "{" in url:
            raise NotImplementedError()

        urls.add(url)

    return urls


async def request_measure_middleware(request: fastapi.Request, call_next: Any) -> fastapi.Response:

    app = request.scope.get("app")

    assert app is not None

    path = _normalize_path(request.scope.get("path"))

    if path not in _existed_route_urls():
        path = "wrong"

    with logger.measure_block_time("request_time", http_path=path) as extra_labels:
        extra_labels["success"] = "success"

        try:
            response = await call_next(request)
        except BaseException:
            extra_labels["success"] = "exception"

        extra_labels["status_code"] = response.status_code

        return response
