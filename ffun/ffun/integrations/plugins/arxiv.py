import re

from bs4 import BeautifulSoup

from ffun.domain.entities import AbsoluteUrl, FeedUrl, UnknownUrl
from ffun.domain.urls import construct_f_url, normalize_classic_unknown_url
from ffun.feeds_discoverer import entities as fd_entities
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.loader import domain as lo_domain
from ffun.parsers import entities as p_entities

_BODY_PREFIX_RE = re.compile(r"^arXiv:[^\s]+\s+Announce Type:\s+[^\s]+\s+Abstract:\s*")
_SECTION_FROM_DELIMITED_TEXT_RE = re.compile(r"(?<=[\(\[])(?P<section>[a-z-]+\.[A-Z]{2})(?=[\s\)\]])")
_SECTION_FROM_LINE_RE = re.compile(r"^(?P<section>[a-z-]+\.[A-Z]{2})$")
_SECTION_FROM_LINK_RE = re.compile(r"/(?:list|archive)/(?P<section>[a-z-]+\.[A-Z]{2})")
_ARXIV_PAGE_HOSTS = {"arxiv.org", "www.arxiv.org"}
_ARXIV_RSS_HOST = "rss.arxiv.org"
_ARXIV_RSS_PATH_PREFIX = "rss"
_ARXIV_FEED_URL_TEMPLATE = "https://rss.arxiv.org/rss/{section}"


def _build_pdf_reference(entry_link: AbsoluteUrl) -> Reference | None:
    f_url = construct_f_url(entry_link)

    path_segments = [segment for segment in f_url.path.segments if segment] if f_url is not None else []

    if f_url is None or f_url.host != "arxiv.org" or len(path_segments) < 2 or path_segments[0] != "abs":
        return None

    f_url.path.segments[0] = "pdf"
    f_url.query = ""  # type: ignore
    f_url.fragment = None

    pdf_url = normalize_classic_unknown_url(UnknownUrl(str(f_url)))

    if pdf_url is None:
        return None

    return Reference(
        semantics=ReferenceSemantics.page,
        url=pdf_url,
        title="PDF",
    )


def _remove_prefix_from_body(body: str) -> str:
    return _BODY_PREFIX_RE.sub("", body, count=1)


def _append_new_references(entry: p_entities.EntryInfo, references: list[Reference | None]) -> list[Reference]:
    existing_urls = {reference.url for reference in entry.references}
    new_references: list[Reference] = []

    for reference in references:
        if reference is None:
            continue

        if reference.url in existing_urls:
            continue

        existing_urls.add(reference.url)
        new_references.append(reference)

    return [*entry.references, *new_references]


def _build_feed_url(section: str) -> AbsoluteUrl | None:
    return normalize_classic_unknown_url(UnknownUrl(_ARXIV_FEED_URL_TEMPLATE.format(section=section)))


def _build_feed_urls(sections: set[str]) -> set[AbsoluteUrl]:
    feed_urls: set[AbsoluteUrl] = set()

    for section in sections:
        feed_url = _build_feed_url(section)

        if feed_url is not None:
            feed_urls.add(feed_url)

    return feed_urls


def _extract_sections_from_feed_url(url: FeedUrl) -> set[str]:
    f_url = construct_f_url(url)

    if f_url is None or f_url.host != _ARXIV_RSS_HOST:
        return set()

    path_segments = [segment for segment in f_url.path.segments if segment]

    if len(path_segments) != 2 or path_segments[0] != _ARXIV_RSS_PATH_PREFIX:
        return set()

    return {section for section in path_segments[1].split("+") if section != ""}


def _extract_sections_from_page_content(content: str) -> set[str]:
    soup = BeautifulSoup(content, "html.parser")
    page_text = soup.get_text("\n")

    sections = {match.group("section") for match in _SECTION_FROM_DELIMITED_TEXT_RE.finditer(page_text)}
    sections.update(match.group("section") for match in _SECTION_FROM_LINK_RE.finditer(content))

    for line in page_text.splitlines():
        line = line.strip()

        if match := _SECTION_FROM_LINE_RE.fullmatch(line):
            sections.add(match.group("section"))

    return sections


def _add_feed_urls_to_context(context: fd_entities.Context, sections: set[str]) -> fd_entities.Context:
    return context.replace(candidate_urls=context.candidate_urls | _build_feed_urls(sections))


class Plugin(BasePlugin):
    __slots__ = ()
    source_name = "ArXiv"

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
        assert context.url is not None

        f_url = construct_f_url(context.url)

        assert f_url is not None

        if f_url.host == _ARXIV_RSS_HOST:
            sections = _extract_sections_from_feed_url(context.url)

            if len(sections) <= 1:
                return context, None

            return _add_feed_urls_to_context(context, sections), None

        if f_url.host not in _ARXIV_PAGE_HOSTS:
            return context, None

        content = await lo_domain.load_decoded_content(context.url)

        if content is None:
            return context, None

        sections = _extract_sections_from_page_content(content)

        if not sections:
            return context, None

        return _add_feed_urls_to_context(context, sections), None

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return entry.replace(
            body=_remove_prefix_from_body(entry.body),
            references=_append_new_references(
                entry,
                [_build_pdf_reference(entry.external_url)],
            ),
        )


def construct() -> Plugin:
    return Plugin()
