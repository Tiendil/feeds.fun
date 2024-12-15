import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.domain.entities import UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, url_to_source_uid, url_to_uid
from ffun.library.operations import all_entries_iterator, count_total_entries

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_check_entries() -> None:
    async with with_app():

        logger.info("start_experiment")

        counter = 0

        chunk = 10000

        total = await count_total_entries()

        wrong_urls = 0

        async for entry in all_entries_iterator(chunk=chunk):
            counter += 1

            if counter % chunk == 0:
                logger.info(
                    "processed_entries",
                    counter=counter,
                    percentage=round((counter / total) * 100, 2),
                    wrong_urls=wrong_urls,
                )

            if "#" in entry.external_url or "magnet" in entry.external_url:
                continue

            if normalize_classic_unknown_url(UnknownUrl(entry.external_url)) != entry.external_url:
                wrong_urls += 1

        logger.info("experiment_finished", wrong_urls=wrong_urls)


async def run_check_feeds() -> None:
    async with with_app():

        logger.info("start_experiment")

        sources = await execute("SELECT id, uid FROM f_sources")

        source_ids = {row["id"]: row["uid"] for row in sources}

        counter = 0
        wrong_urls = 0
        wrong_sources = 0

        feeds = await execute("SELECT url, source_id, uid FROM f_feeds")

        total = len(feeds)

        for row in feeds:
            counter += 1

            url = row["url"]
            uid = row["uid"]

            expected_uid = url_to_uid(url)
            expected_source_uid = url_to_source_uid(url)

            if uid != expected_uid:
                wrong_urls += 1

            if source_ids[row["source_id"]] != expected_source_uid:
                wrong_sources += 1

            if counter % 100 == 0:
                logger.info(
                    "processed_entries",
                    counter=counter,
                    percentage=round((counter / total) * 100, 2),
                    wrong_urls=wrong_urls,
                    wrong_sources=wrong_sources,
                )

        logger.info("experiment_finished", wrong_urls=wrong_urls, wrong_sources=wrong_sources)


async def run_experiment() -> None:
    pass


@cli_app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
