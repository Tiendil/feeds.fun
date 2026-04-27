import pytest
from pytest_mock import MockerFixture

from ffun.domain.urls import str_to_absolute_url, str_to_feed_url
from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import arxiv
from ffun.library.entities import Reference, ReferenceKind
from ffun.parsers.tests import make as p_make


@pytest.fixture  # type: ignore
def plugin() -> arxiv.Plugin:
    return arxiv.construct()


class TestDiscoverFeedUrls:
    @pytest.mark.asyncio
    async def test_returns_context_without_changes_for_non_arxiv_url(self, plugin: arxiv.Plugin) -> None:
        context = fd_make.context("https://example.com/paper")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_context_without_changes_for_single_feed_url(self, plugin: arxiv.Plugin) -> None:
        context = fd_make.context("https://rss.arxiv.org/rss/cs.AI")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_splits_union_feed_url(self, plugin: arxiv.Plugin) -> None:
        context = fd_make.context("https://rss.arxiv.org/rss/cs.AI+cs.LG")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                str_to_absolute_url("https://rss.arxiv.org/rss/cs.AI"),
                str_to_absolute_url("https://rss.arxiv.org/rss/cs.LG"),
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_loads_paper_page_and_constructs_feed_urls(
        self, mocker: MockerFixture, plugin: arxiv.Plugin
    ) -> None:
        context = fd_make.context("https://arxiv.org/abs/2501.00001")

        async def fake_load_decoded_content(url: object) -> str | None:
            assert url == "https://arxiv.org/abs/2501.00001"
            return """
                <h1>Title: Example paper</h1>
                <div>Subjects: Artificial Intelligence (cs.AI); Machine Learning (cs.LG)</div>
                <div>Cite as: arXiv:2501.00001 [cs.AI]</div>
            """

        mocker.patch.object(arxiv.lo_domain, "load_decoded_content", side_effect=fake_load_decoded_content)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                str_to_absolute_url("https://rss.arxiv.org/rss/cs.AI"),
                str_to_absolute_url("https://rss.arxiv.org/rss/cs.LG"),
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_loads_other_arxiv_page_and_constructs_feed_urls(
        self, mocker: MockerFixture, plugin: arxiv.Plugin
    ) -> None:
        context = fd_make.context("https://arxiv.org")

        async def fake_load_decoded_content(url: object) -> str | None:
            assert url == "https://arxiv.org"
            return """
                <ul>
                    <li><a href="/list/cs.AI/recent">Artificial Intelligence</a></li>
                    <li><a href="/list/cs.LG/recent">Machine Learning</a></li>
                    <li><a href="/archive/q-fin">Quantitative Finance</a></li>
                </ul>
            """

        mocker.patch.object(arxiv.lo_domain, "load_decoded_content", side_effect=fake_load_decoded_content)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                str_to_absolute_url("https://rss.arxiv.org/rss/cs.AI"),
                str_to_absolute_url("https://rss.arxiv.org/rss/cs.LG"),
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_ignores_aggregated_archive_categories(self, mocker: MockerFixture, plugin: arxiv.Plugin) -> None:
        context = fd_make.context("https://arxiv.org/abs/2604.21691")

        async def fake_load_decoded_content(url: object) -> str | None:
            assert url == "https://arxiv.org/abs/2604.21691"
            return """
                <div>Subjects: Machine Learning (cs.LG); Machine Learning (stat.ML)</div>
                <div>Cite as: arXiv:2604.21691 [stat]</div>
                <nav>
                    <a href="/archive/stat">Statistics</a>
                    <a href="/archive/cs">Computer Science</a>
                    <a href="/list/cs.LG/recent">Machine Learning</a>
                </nav>
            """

        mocker.patch.object(arxiv.lo_domain, "load_decoded_content", side_effect=fake_load_decoded_content)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                str_to_absolute_url("https://rss.arxiv.org/rss/cs.LG"),
                str_to_absolute_url("https://rss.arxiv.org/rss/stat.ML"),
            }
        )
        assert result is None


class TestBuildPdfReference:
    def test_builds_pdf_reference_from_abs_link(self) -> None:
        reference = arxiv._build_pdf_reference(str_to_absolute_url("https://arxiv.org/abs/2604.13180"))

        assert reference == Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://arxiv.org/pdf/2604.13180"),
            title="PDF",
        )

    def test_returns_none_for_non_abs_link(self) -> None:
        assert arxiv._build_pdf_reference(str_to_absolute_url("https://example.com/abs/2604.13180")) is None


