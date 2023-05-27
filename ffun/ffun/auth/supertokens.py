import contextlib
from typing import Any

import fastapi
from fastapi import FastAPI
from ffun.core import logging
from starlette.middleware.cors import CORSMiddleware
from supertokens_python import (InputAppInfo, SupertokensConfig,
                                get_all_cors_headers, init)
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.ingredients.emaildelivery.types import \
    EmailDeliveryConfig
from supertokens_python.recipe import dashboard, passwordless, session
from supertokens_python.recipe.passwordless import ContactEmailOnlyConfig
from supertokens_python.recipe.passwordless.types import (
    EmailDeliveryOverrideInput, EmailTemplateVars)

from .settings import settings

logger = logging.get_module_logger()


def custom_email_deliver(original_implementation: EmailDeliveryOverrideInput) -> EmailDeliveryOverrideInput:
    original_send_email = original_implementation.send_email

    async def send_email(template_vars: EmailTemplateVars, user_context: dict[str, Any]) -> None:
        assert template_vars.url_with_link_code is not None
        # By default: `${websiteDomain}/${websiteBasePath}/verify`
        template_vars.url_with_link_code = template_vars.url_with_link_code.replace(
            "/auth/verify", "/auth")
        return await original_send_email(template_vars, user_context)

    original_implementation.send_email = send_email
    return original_implementation


@contextlib.asynccontextmanager
async def use_supertokens(app_name: str,
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
                contact_config=ContactEmailOnlyConfig(),
                email_delivery=EmailDeliveryConfig(override=custom_email_deliver)
            ),
            dashboard.init(),
        ],
        mode=settings.supertokens.mode
    )

    logger.info('supertokens_initialized')

    yield


def add_middlewares(app: FastAPI) -> None:
    app.add_middleware(get_middleware())