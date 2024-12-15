import uuid
from typing import Any

from ffun.core import utils
from ffun.domain.entities import AbsoluteUrl, UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url
from ffun.parsers.entities import EntryInfo


def fake_url() -> AbsoluteUrl:
    url = normalize_classic_unknown_url(UnknownUrl(f"https://{uuid.uuid4().hex}.com"))
    assert url is not None
    return url


def fake_title() -> str:
    return f"Entry Title: {uuid.uuid4().hex}"


def fake_body() -> str:
    return f"Entry Body: {uuid.uuid4().hex}"


def fake_entry_info(**kwargs: Any) -> EntryInfo:
    return EntryInfo(
        title=fake_title() if "title" not in kwargs else kwargs["title"],
        body=fake_body() if "body" not in kwargs else kwargs["body"],
        external_id=uuid.uuid4().hex if "external_id" not in kwargs else kwargs["external_id"],
        external_url=fake_url() if "external_url" not in kwargs else kwargs["external_url"],
        external_tags=(
            {uuid.uuid4().hex, uuid.uuid4().hex} if "external_tags" not in kwargs else kwargs["external_tags"]
        ),
        published_at=utils.now() if "published_at" not in kwargs else kwargs["published_at"],
    )
