import datetime
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterable
from copy import deepcopy
from typing import ClassVar

from ffun.core.entities import BaseEntity
from ffun.domain.entities import AbsoluteUrl, ResourceUrl, UnknownUrl
from ffun.domain.urls import adjust_external_url, normalize_classic_unknown_url, to_resource_url
from ffun.extractors import builder, errors, html
from ffun.extractors.entities import (
    ContentPiece,
    DataPiece,
    EntryBodyPiece,
    EntryPublishedAtPiece,
    EntryTitlePiece,
    FeedDescriptionPiece,
    FeedSiteUrlPiece,
    FeedTitlePiece,
    HtmlPiece,
    UrlPiece,
)
from ffun.loader import domain as loader
from ffun.parsers.entities import FeedInfo

# Public builder types for custom extraction rules.
EntryBuilder = builder.EntryBuilder
FeedBuilder = builder.FeedBuilder


class ExtractionRule(BaseEntity, ABC):
    """Match a data piece by type and by the presence of every required tag."""

    input_type: ClassVar[type[DataPiece] | tuple[type[DataPiece], ...]] = DataPiece
    required_tags: frozenset[str] = frozenset()

    def matches(self, piece: DataPiece) -> bool:
        return isinstance(piece, self.input_type) and self.required_tags <= piece.tags

    @abstractmethod
    async def apply(self, piece: DataPiece, feed: FeedBuilder) -> Iterable[DataPiece]:
        """Process a matching piece and return any derived pieces for the queue.

        Derived pieces inherit the input's load budget unless the rule loads a URL.
        """


class _TransformRule(ExtractionRule):
    output_tags: frozenset[str]


class Extractor:
    """Process the queue up to a per-extraction piece limit."""

    __slots__ = ("rules", "max_pieces")

    def __init__(self, rules: Iterable[ExtractionRule], *, max_pieces: int = 10_000) -> None:
        if max_pieces < 1:
            raise errors.InvalidPieceLimit(limit=max_pieces)
        self.rules = tuple(rules)
        self.max_pieces = max_pieces

    async def extract(self, feed_url: ResourceUrl, initial_pieces: Iterable[DataPiece]) -> FeedInfo:
        feed = FeedBuilder(feed_url)
        pending = deque(initial_pieces)

        for _ in range(self.max_pieces):
            if not pending:
                break
            piece = pending.popleft()
            matching_rules = (rule for rule in self.rules if rule.matches(piece))
            for rule in matching_rules:
                pending.extend(await rule.apply(piece, feed))

        if pending:
            raise errors.PieceLimitExceeded(limit=self.max_pieces)

        return feed.build()


class LoadUrl(_TransformRule):
    input_type = UrlPiece

    async def apply(self, piece: DataPiece, feed: FeedBuilder) -> Iterable[DataPiece]:
        assert isinstance(piece, UrlPiece)

        if piece.remaining_loads == 0:
            return ()

        response = await loader.load_content_with_proxies(piece.url)
        response_url = UnknownUrl(str(response.url))
        url = normalize_classic_unknown_url(response_url)
        if url is None:
            raise errors.InvalidLoadedUrl(url=response_url)

        return (
            ContentPiece(
                tags=self.output_tags,
                remaining_loads=piece.remaining_loads - 1,
                url=url,
                content=response.content,
                encoding=response.charset_encoding,
            ),
        )


class ParseHtml(_TransformRule):
    input_type = ContentPiece

    async def apply(self, piece: DataPiece, feed: FeedBuilder) -> Iterable[DataPiece]:
        assert isinstance(piece, ContentPiece)

        element = html.parse_document(piece.content, piece.url, piece.encoding)
        base_href = html.first_text(element, "(//head/base[@href])[1]/@href")
        base_url = piece.url
        if base_href is not None:
            base_url = adjust_external_url(UnknownUrl(base_href), piece.url) or piece.url
        return (
            HtmlPiece(
                tags=self.output_tags,
                remaining_loads=piece.remaining_loads,
                url=piece.url,
                base_url=base_url,
                element=element,
            ),
        )


class _HtmlRule(_TransformRule):
    input_type = HtmlPiece
    xpath: str

    async def apply(self, piece: DataPiece, feed: FeedBuilder) -> Iterable[DataPiece]:
        assert isinstance(piece, HtmlPiece)
        return self.transform(piece)

    @abstractmethod
    def transform(self, piece: HtmlPiece) -> Iterable[DataPiece]:
        """Return the data pieces selected or constructed from the HTML context."""


class RemoveHtml(_HtmlRule):
    def transform(self, piece: HtmlPiece) -> Iterable[DataPiece]:
        cleaned_piece = piece.replace(tags=self.output_tags)
        element = cleaned_piece.element
        matches = list(html.select_elements(element, self.xpath))

        if any(match is element for match in matches):
            return ()

        for match in matches:
            match.drop_tree()

        return (cleaned_piece,)


class ExtractHtml(_HtmlRule):
    def transform(self, piece: HtmlPiece) -> Iterable[DataPiece]:
        for element in html.select_elements(piece.element, self.xpath):
            yield piece.replace(tags=self.output_tags, element=deepcopy(element))