class TestRemovePrefixFromBody:
    def test_removes_arxiv_announce_prefix(self) -> None:
        body = "arXiv:2604.13180v1 Announce Type: new Abstract: Example abstract"

        assert arxiv._remove_prefix_from_body(body) == "Example abstract"

    def test_keeps_body_without_arxiv_announce_prefix(self) -> None:
        body = "Abstract: Example abstract"

        assert arxiv._remove_prefix_from_body(body) == body


class TestAppendNewReferences:
    def test_adds_only_new_references(self) -> None:
        existing_reference = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://arxiv.org/pdf/2604.13180"),
            title="Existing PDF",
        )
        new_reference = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://arxiv.org/abs/2604.13180"),
            title="Paper",
        )
        entry = p_make.fake_entry_info(references=[existing_reference])

        references = arxiv._append_new_references(
            entry,
            [None, existing_reference, new_reference],
        )

        assert references == [existing_reference, new_reference]


class TestBuildFeedUrl:
    def test_builds_feed_url_for_section(self) -> None:
        assert arxiv._build_feed_url("cs.LG") == str_to_absolute_url("https://rss.arxiv.org/rss/cs.LG")


class TestBuildFeedUrls:
    def test_builds_feed_urls_for_sections(self) -> None:
        assert arxiv._build_feed_urls({"cs.AI", "cs.LG"}) == {
            str_to_absolute_url("https://rss.arxiv.org/rss/cs.AI"),
            str_to_absolute_url("https://rss.arxiv.org/rss/cs.LG"),
        }


class TestExtractSectionsFromFeedUrl:
    def test_extracts_sections_from_union_feed_url(self) -> None:
        assert arxiv._extract_sections_from_feed_url(str_to_feed_url("https://rss.arxiv.org/rss/cs.AI+cs.LG")) == {
            "cs.AI",
            "cs.LG",
        }

    def test_returns_empty_set_for_non_arxiv_feed_url(self) -> None:
        assert arxiv._extract_sections_from_feed_url(str_to_feed_url("https://example.com/rss/cs.AI")) == set()

    def test_returns_empty_set_for_unexpected_arxiv_feed_path(self) -> None:
        assert arxiv._extract_sections_from_feed_url(str_to_feed_url("https://rss.arxiv.org/list/cs.AI")) == set()


class TestExtractSectionsFromPageContent:
    def test_extracts_specific_sections_from_text_lines_and_links(self) -> None:
        content = """
            <div>Subjects: Artificial Intelligence (cs.AI); Machine Learning (cs.LG)</div>
            <div>Cite as: arXiv:2501.00001 [stat.ML]</div>
            <a href="/list/math.OC/recent">Optimization and Control</a>
            <pre>q-fin.PM</pre>
        """

        assert arxiv._extract_sections_from_page_content(content) == {
            "cs.AI",
            "cs.LG",
            "math.OC",
            "q-fin.PM",
            "stat.ML",
        }

    def test_ignores_aggregated_archive_sections(self) -> None:
        content = """
            <div>Cite as: arXiv:2604.21691 [stat]</div>
            <a href="/archive/stat">Statistics</a>
            <a href="/archive/cs">Computer Science</a>
            <a href="/list/cs.LG/recent">Machine Learning</a>
        """

        assert arxiv._extract_sections_from_page_content(content) == {"cs.LG"}


class TestAddFeedUrlsToContext:
    def test_adds_feed_urls_to_existing_candidates(self) -> None:
        context = fd_make.context(
            "https://arxiv.org/abs/2604.21691",
            candidate_urls={str_to_absolute_url("https://example.com/feed")},
        )

        new_context = arxiv._add_feed_urls_to_context(context, {"cs.LG", "stat.ML"})

        assert new_context == context.replace(
            candidate_urls={
                str_to_absolute_url("https://example.com/feed"),
                str_to_absolute_url("https://rss.arxiv.org/rss/cs.LG"),
                str_to_absolute_url("https://rss.arxiv.org/rss/stat.ML"),
            }
        )


class TestPostprocessEntry:
    def test_adds_pdf_reference_and_removes_prefix(self, plugin: arxiv.Plugin) -> None:
        author_reference = Reference(
            kind=ReferenceKind.author,
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
                    kind=ReferenceKind.page,
                    url=str_to_absolute_url("https://arxiv.org/pdf/2604.13180"),
                    title="PDF",
                ),
            ],
        )

    def test_keeps_existing_reference_urls_unique(self, plugin: arxiv.Plugin) -> None:
        pdf_reference = Reference(
            kind=ReferenceKind.page,
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


class TestConstruct:
    def test_returns_plugin(self) -> None:
        assert isinstance(arxiv.construct(), arxiv.Plugin)
