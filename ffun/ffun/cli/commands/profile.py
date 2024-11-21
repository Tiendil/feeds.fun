import asyncio
import datetime

import typer

from ffun.api.entities import GetLastEntriesResponse
from ffun.api.http_handlers import _external_entries
from ffun.application.application import with_app
from ffun.cli.commands import cleaner  # noqa: F401
from ffun.cli.commands import metrics  # noqa: F401
from ffun.cli.commands import processors_quality  # noqa: F401
from ffun.cli.commands import user_settings  # noqa: F401
from ffun.core import logging
from ffun.domain.domain import new_user_id
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def _profile_get_last_entries() -> GetLastEntriesResponse:
    backup_time_str = "2024-11-13 22:58:46.876683"
    backup_time = datetime.datetime.fromisoformat(backup_time_str)

    user_id = new_user_id()  # Replace this with the real user id

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


async def run_profile() -> None:
    async with with_app():
        logger.info("experiment_started")

        # insert profiled call here

        logger.info("experiment_finished")


@cli_app.command()
def profile() -> None:
    asyncio.run(run_profile())
