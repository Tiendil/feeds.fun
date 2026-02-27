import datetime
import uuid

from ffun.core.entities import BaseEntity
from ffun.domain.entities import FeedId
from ffun.domain.urls import str_to_absolute_url, str_to_feed_url, url_to_source_uid
from ffun.feeds.entities import Feed, FeedError, FeedState
from ffun.feeds.operations import get_feeds, get_source_ids, save_feed


def fake_url() -> str:
    return f"https://{uuid.uuid4().hex}.com"


def fake_title() -> str:
    return f"Feed Title: {uuid.uuid4().hex}"


def fake_description() -> str:
    return f"Feed Description: {uuid.uuid4().hex}"


class FeedLoading(BaseEntity):
    last_error: FeedError | None = None
    load_attempted_at: datetime.datetime | None = None
    loaded_at: datetime.datetime | None = None


async def fake_feed(
    *,
    id: uuid.UUID | None = None,
    url: str | None = None,
    state: FeedState = FeedState.not_loaded,
    loading: FeedLoading | None = None,
    title: str | None = None,
    description: str | None = None,
) -> Feed:
    if loading is None:
        loading = FeedLoading()

    feed_url = fake_url() if url is None else url

    source_uid = url_to_source_uid(str_to_absolute_url(feed_url))

    source_ids = await get_source_ids([source_uid])

    return Feed(
        id=FeedId(uuid.uuid4() if id is None else id),
        source_id=source_ids[source_uid],
        url=str_to_feed_url(feed_url),
        state=state,
        last_error=loading.last_error,
        load_attempted_at=loading.load_attempted_at,
        loaded_at=loading.loaded_at,
        title=fake_title() if title is None else title,
        description=fake_description() if description is None else description,
    )


async def n_feeds(n: int) -> list[Feed]:
    feed_objects = [await fake_feed() for _ in range(n)]

    saved_ids = [await save_feed(feed) for feed in feed_objects]

    feeds = await get_feeds(saved_ids)

    return feeds
