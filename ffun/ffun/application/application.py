import asyncio
import contextlib
from typing import AsyncGenerator

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from ffun.api import http_handlers as api_http_handlers
from ffun.application import errors
from ffun.application.settings import settings
from ffun.auth import supertokens as st
from ffun.auth.settings import AuthMode
from ffun.auth.settings import settings as auth_settings
from ffun.core import logging, middlewares, postgresql, sentry
from ffun.feeds_collections.collections import collections

logger = logging.get_module_logger()


def initialize_user_settings() -> None:
    logger.info("initialize_user_settings")
    import ffun.application.user_settings  # noqa: F401


@contextlib.asynccontextmanager
async def use_postgresql() -> AsyncGenerator[None, None]:
    logger.info("initialize_postgresql")
    await postgresql.prepare_pool(
        name="ffun_pool",
        dsn=settings.postgresql.dsn,
        min_size=settings.postgresql.pool_min_size,
        max_size=settings.postgresql.pool_max_size,
        timeout=settings.postgresql.pool_timeout,
        num_workers=settings.postgresql.pool_num_workers,
        max_lifetime=settings.postgresql.pool_max_lifetime,
    )
    logger.info("postgresql_initialized")

    refresher = asyncio.create_task(
        postgresql.pool_refresher(settings.postgresql.pool_check_period), name="poll_refresher"
    )

    try:
        await postgresql.execute("""SELECT 1""")
    except Exception as e:
        raise errors.CanNotAccessPostgreSQL() from e

    try:
        yield
    finally:
        logger.info("deinitialize_postgresql")

        refresher.cancel()

        await postgresql.destroy_pool()

        logger.info("postgresql_deinitialized")


@contextlib.asynccontextmanager
async def use_api(app: fastapi.FastAPI) -> AsyncGenerator[None, None]:
    logger.info("api_enabled")
    app.include_router(api_http_handlers.router)

    logger.info("api_initialized")

    yield

    logger.info("api_deinitialized")


@contextlib.asynccontextmanager
async def use_sentry() -> AsyncGenerator[None, None]:
    logger.info("sentry_enabled")

    sentry.initialize(
        dsn=settings.sentry.dsn,
        sample_rate=settings.sentry.sample_rate,
        traces_sample_rate=settings.sentry.traces_sample_rate,
        environment=settings.environment,
    )

    logger.info("sentry_initialized")

    yield

    logger.info("sentry_disabled")


def smart_url(domain: str, port: int) -> str:
    if port == 80:
        return f"http://{domain}"

    if port == 443:
        return f"https://{domain}"

    return f"http://{domain}:{port}"


def create_app() -> fastapi.FastAPI:  # noqa: CCR001
    logging.initialize(use_sentry=settings.enable_sentry)

    logger.info("create_app")

    @contextlib.asynccontextmanager
    async def lifespan(app: fastapi.FastAPI) -> AsyncGenerator[None, None]:
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(use_postgresql())

            if settings.enable_sentry:
                await stack.enter_async_context(use_sentry())

            if auth_settings.mode == AuthMode.supertokens:
                api_domain = smart_url(settings.app_domain, settings.api_port)
                website_domain = smart_url(settings.app_domain, settings.app_port)

                await stack.enter_async_context(
                    st.use_supertokens(
                        app_name=settings.app_name, api_domain=api_domain, website_domain=website_domain
                    )
                )

            if settings.enable_api:
                await stack.enter_async_context(use_api(app))

            await app.router.startup()

            await collections.initialize()

            initialize_user_settings()

            yield

            await app.router.shutdown()

    app = fastapi.FastAPI(
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        default_response_class=ORJSONResponse,
    )

    middlewares.initialize_error_processors(app)

    if auth_settings.mode == AuthMode.supertokens:
        st.add_middlewares(app)

    app.middleware("http")(middlewares.final_errors_middleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=False,
        allow_methods=[],
        allow_headers=[],
    )

    app.middleware("http")(middlewares.request_measure_middleware)

    app.middleware("http")(middlewares.request_id_middleware)

    logger.info("app_created")

    return app


@contextlib.asynccontextmanager
async def with_app() -> AsyncGenerator[fastapi.FastAPI, None]:
    async with app.router.lifespan_context(app):
        yield app


app = create_app()
