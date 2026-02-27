import asyncio

from ffun.cli.application import app
from ffun.core import migrations


async def run() -> None:
    await migrations.apply_all()


@app.command()  # type: ignore
def migrate() -> None:
    asyncio.run(run())
