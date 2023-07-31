import asyncio
import contextlib

from yoyo import get_backend, read_migrations
from yoyo.migrations import MigrationList

from ffun import __path__ as ffun_path
from ffun.application import utils as app_utils
from ffun.application import workers as app_workers
from ffun.application.application import with_app
from ffun.application.settings import settings as app_settings
from ffun.loader import domain as l_domain

from ..application import app


ffun_root = ffun_path[0]


async def run() -> None:
    migrations: MigrationList = read_migrations(f"{ffun_root}/*/migrations")

    with get_backend(app_settings.postgresql.dsn_yoyo, "yoyo_migrations") as backend:
        migrations_to_apply: MigrationList = backend.to_apply(migrations)
        backend.apply_migrations(migrations_to_apply)


@app.command()
def migrate() -> None:
    asyncio.run(run())
