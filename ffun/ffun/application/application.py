import asyncio
import contextlib

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from ffun.api import http_handlers as api_http_handlers
from ffun.auth.supertokens import use_supertokens
from ffun.core import logging, postgresql
from ffun.librarian.background_processors import create_background_processors
from ffun.loader.background_loader import FeedsLoader

from .settings import settings

_app = None


logger = logging.get_module_logger()


@contextlib.asynccontextmanager
async def use_postgresql():
    logger.info('initialize_postgresql')
    await postgresql.prepare_pool(name='ffun_pool',
                                  dsn='postgresql://ffun:ffun@localhost/ffun',
                                  min_size=20,
                                  max_size=None,
                                  timeout=1,
                                  num_workers=1)
    logger.info('postgresql_initialized')

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


@contextlib.asynccontextmanager
async def use_loader(app: fastapi.FastAPI):
    logger.info('feeds_loader_enabled')
    app.state.feeds_loader = FeedsLoader(name='ffun_feeds_loader',
                                         delay_between_runs=1)

    app.state.feeds_loader.start()

    logger.info('feeds_loader_initialized')

    try:
        yield
    finally:
        logger.info('deinitialize_feeds_loader')
        await app.state.feeds_loader.stop()
        logger.info('feeds_loader_deinitialized')


@contextlib.asynccontextmanager
async def use_librarian(app: fastapi.FastAPI):
    logger.info('librarian_enabled')

    app.state.entries_processors = create_background_processors()

    for processor in app.state.entries_processors:
        processor.start()

    logger.info('librarian_initialized')

    try:
        yield
    finally:
        logger.info('deinitialize_librarian')
        await asyncio.gather(*[processor.stop() for processor in app.state.entries_processors],
                             return_exceptions=True)
        logger.info('librarian_deinitialized')


def create_app(api: bool,  # noqa: CCR001
               loader: bool,
               librarian: bool,
               supertokens: bool):
    logging.initialize()

    logger.info('create_app')

    @contextlib.asynccontextmanager
    async def lifespan(app: fastapi.FastAPI):
        async with contextlib.AsyncExitStack() as stack:
            if supertokens:
                await stack.enter_async_context(use_supertokens(app,
                                                                app_name=settings.name,
                                                                api_domain=f'http://{settings.domain}:8000',
                                                                website_domain=f'http://{settings.domain}:5173'))

            await stack.enter_async_context(use_postgresql())

            if api:
                await stack.enter_async_context(use_api(app))

            if loader:
                await stack.enter_async_context(use_loader(app))

            if librarian:
                await stack.enter_async_context(use_librarian(app))

            await app.router.startup()

            yield

            await app.router.shutdown()

    app = fastapi.FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info('app_created')

    return app


def prepare_app(api: bool = False,
                loader: bool = False,
                librarian: bool = False,
                supertokens: bool = False):
    global _app

    _app = create_app(api=api, loader=loader, librarian=librarian, supertokens=supertokens)


def get_app():
    return _app


@contextlib.asynccontextmanager
async def with_app(**kwargs):

    prepare_app(**kwargs)

    app = get_app()

    async with app.router.lifespan_context(app):
        yield app