class ExtractUrls(_HtmlRule):
    def transform(self, piece: HtmlPiece) -> Iterable[DataPiece]:  # noqa: CCR001
        seen: set[ResourceUrl] = set()
        for result in html.select(piece.element, self.xpath):
            if not isinstance(result, str) or not result.strip():
                continue
            url = adjust_external_url(UnknownUrl(result), piece.base_url)
            if url is None:
                continue

            resource_url = to_resource_url(url)
            if resource_url not in seen:
                seen.add(resource_url)
                yield UrlPiece(url=resource_url, tags=self.output_tags, remaining_loads=piece.remaining_loads)


class ExtractFeedTitle(_HtmlRule):
    def transform(self, piece: HtmlPiece) -> Iterable[DataPiece]:
        title = html.first_text(piece.element, self.xpath)
        if title is None:
            return ()
        return (FeedTitlePiece(title=title, tags=self.output_tags, remaining_loads=piece.remaining_loads),)


class ExtractFeedDescription(_HtmlRule):
    def transform(self, piece: HtmlPiece) -> Iterable[DataPiece]:
        description = html.first_text(piece.element, self.xpath)
        if description is None:
            return ()
        return (
            FeedDescriptionPiece(
                description=description, tags=self.output_tags, remaining_loads=piece.remaining_loads
            ),
        )


class ExtractFeedSiteUrl(_HtmlRule):
    def transform(self, piece: HtmlPiece) -> Iterable[DataPiece]:
        href = html.first_text(piece.element, self.xpath)
        if href is None:
            return ()

        site_url = adjust_external_url(UnknownUrl(href), piece.base_url)
        if site_url is None:
            return ()
        return (FeedSiteUrlPiece(site_url=site_url, tags=self.output_tags, remaining_loads=piece.remaining_loads),)


class _EntryFieldRule(_HtmlRule):
    """Resolve the entry URL before extracting its field."""

    url_xpath: str | None = None

    def transform(self, piece: HtmlPiece) -> Iterable[DataPiece]:
        url = self.entry_url(piece)
        if url is None:
            return ()

        field = self.extract_field(piece, url)
        return (field,) if field is not None else ()

    def entry_url(self, piece: HtmlPiece) -> AbsoluteUrl | None:
        if self.url_xpath is None:
            return piece.url

        href = html.first_text(piece.element, self.url_xpath)
        if href is None:
            return None

        return adjust_external_url(UnknownUrl(href), piece.base_url)

    @abstractmethod
    def extract_field(self, piece: HtmlPiece, url: AbsoluteUrl) -> DataPiece | None:
        """Return the selected field for the resolved entry URL when available."""


class ExtractEntryTitle(_EntryFieldRule):
    def extract_field(self, piece: HtmlPiece, url: AbsoluteUrl) -> EntryTitlePiece | None:
        title = html.first_text(piece.element, self.xpath)
        if title is None:
            return None
        return EntryTitlePiece(url=url, title=title, tags=self.output_tags, remaining_loads=piece.remaining_loads)


class ExtractEntryBody(_EntryFieldRule):
    def extract_field(self, piece: HtmlPiece, url: AbsoluteUrl) -> EntryBodyPiece | None:
        body = html.first_body(piece.element, self.xpath)
        if body is None:
            return None
        return EntryBodyPiece(url=url, body=body, tags=self.output_tags, remaining_loads=piece.remaining_loads)


class ExtractEntryPublishedAt(_EntryFieldRule):
    def extract_field(self, piece: HtmlPiece, url: AbsoluteUrl) -> EntryPublishedAtPiece | None:
        value = html.first_text(piece.element, self.xpath)
        if value is None:
            return None

        try:
            timestamp = datetime.datetime.fromisoformat(value)
        except ValueError:
            return None

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
        return EntryPublishedAtPiece(
            url=url, published_at=timestamp, tags=self.output_tags, remaining_loads=piece.remaining_loads
        )


class AddToFeed(ExtractionRule):
    input_type = (
        FeedTitlePiece,
        FeedDescriptionPiece,
        FeedSiteUrlPiece,
        EntryTitlePiece,
        EntryBodyPiece,
        EntryPublishedAtPiece,
    )

    async def apply(self, piece: DataPiece, feed: FeedBuilder) -> Iterable[DataPiece]:
        match piece:
            case FeedTitlePiece(title=title):
                feed.add_title(title)
            case FeedDescriptionPiece(description=description):
                feed.add_description(description)
            case FeedSiteUrlPiece(site_url=site_url):
                feed.add_site_url(site_url)
            case EntryTitlePiece():
                feed.get_or_create(piece.url).add_title(piece.title)
            case EntryBodyPiece():
                feed.get_or_create(piece.url).add_body(piece.body)
            case EntryPublishedAtPiece():
                feed.get_or_create(piece.url).add_published_at(piece.published_at)
            case _:
                raise AssertionError("AddToFeed received an unsupported data piece")
        return ()
