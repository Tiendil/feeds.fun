import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import AbsoluteUrl
from ffun.extractors.html import HtmlElement


class DataPiece(BaseEntity):
    """Data routed by extraction tags with a budget for subsequent URL loads."""

    tags: frozenset[str] = frozenset()
    remaining_loads: pydantic.NonNegativeInt = 0


class UrlPiece(DataPiece):
    url: AbsoluteUrl


class ContentPiece(DataPiece):
    # In Markdown, "    print('hi')\n" is an indented code block.
    # Stripping the leading spaces turns it into a paragraph.
    model_config = pydantic.ConfigDict(str_strip_whitespace=False)

    url: AbsoluteUrl
    content: bytes | str
    encoding: str | None = None


class HtmlPiece(DataPiece):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    url: AbsoluteUrl
    base_url: AbsoluteUrl
    element: HtmlElement


class FeedTitlePiece(DataPiece):
    title: str


class FeedDescriptionPiece(DataPiece):
    description: str


class FeedSiteUrlPiece(DataPiece):
    site_url: AbsoluteUrl


class _EntryFieldPiece(DataPiece):
    url: AbsoluteUrl


class EntryTitlePiece(_EntryFieldPiece):
    title: str


class EntryBodyPiece(_EntryFieldPiece):
    body: str


class EntryPublishedAtPiece(_EntryFieldPiece):
    published_at: pydantic.AwareDatetime
