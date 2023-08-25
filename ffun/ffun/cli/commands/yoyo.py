import asyncio

from ffun.core import migrations

from ..application import app


async def run() -> None:
    await migrations.apply_all()


@app.command()
def migrate() -> None:
    asyncio.run(run())
