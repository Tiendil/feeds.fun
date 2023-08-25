import uuid
from typing import Any

from ffun.feeds.entities import Feed, FeedState


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
