"""
Development utilities for feeds.

This code is intended to be used by developers to simplify our work, therefore:

- It MUST NOT be used in production code.
- It MUST NOT be used in tests.
- no tests are required for this code.
"""

import asyncio
import uuid

import typer

from ffun.application.application import with_app
from ffun.auth.settings import settings as a_settings
from ffun.core import logging, utils
from ffun.domain.domain import new_entry_id, new_feed_id
from ffun.domain.entities import UnknownUrl, UserId
from ffun.domain.urls import adjust_classic_relative_url, str_to_feed_url, url_to_source_uid
from ffun.feeds.domain import get_feeds, get_source_ids, save_feed
from ffun.feeds.entities import Feed, FeedState
from ffun.feeds_links.domain import add_link
from ffun.library.domain import catalog_entries, get_entries_by_ids
from ffun.library.entities import Entry
from ffun.ontology.domain import apply_tags_to_entry
from ffun.ontology.entities import ProcessorTag
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def fake_feed() -> Feed:

    _id = uuid.uuid4().hex

    url = str_to_feed_url(f"https://{_id}.com")

    source_uid = url_to_source_uid(url)

    source_ids = await get_source_ids([source_uid])

    timestamp = utils.now()

    feed = Feed(
        id=new_feed_id(),
        source_id=source_ids[source_uid],
        url=url,
        state=FeedState.loaded,
        last_error=None,
        load_attempted_at=timestamp,
        loaded_at=timestamp,
        title=f"Title {_id}",
        description=f"Description {_id}",
    )

    feed_id = await save_feed(feed)

    feeds = await get_feeds([feed_id])

    return feeds[0]


async def fake_entry(feed: Feed) -> Entry:
    _id = uuid.uuid4().hex

    timestamp = utils.now()

    url = adjust_classic_relative_url(UnknownUrl(f"enrty-{_id}"), feed.url)

    assert url is not None

    entry = Entry(
        id=new_entry_id(),
        source_id=feed.source_id,
        title=f"Title {_id}",
        body=f"Body {_id}",
        external_id=uuid.uuid4().hex,
        external_url=url,
        external_tags=set(),
        published_at=timestamp,
        cataloged_at=timestamp,
    )

    await catalog_entries(feed.id, [entry])

    entries = await get_entries_by_ids([entry.id])

    assert entry is not None

    returned_entry = entries[entry.id]

    assert returned_entry is not None

    return returned_entry


async def run_fill_db(feeds_number: int, entries_per_feed: int, tags_per_entry: int) -> None:
    async with with_app():
        external_user_id = a_settings.single_user.external_id

        internal_user_id = await u_domain.get_or_create_user_id(u_entities.Service.single, external_user_id)

        for _ in range(feeds_number):
            feed = await fake_feed()

            await add_link(internal_user_id, feed.id)

            entries = [await fake_entry(feed) for _ in range(entries_per_feed)]

            for i, entry in enumerate(entries, start=1):

                tags = []

                for j, _ in enumerate(range(tags_per_entry), start=1):
                    raw_uid = f"some-long-tag-name-{j}-{i % j}"
                    tags.append(ProcessorTag(raw_uid=raw_uid))

                await apply_tags_to_entry(entry.id, 100500, tags)


@cli_app.command()
def fill_db(feeds_number: int = 10, entries_per_feed: int = 100, tags_per_entry: int = 25) -> None:
    asyncio.run(run_fill_db(feeds_number, entries_per_feed, tags_per_entry))


async def run_supertokens_user_to_dev(intenal_user_id: UserId) -> None:
    async with with_app():
        external_user_id = a_settings.single_user.external_id

        to_user_id = await u_domain.get_or_create_user_id(u_entities.Service.single, external_user_id)

        await u_domain.tech_move_user(from_user_id=intenal_user_id, to_user_id=to_user_id)


@cli_app.command()
def supertokens_user_to_dev(intenal_user_id: str) -> None:
    asyncio.run(run_supertokens_user_to_dev(UserId(uuid.UUID(intenal_user_id))))
