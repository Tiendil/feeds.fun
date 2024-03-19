import asyncio
import sys

from tabulate import tabulate

from ffun.application.application import with_app
from ffun.cli.application import app
from ffun.librarian.background_processors import processors
from ffun.librarian.domain import count_failed_entries, move_failed_entries_to_processor_queue


async def run_failed_entries_count() -> None:
    async with with_app():
        failed_entries_count = await count_failed_entries()

    table = []

    for processor_info in processors:
        table.append(
            [processor_info.id, processor_info.processor.name, failed_entries_count.get(processor_info.id, 0)]
        )

    sys.stdout.write(tabulate(table, headers=["processor id", "processor name", "failed entries"], tablefmt="grid"))


@app.command()
def failed_entries_count() -> None:
    asyncio.run(run_failed_entries_count())


async def run_failed_enties_move_to_queue(processor_id: int, limit: int) -> None:
    if not any(processor_info.id == processor_id for processor_info in processors):
        raise ValueError(f"Processor with id {processor_id} not found")

    async with with_app():
        await move_failed_entries_to_processor_queue(processor_id, limit=limit)
        await count_failed_entries()


@app.command()
def failed_entries_move_to_queue(processor_id: int, limit: int) -> None:
    asyncio.run(run_failed_enties_move_to_queue(processor_id, limit))
