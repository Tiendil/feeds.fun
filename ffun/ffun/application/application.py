
import contextlib

import fastapi
from ffun.core import postgresql

_app = None


async def initialize_postgresql() -> None:
    await postgresql.prepare_pool(name='ffun_pool',
                                  dsn='postgresql://ffun:ffun@localhost/ffun',
                                  min_size=20,
                                  max_size=None,
                                  timeout=1,
                                  num_workers=1)


async def deinitialize_postgresql() -> None:
    await postgresql.destroy_pool()


def initialize(app: fastapi.FastAPI) -> fastapi.FastAPI:

    return app


def create_app():

    app = fastapi.FastAPI()

    app.on_event("startup")(initialize_postgresql)
    app.on_event("shutdown")(deinitialize_postgresql)

    return app


def get_app():
    global _app

    if _app is None:
        _app = create_app()

    return _app


@contextlib.asynccontextmanager
async def with_app():

    app = get_app()

    await app.router.startup()

    yield app

    await app.router.shutdown()
