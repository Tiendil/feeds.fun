from ffun.domain.urls import construct_f_url
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.parsers import entities as p_entities


DEFAULT_ORIGINAL_HOSTS = ("news.ycombinator.com",)


def _swap_link_and_comments(
    entry: p_entities.EntryInfo, original_hosts: tuple[str, ...] = DEFAULT_ORIGINAL_HOSTS
) -> p_entities.EntryInfo:
    comments_reference = None

    for reference in entry.references:
        if reference.semantics == ReferenceSemantics.comments:
            comments_reference = reference
            break

    if comments_reference is None:
        return entry

    original_url = entry.external_url
    original_f_url = construct_f_url(original_url)

    if original_f_url is None or original_f_url.host in original_hosts:
        return entry

    page_reference = Reference(
        semantics=ReferenceSemantics.page,
        url=original_url,
        title="Original article",
    )

    return entry.replace(
        external_url=comments_reference.url,
        references=[*entry.references, page_reference],
    )


class Plugin(BasePlugin):
    __slots__ = ("_original_hosts",)

    def __init__(self, original_hosts: list[str]):
        self._original_hosts = tuple(original_hosts)

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return _swap_link_and_comments(entry, self._original_hosts)


def construct(**kwargs: object) -> Plugin:
    original_hosts = kwargs.get("original_hosts", list(DEFAULT_ORIGINAL_HOSTS))
    assert isinstance(original_hosts, list)
    assert all(isinstance(host, str) for host in original_hosts)

    return Plugin(original_hosts=original_hosts)
