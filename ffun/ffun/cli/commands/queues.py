import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind

logger = logging.get_module_logger()

cli_app = typer.Typer()


def queue_kind_from_string(raw_queue: str) -> QueueKind:
    try:
        return QueueKind(int(raw_queue))
    except ValueError:
        pass

    try:
        return QueueKind[raw_queue]
    except KeyError as e:
        raise typer.BadParameter(f"unknown queue: {raw_queue}") from e


def validate_cleanup_request(clean_all: bool, queue: str | None, subqueue: int | None) -> None:
    match (clean_all, queue is not None, subqueue is not None):
        case (True, True, _):
            raise typer.BadParameter("--all can not be used with --queue")
        case (True, _, True):
            raise typer.BadParameter("--all can not be used with --subqueue")
        case (False, False, True):
            raise typer.BadParameter("--subqueue requires --queue")
        case (False, False, False):
            raise typer.BadParameter("provide --all or --queue")


async def cleanup_queues(clean_all: bool, queue: str | None, subqueue: int | None) -> None:
    validate_cleanup_request(clean_all=clean_all, queue=queue, subqueue=subqueue)

    if clean_all:
        logger.info("queues_cleanup_all_started")

        for queue_kind in QueueKind:
            await q_operations.tech_clear_queue(queue_kind)

        logger.info("queues_cleanup_all_finished")
        return

    assert queue is not None

    queue_kind = queue_kind_from_string(queue)

    logger.info("queue_cleanup_started", queue=queue_kind.name, primary_id=queue_kind.value, secondary_id=subqueue)

    await q_operations.tech_clear_queue(queue_kind, secondary_id=subqueue)

    logger.info("queue_cleanup_finished", queue=queue_kind.name, primary_id=queue_kind.value, secondary_id=subqueue)


async def run_cleanup(clean_all: bool, queue: str | None, subqueue: int | None) -> None:
    async with with_app():
        await cleanup_queues(clean_all=clean_all, queue=queue, subqueue=subqueue)


@cli_app.command()  # type: ignore
def cleanup(
    clean_all: bool = typer.Option(False, "--all"),
    queue: str | None = typer.Option(None, "--queue"),
    subqueue: int | None = typer.Option(None, "--subqueue"),
) -> None:
    validate_cleanup_request(clean_all=clean_all, queue=queue, subqueue=subqueue)
    asyncio.run(run_cleanup(clean_all=clean_all, queue=queue, subqueue=subqueue))
