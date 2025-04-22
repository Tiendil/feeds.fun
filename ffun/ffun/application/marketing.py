from typing import Annotated

from typing import Any
import fastapi
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from ffun.core import logging
from ffun.domain.entities import UserId
from ffun.auth.settings import AuthMode, settings
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities
from ffun.auth.dependencies import OptionalUser


logger = logging.get_module_logger()


# Straightforward implementation:
#
# 1. Frontend set cookies whenever user comes from utm link
# 2. If backend detect utm cookies for registered user,
#    it sends business event (in depdency) and remove cookies (in middleware)


_utm_keys = {'ffun_utm_source': 'utm_source', 'ffun_utm_medium': 'utm_medium', 'ffun_utm_campaign': 'utm_campaign'}


# TODO: test
async def _process_utm(request: fastapi.Request, user: OptionalUser) -> None:

    if user is None:
        return

    utm = {event_attr_name: request.cookies.get(cookie_name)
           for cookie_name, event_attr_name in _utm_keys.items()
           if cookie_name in request.cookies}

    if not utm:
        return

    logger.business_event("user_utm", user.id, **utm)


process_utm = fastapi.Depends(_process_utm)


# TODO: test
async def clean_utm_cookies_middleware(request: fastapi.Request, call_next: Any) -> fastapi.Response:
    response = await call_next(request)

    for cookie_name in _utm_keys.keys():
        if cookie_name in request.cookies:
            response.delete_cookie(cookie_name)

    return response
