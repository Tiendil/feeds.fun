import asyncio
import contextlib

from yoyo import get_backend, read_migrations
from yoyo.migrations import MigrationList

from ffun.application import utils as app_utils
from ffun.application import workers as app_workers
from ffun.application.application import with_app
from ffun.application.settings import settings as app_settings
from ffun.core import migrations
from ffun.loader import domain as l_domain

from ..application import app


async def run() -> None:
    await migrations.apply_all()


@app.command()
def migrate() -> None:
    asyncio.run(run())
