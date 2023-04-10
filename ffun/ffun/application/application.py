import contextlib
import logging

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from ffun.api import http_handlers as api_http_handlers
from ffun.core import postgresql
from ffun.loader.background_loader import FeedsLoader

_app = None


logger = logging.getLogger(__name__)


def initialize_logging() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info('Logging initialized')


@contextlib.asynccontextmanager
async def use_postgresql():
    await postgresql.prepare_pool(name='ffun_pool',
                                  dsn='postgresql://ffun:ffun@localhost/ffun',
                                  min_size=20,
                                  max_size=None,
                                  timeout=1,
                                  num_workers=1)

    try:
        yield
    finally:
        await postgresql.destroy_pool()


@contextlib.asynccontextmanager
async def use_api(app: fastapi.FastAPI):
    logger.info('API enabled')
    app.include_router(api_http_handlers.router)

    yield


@contextlib.asynccontextmanager
async def use_loader(app: fastapi.FastAPI):
    logger.info('Feeds Loader enabled')
    app.state.feeds_loader = FeedsLoader(name='ffun_feeds_loader',
                                         delay_between_runs=1)

    app.state.feeds_loader.start()

    try:
        yield
    finally:
        await app.state.feeds_loader.stop()


@contextlib.asynccontextmanager
async def use_librarian(app: fastapi.FastAPI):
    logger.info('Librarian enabled')
    raise NotImplementedError()
    yield


def create_app(api: bool, loader: bool, librarian: bool):
    initialize_logging()

    @contextlib.asynccontextmanager
    async def lifespan(app: fastapi.FastAPI):
        async with (use_postgresql(),
                    use_api(app) if api else contextlib.nullcontext(),
                    use_loader(app) if loader else contextlib.nullcontext(),
                    use_librarian(app) if librarian else contextlib.nullcontext()):
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

    return app


def prepare_app(api: bool = False,
                loader: bool = False,
                librarian: bool = False):
    global _app

    _app = create_app(api=api, loader=loader, librarian=librarian)


def get_app():
    return _app


@contextlib.asynccontextmanager
async def with_app(**kwargs):

    prepare_app(**kwargs)

    app = get_app()

    async with app.router.lifespan_context(app):
        yield app
