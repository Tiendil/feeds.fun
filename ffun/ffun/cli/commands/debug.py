import sys
import asyncio
import uuid

import typer
from rich.pretty import pprint

from ffun.application.application import with_app
from ffun.domain.entities import FeedId
from ffun.domain.urls import str_to_feed_url
from ffun.loader import domain as l_domain
from ffun.parsers.feed import parse_into_feedparser

cli_app = typer.Typer()


async def run_load_feed_internal(feed_url: str) -> None:
    async with with_app():
        try:
            response = await l_domain.load_content_with_proxies(feed_url)
            content = await l_domain.decode_content(response)
            feed_info = await l_domain.parse_content(content, original_url=feed_url)
        except Exception as e:
            sys.stdout.write(f"Failed to load feed info: {e}\n")
            return

    if feed_info is None:
        sys.stdout.write("Failed to load feed info: No feed info found\n")

    sys.stdout.write("Feed info loaded successfully:\n\n")

    pprint(feed_info)


@cli_app.command()  # type: ignore
def load_feed_internal(feed_url: str) -> None:
    asyncio.run(run_load_feed_internal(feed_url))


async def run_load_feed_feedparser(feed_url: str) -> None:
    async with with_app():
        try:
            response = await l_domain.load_content_with_proxies(feed_url)
            content = await l_domain.operations.decode_content(response)
            channel = parse_into_feedparser(content)
        except Exception as e:
            sys.stdout.write(f"Failed to load feed info: {e}\n")
            return

    if channel is None:
        sys.stdout.write("Failed to load feed info: No feed info found\n")

    sys.stdout.write("Feed info loaded successfully:\n\n")

    pprint(channel)


@cli_app.command()  # type: ignore
def load_feed_feedparser(feed_url: str) -> None:
    asyncio.run(run_load_feed_feedparser(feed_url))


async def run_load_feed_raw(feed_url: str) -> None:
    async with with_app():
        try:
            response = await l_domain.load_content_with_proxies(feed_url)
            content = await l_domain.operations.decode_content(response)
        except Exception as e:
            sys.stdout.write(f"Failed to load feed info: {e}\n")
            return

    sys.stdout.write("Feed info loaded successfully:\n\n")

    sys.stdout.write(content)
    sys.stdout.write("\n")


@cli_app.command()  # type: ignore
def load_feed_raw(feed_url: str) -> None:
    asyncio.run(run_load_feed_raw(feed_url))
