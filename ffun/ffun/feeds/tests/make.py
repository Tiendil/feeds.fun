import uuid
from typing import Any

from ffun.feeds.entities import Feed, FeedState
from ffun.feeds.operations import get_feeds, save_feed


def fake_url() -> str:
    return f"https://{uuid.uuid4().hex}.com"


def fake_title() -> str:
    return f"Feed Title: {uuid.uuid4().hex}"


def fake_description() -> str:
    return f"Feed Description: {uuid.uuid4().hex}"


def fake_feed(**kwargs: Any) -> Feed:
    return Feed(
        id=uuid.uuid4() if "id" not in kwargs else kwargs["id"],
        url=fake_url() if "url" not in kwargs else kwargs["url"],
        state=FeedState.not_loaded if "state" not in kwargs else kwargs["state"],
        last_error=kwargs.get("last_error"),
        load_attempted_at=kwargs.get("load_attempted_at"),
        loaded_at=kwargs.get("loaded_at"),
        title=fake_title() if "title" not in kwargs else kwargs["title"],
        description=fake_description() if "description" not in kwargs else kwargs["description"],
    )


async def n_feeds(n: int) -> list[Feed]:
    feed_objects = [fake_feed() for _ in range(n)]

    saved_ids = [await save_feed(feed) for feed in feed_objects]

    feeds = await get_feeds(saved_ids)

    return feeds
