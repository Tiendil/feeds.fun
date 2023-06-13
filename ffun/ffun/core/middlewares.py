
from fastapi.responses import JSONResponse
from sentry_sdk import capture_exception, capture_message

from . import api, logging
from .errors import Error

logger = logging.get_module_logger()


async def _handle_expected_error(_, error):
    # TODO: improve error processing
    api_error = api.APIError(code=error.__class__.__name__)

    capture_exception(error)

    logger.error(error.__class__.__name__, sentry_skip=True)

    return JSONResponse(status_code=500, content=api_error.dict())


async def _handle_unexpected_error(_, error):
    # TODO: improve error processing
    api_error = api.APIError(code=error.__class__.__name__,
                             message="An unexpected error appeared. We are working on fixing it.")

    capture_exception(error)

    logger.exception(error.__class__.__name__, sentry_skip=True)

    return JSONResponse(status_code=500, content=api_error.dict())


# TODO: move somewhere?
def initialize_error_processors(app):
    app.exception_handler(Error)(_handle_expected_error)
    return app


async def final_errors_middleware(request, call_next):
    try:
        return await call_next(request)
    except Error as e:
        return await _handle_expected_error(request, e)
    except Exception as e:
        return await _handle_unexpected_error(request, e)