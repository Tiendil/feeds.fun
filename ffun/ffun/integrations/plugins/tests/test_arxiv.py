import pytest

from ffun.domain.urls import str_to_absolute_url
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import arxiv
from ffun.integrations.plugins.arxiv import _build_pdf_reference, _remove_prefix_from_body
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.parsers.tests import make as p_make


@pytest.fixture  # type: ignore
def plugin() -> arxiv.Plugin:
    return arxiv.construct()


class TestDiscoverFeedUrls:
    @pytest.mark.asyncio
    async def test_returns_context_without_changes(self, plugin: arxiv.Plugin) -> None:
        context = fd_make.context("https://rss.arxiv.org/rss/cs.AI")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None


class TestBuildPdfReference:
    def test_builds_pdf_reference_from_abs_link(self) -> None:
        reference = _build_pdf_reference(str_to_absolute_url("https://arxiv.org/abs/2604.13180"))

        assert reference == Reference(
            semantics=ReferenceSemantics.page,
            url=str_to_absolute_url("https://arxiv.org/pdf/2604.13180"),
            title="PDF",
        )

    def test_returns_none_for_non_abs_link(self) -> None:
        assert _build_pdf_reference(str_to_absolute_url("https://example.com/abs/2604.13180")) is None


class TestRemovePrefixFromBody:
    def test_removes_arxiv_announce_prefix(self) -> None:
        body = "arXiv:2604.13180v1 Announce Type: new Abstract: Example abstract"

        assert _remove_prefix_from_body(body) == "Example abstract"

    def test_keeps_body_without_arxiv_announce_prefix(self) -> None:
        body = "Abstract: Example abstract"

        assert _remove_prefix_from_body(body) == body


class TestPostprocessEntry:
    def test_adds_pdf_reference_and_removes_prefix(self, plugin: arxiv.Plugin) -> None:
        author_reference = Reference(
            semantics=ReferenceSemantics.author,
            url=str_to_absolute_url("https://arxiv.org/search/?searchtype=author&query=Liu%2C+Q"),
            title="Qibin Liu",
        )
        entry = p_make.fake_entry_info(
            body="arXiv:2604.13180v1 Announce Type: new Abstract: Example abstract",
            external_url=str_to_absolute_url("https://arxiv.org/abs/2604.13180"),
            references=[author_reference],
        )

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry == entry.replace(
            body="Example abstract",
            references=[
                author_reference,
                Reference(
                    semantics=ReferenceSemantics.page,
                    url=str_to_absolute_url("https://arxiv.org/pdf/2604.13180"),
                    title="PDF",
                ),
            ],
        )

    def test_keeps_existing_reference_urls_unique(self, plugin: arxiv.Plugin) -> None:
        pdf_reference = Reference(
            semantics=ReferenceSemantics.page,
            url=str_to_absolute_url("https://arxiv.org/pdf/2604.13180"),
            title="Existing PDF",
        )
        entry = p_make.fake_entry_info(
            body="Abstract: Example abstract",
            external_url=str_to_absolute_url("https://arxiv.org/abs/2604.13180"),
            references=[pdf_reference],
        )

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry.references == [pdf_reference]
