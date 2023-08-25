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
