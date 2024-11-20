import asyncio

import datetime
import typer

from ffun.application.application import with_app
from httpx import ASGITransport, AsyncClient

from ffun.cli.commands import cleaner  # noqa: F401
from ffun.cli.commands import metrics  # noqa: F401
from ffun.cli.commands import processors_quality  # noqa: F401
from ffun.cli.commands import user_settings  # noqa: F401
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.domain.entities import UserId
from ffun.api.http_handlers import _external_entries
from ffun.api.entities import GetLastEntriesResponse
from ffun.core import logging

app = typer.Typer()

logger = logging.get_module_logger()


async def profiled_code() -> None:
    backup_time_str = "2024-11-13 22:58:46.876683"
    backup_time = datetime.datetime.fromisoformat(backup_time_str)

    user_id = UserId('59da1b8f-c0c4-416f-908d-85daecfb1726')
    period = datetime.datetime.now() - backup_time + datetime.timedelta(days=3)
    max_returned_entries = 10000

    linked_feeds = await fl_domain.get_linked_feeds(user_id)

    linked_feeds_ids = [link.feed_id for link in linked_feeds]

    entries = await l_domain.get_entries_by_filter(
        feeds_ids=linked_feeds_ids, period=period, limit=max_returned_entries
    )

    external_entries, tags_mapping = await _external_entries(entries, with_body=False, user_id=user_id)

    logger.info("almost_finishied", entries_number=len(external_entries), tags_number=len(tags_mapping))

    return GetLastEntriesResponse(entries=external_entries, tagsMapping=tags_mapping)


async def run_experiment() -> None:
    async with with_app():
        logger.info("experiment_started")

        for _ in range(100):
            await profiled_code()

        logger.info("experiment_finished")


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())


app.add_typer(processors_quality.cli_app, name="processors-quality")
app.add_typer(user_settings.cli_app, name="user-settings")
app.add_typer(cleaner.cli_app, name="cleaner")
app.add_typer(metrics.cli_app, name="metrics")


if __name__ == "__main__":
    app()
