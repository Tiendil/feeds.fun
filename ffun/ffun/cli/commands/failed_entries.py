import asyncio
import contextlib

from ffun.application import utils as app_utils
from ffun.application import workers as app_workers
from ffun.application.application import with_app
from ffun.cli.application import app
from ffun.librarian.background_processors import processors
from ffun.librarian.domain import count_failed_entries
from ffun.loader import domain as l_domain
from tabulate import tabulate


async def run() -> None:
    async with with_app():
        failed_entries_count = await count_failed_entries()

    table = []

    for processor_info in processors:
        table.append([processor_info.processor.name, failed_entries_count.get(processor_info.id, 0)])

    print(tabulate(table, headers=['processor', 'failed entries'], tablefmt="grid"))


@app.command()
def failed_entries_count() -> None:
    asyncio.run(run())
