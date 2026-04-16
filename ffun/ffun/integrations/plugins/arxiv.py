import re

from ffun.domain.entities import AbsoluteUrl, UnknownUrl
from ffun.domain.urls import construct_f_url, normalize_classic_unknown_url
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.parsers import entities as p_entities

_BODY_PREFIX_RE = re.compile(r"^arXiv:[^\s]+\s+Announce Type:\s+[^\s]+\s+Abstract:\s*")


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


class Plugin(BasePlugin):
    __slots__ = ()

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
