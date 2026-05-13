import asyncio
import sys

from tabulate import tabulate

from ffun.application.application import with_app
from ffun.cli.application import app
from ffun.dispatcher.domain import count_entries_by_processing_status, move_failed_entries_to_processor_queue
from ffun.dispatcher.entities import EntryProcessingStatus
from ffun.domain.entities import ProcessorId
from ffun.librarian.background_processors import processors


async def run_dispatcher_failed_entries_count() -> None:
    async with with_app():
        failed_entries_count = await count_entries_by_processing_status(EntryProcessingStatus.failed)

    table = []

    for processor_info in processors:
        table.append(
            [processor_info.id, processor_info.processor.name, failed_entries_count.get(processor_info.id, 0)]
        )

    sys.stdout.write(tabulate(table, headers=["processor id", "processor name", "failed entries"], tablefmt="grid"))


@app.command()  # type: ignore
def dispatcher_failed_entries_count() -> None:
    asyncio.run(run_dispatcher_failed_entries_count())


async def run_dispatcher_failed_entries_move_to_queue(processor_id: int, limit: int) -> None:
    typed_processor_id = ProcessorId(processor_id)

    if not any(processor_info.id == typed_processor_id for processor_info in processors):
        raise ValueError(f"Processor with id {processor_id} not found")

    async with with_app():
        await move_failed_entries_to_processor_queue(typed_processor_id, limit=limit)


@app.command()  # type: ignore
def dispatcher_failed_entries_move_to_queue(processor_id: int, limit: int) -> None:
    asyncio.run(run_dispatcher_failed_entries_move_to_queue(processor_id, limit))
