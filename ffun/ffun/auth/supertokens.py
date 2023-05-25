import contextlib

import fastapi
from fastapi import FastAPI
from ffun.core import logging
from starlette.middleware.cors import CORSMiddleware
from supertokens_python import (InputAppInfo, SupertokensConfig,
                                get_all_cors_headers, init)
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe import passwordless, session
from supertokens_python.recipe.passwordless import ContactEmailOnlyConfig

from .settings import settings

logger = logging.get_module_logger()


@contextlib.asynccontextmanager
async def use_supertokens(app: fastapi.FastAPI,
                          app_name: str,
                          api_domain: str,
                          website_domain: str,
                          api_base_path: str = "/auth",
                          website_base_path: str = "/auth"):
    logger.info('supertokens_enabled')

    init(
        app_info=InputAppInfo(
            app_name=app_name,
            api_domain=api_domain,
            website_domain=website_domain,
            api_base_path=api_base_path,
            website_base_path=website_base_path
        ),

        supertokens_config=SupertokensConfig(
            connection_uri=settings.supertokens.connection_uri,
            api_key=settings.supertokens.api_key
        ),
        framework='fastapi',
        recipe_list=[
            session.init(),
            passwordless.init(
                flow_type="MAGIC_LINK",
                contact_config=ContactEmailOnlyConfig()
            )
        ],
        mode=settings.supertokens.mode
    )

    logger.info('supertokens_initialized')

    yield
