import functools
import uuid
from typing import Any

import fastapi
import sentry_sdk
from fastapi.responses import JSONResponse

from ffun.core import api, errors, logging

logger = logging.get_module_logger()


async def _handle_api_error(request: fastapi.Request, error: errors.APIError) -> JSONResponse:
    # TODO: improve error processing

    api_error = api.APIError(code=error.code, message=error.message)  # type: ignore

    logger.info("api_error", code=error.code, message=error.message)  # type: ignore

    request.state.api_error_code = error.code  # type: ignore

    return JSONResponse(status_code=200, content=api_error.model_dump())


async def _handle_unexpected_error(request: fastapi.Request, error: BaseException) -> JSONResponse:
    # TODO: improve error processing

    code = error.__class__.__name__

    api_error = api.APIError(code=code, message="An unexpected error appeared. We are working on fixing it.")

    request.state.internal_error_code = code

    sentry_sdk.capture_exception(error)

    logger.exception(error.__class__.__name__, sentry_skip=True)

    return JSONResponse(status_code=500, content=api_error.model_dump())


# TODO: move somewhere?
def initialize_error_processors(app: fastapi.FastAPI) -> fastapi.FastAPI:
    app.exception_handler(errors.Error)(_handle_api_error)
    return app


async def final_errors_middleware(request: fastapi.Request, call_next: Any) -> fastapi.Response:
    try:
        return await call_next(request)  # type: ignore
    except errors.APIError as e:
        return await _handle_api_error(request, e)
    except BaseException as e:
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

        if url is None:
            raise NotImplementedError()

        if "{" in url:
            raise NotImplementedError()

        urls.add(url)

    return urls


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

        if hasattr(request.state, "api_error_code"):
            extra_labels["error_code"] = request.state.api_error_code
            extra_labels["result"] = "api_error"

        if hasattr(request.state, "internal_error_code"):
            extra_labels["error_code"] = request.state.internal_error_code
            extra_labels["result"] = "internal_error"

        assert isinstance(response, fastapi.Response)

        return response
