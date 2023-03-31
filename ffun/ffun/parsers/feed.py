import datetime
import logging
import uuid
from typing import Any, Iterable

import feedparser
from ffun.library.entities import Entry


def _parse_tags(tags: Iterable[dict[str, Any]]) -> set[str]:
    result = set()

    for tag in tags:
        if tag.get('label') is not None:
            result.add(tag['label'])

        elif tag.get('term') is not None:
            result.add(tag['term'])

    return result


def _should_skip(entry: Any) -> bool:
    if entry.get('id') is None:
        logging.warning('Feed does not has "id" field')
        return True

    if entry.get('link') is None:
        logging.warning('Feed does not has "link" field')
        return True

    return False


def _extract_published_at(entry: Any) -> datetime.datetime:
    published_at = entry.get('published_parsed')

    if published_at is not None:
        return datetime.datetime(*published_at[:6])

    return datetime.datetime.now()


def parse_feed(feed_id: uuid.UUID, content: str) -> list[Entry]:

    channel = feedparser.parse(content)

    entries: list[Entry] = []

    for entry in channel.entries:
        # TODO: remove all tags from title
        # TODO: extract tags from <category> tag

        if _should_skip(entry):
            continue

        url = entry.get('link')

        now = datetime.datetime.now()

        published_at = _extract_published_at(entry)

        entries.append(Entry(id=uuid.uuid4(),
                             feed_id=feed_id,
                             title=entry.get('title', ''),
                             body=entry.get('description', ''),
                             external_id=url,  # TODO: normalize url
                             external_url=url,
                             external_tags=_parse_tags(entry.get('tags', ())),
                             published_at=published_at,
                             cataloged_at=now))

    return entries
