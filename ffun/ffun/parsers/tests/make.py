import datetime
import uuid

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


def fake_entry_info(
    *,
    title: str | None = None,
    body: str | None = None,
    external_id: str | None = None,
    external_url: AbsoluteUrl | None = None,
    external_tags: set[str] | None = None,
    published_at: datetime.datetime | None = None,
) -> EntryInfo:
    return EntryInfo(
        title=fake_title() if title is None else title,
        body=fake_body() if body is None else body,
        external_id=uuid.uuid4().hex if external_id is None else external_id,
        external_url=fake_url() if external_url is None else external_url,
        external_tags={uuid.uuid4().hex, uuid.uuid4().hex} if external_tags is None else external_tags,
        published_at=utils.now() if published_at is None else published_at,
    )
