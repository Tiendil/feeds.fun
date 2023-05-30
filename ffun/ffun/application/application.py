import asyncio
import contextlib

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from ffun.api import http_handlers as api_http_handlers
from ffun.auth import supertokens as st
from ffun.core import logging, postgresql
from ffun.librarian.background_processors import create_background_processors
from ffun.loader.background_loader import FeedsLoader

from . import errors
from .settings import settings

logger = logging.get_module_logger()


@contextlib.asynccontextmanager
async def use_postgresql():
    logger.info('initialize_postgresql')
    # TODO: move to settings
    await postgresql.prepare_pool(name='ffun_pool',
                                  dsn='postgresql://ffun:ffun@postgresql/ffun',
                                  # dsn='postgresql://ffun:ffun@localhost/ffun',
                                  min_size=20,
                                  max_size=None,
                                  timeout=0.1,
                                  num_workers=1)
    logger.info('postgresql_initialized')

    try:
        await postgresql.execute('''SELECT 1''')
    except Exception as e:
        raise errors.CanNotAccessPostgreSQL() from e

    try:
        yield
    finally:
        logger.info('deinitialize_postgresql')
        await postgresql.destroy_pool()
        logger.info('postgresql_deinitialized')


@contextlib.asynccontextmanager
async def use_api(app: fastapi.FastAPI):
    logger.info('api_enabled')
    app.include_router(api_http_handlers.router)

    logger.info('api_initialized')

    yield

    logger.info('api_deinitialized')


def create_app():  # noqa: CCR001
    logging.initialize()

    logger.info('create_app')

    @contextlib.asynccontextmanager
    async def lifespan(app: fastapi.FastAPI):
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(use_postgresql())

            if settings.enable_supertokens:
                await stack.enter_async_context(st.use_supertokens(app_name=settings.name,
                                                                   api_domain=f'http://{settings.domain}:8000',
                                                                   website_domain=f'http://{settings.domain}:5173'))

            if settings.enable_api:
                await stack.enter_async_context(use_api(app))

            await app.router.startup()

            yield

            await app.router.shutdown()

    app = fastapi.FastAPI(lifespan=lifespan)

    st.add_middlewares(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost",
                       "http://localhost:5173",
                       "http://127.0.0.1",
                       "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info('app_created')

    return app


@contextlib.asynccontextmanager
async def with_app(**kwargs):
    async with app.router.lifespan_context(app):
        yield app


app = create_app()
