import xml.etree.ElementTree as ET  # noqa
from typing import Generator

from ffun.domain.entities import UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, to_feed_url, url_to_uid
from ffun.parsers.entities import FeedInfo


def _extract_body(data: str) -> ET.Element:
    root = ET.fromstring(data)  # noqa

    if root.tag != "opml":
        raise NotImplementedError(f"Unknown root tag: {root.tag}")

    head, body = root

    if head.tag != "head":
        raise NotImplementedError(f"Unknown root tag: {head.tag}")

    if body.tag != "body":
        raise NotImplementedError(f"Unknown root tag: {body.tag}")

    return body


def extract_feeds(data: str) -> list[FeedInfo]:
    feeds: list[FeedInfo] = []

    body = _extract_body(data)

    repeated_feeds = extract_feeds_records(body)

    for new_feed in repeated_feeds:
        for saved_feed in feeds:
            if new_feed.url == saved_feed.url:
                break
        else:
            feeds.append(new_feed)

    return feeds


def extract_feeds_records(body: ET.Element) -> Generator[FeedInfo, None, None]:
    for outline in body:
        if outline.attrib.get("type") == "rss":
            url = normalize_classic_unknown_url(UnknownUrl(outline.attrib["xmlUrl"]))

            if url is None:
                continue

            feed_url = to_feed_url(url)

            yield FeedInfo(
                url=feed_url,
                title=outline.attrib.get("title", ""),
                description="",
                entries=[],
                uid=url_to_uid(feed_url),
            )
            continue

        yield from extract_feeds_records(outline)
