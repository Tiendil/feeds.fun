import functools
import uuid
from typing import Any

import fastapi
import sentry_sdk
from fastapi.responses import JSONResponse

from ffun.core import api, logging
from ffun.core.errors import Error

logger = logging.get_module_logger()


_exception_code = "exception_code"


async def _handle_expected_error(request: fastapi.Request, error: Error) -> JSONResponse:
    # TODO: improve error processing
    code = error.__class__.__name__

    api_error = api.APIError(code=code)

    setattr(request.state, _exception_code, code)

    sentry_sdk.capture_exception(error)

    logger.exception(error.__class__.__name__, sentry_skip=True)

    return JSONResponse(status_code=500, content=api_error.model_dump())


async def _handle_unexpected_error(request: fastapi.Request, error: Exception) -> JSONResponse:
    # TODO: improve error processing

    code = error.__class__.__name__

    api_error = api.APIError(code=code, message="An unexpected error appeared. We are working on fixing it.")

    setattr(request.state, _exception_code, code)

    sentry_sdk.capture_exception(error)

    logger.exception(error.__class__.__name__, sentry_skip=True)

    return JSONResponse(status_code=500, content=api_error.model_dump())


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


async def request_id_middleware(request: fastapi.Request, call_next: Any) -> fastapi.Response:
    with logging.bound_log_args(request_uid=uuid.uuid4().hex):
        return await call_next(request)  # type: ignore


def _normalize_path(url: str) -> str | None:
    url = url.lower().rstrip("/")

    if "//" in url:
        return None

    return url


@functools.cache
def _existed_route_urls(app: fastapi.FastAPI) -> set[str]:
    # cache should be all right here because app is singleton

    urls = set()

    for route in app.routes:
        url = _normalize_path(route.path)  # type: ignore

        if "{" in url:
            raise NotImplementedError()

        urls.add(url)

    return urls


# TODO: add support for special exceptions raised from views
async def request_measure_middleware(request: fastapi.Request, call_next: Any) -> fastapi.Response:
    app = request.scope.get("app")

    assert app is not None

    path = _normalize_path(request.scope.get("path"))  # type: ignore

    if path not in _existed_route_urls(app):
        path = "wrong"

    with logger.measure_block_time("request_time", http_path=path) as extra_labels:
        extra_labels["result"] = "success"
        extra_labels["status_code"] = None
        extra_labels["error_code"] = None

        response = await call_next(request)

        extra_labels["status_code"] = response.status_code

        if hasattr(request.state, _exception_code):
            extra_labels["error_code"] = getattr(request.state, _exception_code)
            extra_labels["result"] = "error"

        assert isinstance(response, fastapi.Response)

        return response
