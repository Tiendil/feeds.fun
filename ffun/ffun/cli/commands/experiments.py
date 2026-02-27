import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.domain.entities import AbsoluteUrl, UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, url_to_source_uid, url_to_uid
from ffun.library.operations import all_entries_iterator, count_total_entries

logger = logging.get_module_logger()

cli_app = typer.Typer()


def _source_row(source_row: dict[str, object]) -> tuple[int, str]:
    source_id = source_row["id"]
    source_uid = source_row["uid"]

    assert isinstance(source_id, int)
    assert isinstance(source_uid, str)

    return source_id, source_uid


def _feed_row(feed_row: dict[str, object]) -> tuple[AbsoluteUrl, str, int]:
    url = feed_row["url"]
    uid = feed_row["uid"]
    source_id = feed_row["source_id"]

    assert isinstance(url, str)
    assert isinstance(uid, str)
    assert isinstance(source_id, int)

    absolute_url = normalize_classic_unknown_url(UnknownUrl(url))

    assert absolute_url is not None, f"URL {url} cannot be normalized"

    return absolute_url, uid, source_id


def _log_processed(counter: int, total: int, wrong_urls: int, wrong_sources: int) -> None:
    if counter % 100 != 0:
        return

    logger.info(
        "processed_entries",
        counter=counter,
        percentage=round((counter / total) * 100, 2),
        wrong_urls=wrong_urls,
        wrong_sources=wrong_sources,
    )


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

        sources: list[dict[str, object]] = await execute("SELECT id, uid FROM f_sources")

        source_ids: dict[int, str] = {}

        for source_row in sources:
            source_id, source_uid = _source_row(source_row)
            source_ids[source_id] = source_uid

        counter = 0
        wrong_urls = 0
        wrong_sources = 0

        feeds: list[dict[str, object]] = await execute("SELECT url, source_id, uid FROM f_feeds")

        total = len(feeds)

        for feed_row in feeds:
            counter += 1

            url, uid, source_id = _feed_row(feed_row)

            expected_uid = url_to_uid(url)
            expected_source_uid = url_to_source_uid(url)

            if uid != expected_uid:
                wrong_urls += 1

            if source_ids[source_id] != expected_source_uid:
                wrong_sources += 1

            _log_processed(counter, total, wrong_urls, wrong_sources)

        logger.info("experiment_finished", wrong_urls=wrong_urls, wrong_sources=wrong_sources)


async def run_experiment() -> None:
    pass


@cli_app.command()  # type: ignore
def experiment() -> None:
    asyncio.run(run_experiment())
