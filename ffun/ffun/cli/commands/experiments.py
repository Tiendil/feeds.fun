import asyncio
import enum

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.core.errors import Error
from ffun.core.postgresql import execute
from ffun.domain.entities import AbsoluteUrl, UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, to_resource_url, url_to_source_uid, url_to_uid
from ffun.extractors.domain import (
    AddToFeed,
    ExtractEntryBody,
    ExtractEntryPublishedAt,
    ExtractEntryTitle,
    ExtractFeedDescription,
    ExtractFeedSiteUrl,
    ExtractFeedTitle,
    ExtractHtml,
    Extractor,
    ExtractUrls,
    LoadUrl,
    ParseHtml,
    RemoveHtml,
)
from ffun.extractors.entities import UrlPiece
from ffun.library.operations import all_entries_iterator, count_total_entries
from ffun.parsers.entities import FeedInfo

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


class _TiendilStage(enum.StrEnum):
    index_page = "index"
    listing = "listing"
    article = "article"
    clean_article = "clean_article"
    feed = "feed"


async def run_extract_tiendil() -> FeedInfo:
    url = AbsoluteUrl("https://tiendil.org/en")
    index = frozenset({_TiendilStage.index_page})
    listing = frozenset({_TiendilStage.listing})
    article = frozenset({_TiendilStage.article})
    clean_article = frozenset({_TiendilStage.clean_article})
    feed = frozenset({_TiendilStage.feed})
    article_xpath = "//article[@class='brigid-article']"
    canonical_url_xpath = "/html/head/link[@rel='canonical']/@href"

    extractor = Extractor(
        rules=[
            LoadUrl(required_tags=index, output_tags=index),
            ParseHtml(required_tags=index, output_tags=index),
            ExtractFeedTitle(required_tags=index, output_tags=feed, xpath="/html/head/title"),
            ExtractFeedDescription(
                required_tags=index,
                output_tags=feed,
                xpath="/html/head/meta[@name='description']/@content",
            ),
            ExtractFeedSiteUrl(required_tags=index, output_tags=feed, xpath=canonical_url_xpath),
            ExtractHtml(required_tags=index, output_tags=listing, xpath="//div[@class='brigid-index-posts']"),
            ExtractUrls(
                required_tags=listing,
                output_tags=article,
                xpath="./div[@class='brigid-article']/h1/a/@href",
            ),
            LoadUrl(required_tags=article, output_tags=article),
            ParseHtml(required_tags=article, output_tags=article),
            ExtractEntryTitle(
                required_tags=article,
                output_tags=feed,
                xpath="//meta[@property='og:title']/@content",
                url_xpath=canonical_url_xpath,
            ),
            ExtractEntryPublishedAt(
                required_tags=article,
                output_tags=feed,
                xpath="//meta[@property='article:published_time']/@content",
                url_xpath=canonical_url_xpath,
            ),
            RemoveHtml(
                required_tags=article,
                output_tags=clean_article,
                xpath=f"{article_xpath}/h1 | {article_xpath}/div[@class='brigid-article-footer']",
            ),
            ExtractEntryBody(
                required_tags=clean_article,
                output_tags=feed,
                xpath=article_xpath,
                url_xpath=canonical_url_xpath,
            ),
            AddToFeed(required_tags=feed),
        ]
    )

    async with with_app():
        return await extractor.extract(to_resource_url(url), [UrlPiece(url=url, tags=index, remaining_loads=2)])


@cli_app.command()  # type: ignore
def extract_tiendil() -> None:
    """Extract the latest English posts from tiendil.org and print them as JSON."""
    try:
        result = asyncio.run(run_extract_tiendil())
    except Error as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    typer.echo(result.model_dump_json(indent=2))
