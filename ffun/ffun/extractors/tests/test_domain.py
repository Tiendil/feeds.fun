import datetime
from typing import cast

import httpx
import pytest
from pytest_mock import MockerFixture
from respx.models import Call
from respx.router import MockRouter

from ffun.core.utils import now
from ffun.domain.entities import AbsoluteUrl
from ffun.domain.urls import str_to_resource_url, to_resource_url
from ffun.extractors import html
from ffun.extractors.domain import (
    AddToFeed,
    ExtractEntryBody,
    ExtractEntryPublishedAt,
    ExtractEntryTitle,
    ExtractFeedDescription,
    ExtractFeedSiteUrl,
    ExtractFeedTitle,
    ExtractHtml,
    ExtractionRule,
    Extractor,
    ExtractUrls,
    FeedBuilder,
    LoadUrl,
    ParseHtml,
    RemoveHtml,
    _EntryFieldRule,
    _HtmlRule,
)
from ffun.extractors.entities import (
    ContentPiece,
    EntryBodyPiece,
    EntryPublishedAtPiece,
    EntryTitlePiece,
    FeedDescriptionPiece,
    FeedSiteUrlPiece,
    FeedTitlePiece,
    HtmlPiece,
    UrlPiece,
)
from ffun.extractors.errors import InvalidLoadedUrl, InvalidPieceLimit, PieceLimitExceeded


@pytest.fixture()
def feed_builder() -> FeedBuilder:
    return FeedBuilder(str_to_resource_url("https://news.example/digest/index.html"))


@pytest.fixture()
def article_piece() -> HtmlPiece:
    url = AbsoluteUrl("https://news.example/digest/index.html")
    markup = (
        '<link rel="canonical" href="first">'
        "<main><article><h1>First article</h1><p>Before <span>menu</span> after</p>"
        '<time datetime="2024-02-29"></time></article><article><h1>Second article</h1></article></main>'
    )
    return HtmlPiece(
        url=url,
        base_url=AbsoluteUrl("https://news.example/stories/"),
        tags=frozenset({"article"}),
        remaining_loads=2,
        element=html.parse_document(markup, url, encoding=None),
    )


class TestExtractionRule:
    @pytest.fixture()
    def rule(self) -> ExtractionRule:
        required_tags = frozenset({"page", "selected"})
        return LoadUrl(required_tags=required_tags, output_tags=frozenset())

    def test_matches__accepts_a_piece_with_additional_tags(self, rule: ExtractionRule) -> None:
        piece = UrlPiece(url=AbsoluteUrl("https://news.example/"), tags=frozenset({"page", "selected", "extra"}))

        assert rule.matches(piece)

    def test_matches__rejects_a_piece_missing_a_required_tag(self, rule: ExtractionRule) -> None:
        piece = UrlPiece(url=AbsoluteUrl("https://news.example/"), tags=frozenset({"page"}))

        assert not rule.matches(piece)

    def test_matches__rejects_a_piece_of_a_different_type(self, rule: ExtractionRule) -> None:
        piece = ContentPiece(
            url=AbsoluteUrl("https://news.example/"), content="<p>News</p>", tags=frozenset({"page", "selected"})
        )

        assert not rule.matches(piece)


class TestExtractor:
    @pytest.mark.parametrize("max_pieces", [0, -1])
    def test_init__rejects_a_nonpositive_piece_limit(self, max_pieces: int) -> None:
        with pytest.raises(InvalidPieceLimit):
            Extractor(rules=[], max_pieces=max_pieces)

    @pytest.mark.asyncio
    async def test_extract__allows_the_queue_to_end_at_the_piece_limit(self) -> None:
        extractor = Extractor(rules=[AddToFeed()], max_pieces=1)

        feed = await extractor.extract(
            str_to_resource_url("https://news.example/"), [FeedTitlePiece(title="City News")]
        )

        assert feed.title == "City News"

    @pytest.mark.asyncio
    async def test_extract__returns_an_empty_feed_for_an_empty_queue(self) -> None:
        url = str_to_resource_url("https://news.example/")

        feed = await Extractor(rules=[AddToFeed()]).extract(url, [])

        assert feed.entries == []

    @pytest.mark.asyncio
    async def test_extract__applies_every_matching_rule(self) -> None:
        url = AbsoluteUrl("https://news.example/edition/index.html")
        html_tags = frozenset({"parsed"})
        metadata_tags = frozenset({"metadata"})
        extractor = Extractor(
            rules=[
                ParseHtml(output_tags=html_tags),
                ExtractFeedTitle(
                    required_tags=html_tags,
                    output_tags=metadata_tags,
                    xpath="normalize-space(//h1)",
                ),
                ExtractFeedDescription(required_tags=html_tags, output_tags=metadata_tags, xpath="//p"),
                ExtractFeedSiteUrl(
                    required_tags=html_tags,
                    output_tags=metadata_tags,
                    xpath="//link[@rel='home']/@href",
                ),
                AddToFeed(required_tags=metadata_tags),
            ]
        )

        feed = await extractor.extract(
            to_resource_url(url),
            [
                ContentPiece(
                    url=url,
                    content=(
                        "<html>"
                        '<head><link rel="home" href="../home" /></head>'
                        "<body><h1>City <em>News</em></h1><p>Weekly reports</p></body></html>"
                    ),
                ),
            ],
        )

        assert feed.title == "City News"
        assert feed.description == "Weekly reports"
        assert feed.site_url == "https://news.example/home"

    @pytest.mark.asyncio
    async def test_extract__skips_a_rule_when_a_required_tag_is_missing(self) -> None:
        url = str_to_resource_url("https://news.example/articles")
        rule = AddToFeed(required_tags=frozenset({"page", "selected"}))
        piece = FeedTitlePiece(title="Unselected title", tags=frozenset({"page"}))

        feed = await Extractor(rules=[rule]).extract(url, [piece])

        assert feed.title == ""

    @pytest.mark.asyncio
    async def test_extract__applies_feed_fields_in_queue_order(self) -> None:
        feed_url = str_to_resource_url("https://news.example/articles")
        extractor = Extractor(rules=[AddToFeed()])

        feed = await extractor.extract(
            feed_url,
            [
                FeedTitlePiece(title="City News"),
                FeedTitlePiece(title="Later title"),
            ],
        )

        assert feed.title == "City News"

    @pytest.mark.asyncio
    async def test_extract__assembles_entry_fields_from_listing_and_article_pages(self) -> None:
        index_url = AbsoluteUrl("https://news.example/edition/index.html")
        first_url = AbsoluteUrl("https://news.example/stories/first")
        published_at = now()
        document_tags = frozenset({"document"})
        entry_tags = frozenset({"entry"})
        entry_url_xpath = "//a[@rel='entry']/@href"
        extractor = Extractor(
            rules=[
                ParseHtml(output_tags=document_tags),
                ExtractEntryBody(
                    required_tags=document_tags,
                    output_tags=entry_tags,
                    url_xpath=entry_url_xpath,
                    xpath="normalize-space(//p)",
                ),
                ExtractEntryPublishedAt(
                    required_tags=document_tags,
                    output_tags=entry_tags,
                    url_xpath=entry_url_xpath,
                    xpath="//time/@datetime",
                ),
                ExtractEntryTitle(required_tags=document_tags, output_tags=entry_tags, xpath="//main/h1"),
                AddToFeed(required_tags=entry_tags),
            ]
        )

        feed = await extractor.extract(
            to_resource_url(index_url),
            [
                ContentPiece(
                    url=index_url,
                    content=(
                        '<a rel="entry" href="../stories/first">First</a><p>Listing preview</p>'
                        f'<time datetime="{published_at.isoformat()}"></time>'
                    ),
                ),
                ContentPiece(url=first_url, content="<main><h1>First article</h1></main>"),
            ],
        )

        (entry,) = feed.entries
        assert entry.external_url == first_url
        assert entry.title == "First article"
        assert entry.body == "Listing preview"
        assert entry.published_at == published_at

    @pytest.fixture()
    def linked_page_extractor(self) -> Extractor:
        crawl_tags = frozenset({"crawl"})
        entry_tags = frozenset({"entry"})
        return Extractor(
            rules=[
                LoadUrl(required_tags=crawl_tags, output_tags=crawl_tags),
                ParseHtml(required_tags=crawl_tags, output_tags=crawl_tags),
                ExtractUrls(required_tags=crawl_tags, output_tags=crawl_tags, xpath="//a/@href"),
                ExtractEntryTitle(required_tags=crawl_tags, output_tags=entry_tags, xpath="//article/h1"),
                AddToFeed(required_tags=entry_tags),
            ]
        )

    @pytest.mark.asyncio
    async def test_extract__resolves_a_link_against_the_redirected_page_base(
        self, linked_page_extractor: Extractor, respx_mock: MockRouter
    ) -> None:
        seed = AbsoluteUrl("https://news.example/start")
        index = "https://news.example/edition/index.html"
        story = "https://news.example/edition/stories/first"
        respx_mock.get(seed).mock(return_value=httpx.Response(302, headers={"Location": index}))
        respx_mock.get(index).mock(
            return_value=httpx.Response(200, text='<base href="stories/"><a href="first">First</a>')
        )
        respx_mock.get(story).mock(return_value=httpx.Response(200, text="<article><h1>First</h1></article>"))
        piece = UrlPiece(url=seed, tags=frozenset({"crawl"}), remaining_loads=2)

        feed = await linked_page_extractor.extract(to_resource_url(seed), [piece])

        assert [entry.external_url for entry in feed.entries] == [story]

    @pytest.mark.asyncio
    async def test_extract__enforces_the_load_budget_on_each_path(
        self, linked_page_extractor: Extractor, respx_mock: MockRouter
    ) -> None:
        seed = AbsoluteUrl("https://news.example/start")
        first_story = "https://news.example/stories/first"
        second_story = "https://news.example/stories/second"
        index = f'<a href="{first_story}">First</a><a href="{second_story}">Second</a>'
        respx_mock.get(seed).mock(side_effect=[httpx.Response(200, text=index)])
        for story in (first_story, second_story):
            respx_mock.get(story).mock(return_value=httpx.Response(200, text=f'<a href="{seed}">Index</a>'))
        piece = UrlPiece(url=seed, tags=frozenset({"crawl"}), remaining_loads=2)

        await linked_page_extractor.extract(to_resource_url(seed), [piece])

        calls = cast(list[Call], respx_mock.calls)
        assert [str(call.request.url) for call in calls] == [seed, first_story, second_story]

    @pytest.mark.asyncio
    async def test_extract__uses_the_resource_url_as_the_feed_url(self) -> None:
        source_url = AbsoluteUrl("https://news.example/index.html?edition=weekly#contents")
        piece = ContentPiece(url=source_url, content="<h1>News</h1>")

        feed = await Extractor(rules=[]).extract(to_resource_url(source_url), [piece])

        assert feed.url == "https://news.example/index.html?edition=weekly"

    @pytest.mark.asyncio
    async def test_extract__keeps_an_entry_url_fragment(self) -> None:
        index_url = AbsoluteUrl("https://news.example/index.html")
        tags: frozenset[str] = frozenset()
        extractor = Extractor(
            rules=[
                ParseHtml(output_tags=tags),
                ExtractEntryTitle(output_tags=tags, xpath="//h1", url_xpath="//a/@href"),
                AddToFeed(),
            ]
        )
        piece = ContentPiece(url=index_url, content='<h1>Earlier</h1><a href="/earlier#summary">Story</a>')

        feed = await extractor.extract(to_resource_url(index_url), [piece])

        (entry,) = feed.entries
        assert entry.external_url == "https://news.example/earlier#summary"

    @pytest.mark.asyncio
    async def test_extract__reads_the_html_charset_when_http_has_no_charset(self, respx_mock: MockRouter) -> None:
        url = AbsoluteUrl("https://news.example/index.html")
        title = "News from the café — latest reports"
        content = f'<meta charset="windows-1252"><title>{title}</title>'.encode("windows-1252")
        respx_mock.get(url).mock(
            return_value=httpx.Response(200, headers={"Content-Type": "text/html"}, content=content)
        )
        url_tags = frozenset({"url"})
        content_tags = frozenset({"content"})
        document_tags = frozenset({"document"})
        metadata_tags = frozenset({"metadata"})
        extractor = Extractor(
            rules=[
                LoadUrl(required_tags=url_tags, output_tags=content_tags),
                ParseHtml(required_tags=content_tags, output_tags=document_tags),
                ExtractFeedTitle(required_tags=document_tags, output_tags=metadata_tags, xpath="//title"),
                AddToFeed(required_tags=metadata_tags),
            ]
        )

        feed = await extractor.extract(to_resource_url(url), [UrlPiece(url=url, tags=url_tags, remaining_loads=1)])

        assert feed.title == title

    @pytest.mark.asyncio
    async def test_extract__enforces_the_piece_limit_when_fragment_rules_form_a_cycle(self) -> None:
        url = AbsoluteUrl("https://news.example/index.html")
        document_tags = frozenset({"document"})
        outer_tags = frozenset({"outer"})
        inner_tags = frozenset({"inner"})
        extractor = Extractor(
            rules=[
                ParseHtml(output_tags=document_tags),
                ExtractHtml(required_tags=document_tags, output_tags=outer_tags, xpath="//body/div"),
                ExtractHtml(required_tags=outer_tags, output_tags=inner_tags, xpath="./div"),
                ExtractHtml(required_tags=inner_tags, output_tags=outer_tags, xpath="./div"),
            ],
            max_pieces=4,
        )
        content = "<div>" * 6 + "Nested content" + "</div>" * 6

        with pytest.raises(PieceLimitExceeded):
            await extractor.extract(to_resource_url(url), [ContentPiece(url=url, content=content)])

    @pytest.mark.asyncio
    async def test_extract__keeps_the_original_and_cleaned_html_branches_independent(self) -> None:
        url = AbsoluteUrl("https://news.example/index.html")
        content = """
            <main>
              <article>
                <h2>Story</h2><a href="/story">Link</a>
                <p>Before <span class="housekeeping">Related links</span> after</p>
              </article>
            </main>
        """
        page_tags = frozenset({"page"})
        document_tags = frozenset({"document"})
        card_tags = frozenset({"card"})
        clean_tags = frozenset({"clean"})
        result_tags = frozenset({"result"})
        entry_url_xpath = "./a/@href"
        extractor = Extractor(
            rules=[
                ParseHtml(required_tags=page_tags, output_tags=document_tags),
                ExtractHtml(required_tags=document_tags, output_tags=card_tags, xpath="//main/article"),
                RemoveHtml(required_tags=card_tags, output_tags=clean_tags, xpath="./p/span[@class='housekeeping']"),
                ExtractFeedTitle(required_tags=card_tags, output_tags=result_tags, xpath="./p/span"),
                ExtractEntryTitle(
                    required_tags=clean_tags, output_tags=result_tags, url_xpath=entry_url_xpath, xpath="./h2"
                ),
                ExtractEntryBody(
                    required_tags=clean_tags, output_tags=result_tags, url_xpath=entry_url_xpath, xpath="./p"
                ),
                AddToFeed(required_tags=result_tags),
            ]
        )

        feed = await extractor.extract(to_resource_url(url), [ContentPiece(url=url, content=content, tags=page_tags)])

        (entry,) = feed.entries
        assert feed.title == "Related links"
        assert entry.body == "<p>Before  after</p>"


class TestExtractFeedTitle:
    def test_transform__emits_the_title(self, article_piece: HtmlPiece) -> None:
        tags = frozenset({"result"})
        rule = ExtractFeedTitle(xpath="(//h1)[1]", output_tags=tags)

        assert list(rule.transform(article_piece)) == [
            FeedTitlePiece(title="First article", tags=tags, remaining_loads=2)
        ]

    def test_transform__emits_no_piece_when_the_title_is_missing(self, article_piece: HtmlPiece) -> None:
        rule = ExtractFeedTitle(xpath="//h2", output_tags=frozenset())

        assert list(rule.transform(article_piece)) == []


class TestExtractFeedDescription:
    def test_transform__emits_the_description(self, article_piece: HtmlPiece) -> None:
        tags = frozenset({"result"})
        rule = ExtractFeedDescription(xpath="normalize-space(//p)", output_tags=tags)

        assert list(rule.transform(article_piece)) == [
            FeedDescriptionPiece(description="Before menu after", tags=tags, remaining_loads=2)
        ]

    def test_transform__emits_no_piece_when_the_description_is_missing(self, article_piece: HtmlPiece) -> None:
        rule = ExtractFeedDescription(xpath="//aside", output_tags=frozenset())

        assert list(rule.transform(article_piece)) == []


class TestExtractFeedSiteUrl:
    def test_transform__resolves_the_site_url_against_the_html_base(self, article_piece: HtmlPiece) -> None:
        rule = ExtractFeedSiteUrl(output_tags=frozenset({"result"}), xpath="//link[@rel='canonical']/@href")

        assert list(rule.transform(article_piece)) == [
            FeedSiteUrlPiece(
                site_url=AbsoluteUrl("https://news.example/stories/first"),
                tags=frozenset({"result"}),
                remaining_loads=2,
            )
        ]

    @pytest.mark.parametrize("xpath", ["//link[@rel='home']/@href", "'mailto:news@news.example'"])
    def test_transform__emits_no_piece_when_the_site_url_is_unusable(
        self, article_piece: HtmlPiece, xpath: str
    ) -> None:
        rule = ExtractFeedSiteUrl(xpath=xpath, output_tags=frozenset())

        assert list(rule.transform(article_piece)) == []


class TestLoadUrl:
    @pytest.mark.asyncio
    async def test_apply__returns_raw_content_at_the_normalized_effective_url(
        self, feed_builder: FeedBuilder, respx_mock: MockRouter
    ) -> None:
        url = AbsoluteUrl("https://news.example/start")
        effective_url = "https://news.example/"
        content = "<title>Café News</title>".encode("windows-1252")
        respx_mock.get(url).mock(return_value=httpx.Response(302, headers={"Location": effective_url}))
        respx_mock.get(effective_url).mock(
            return_value=httpx.Response(
                200, content=content, headers={"Content-Type": "text/html; charset=windows-1252"}
            )
        )
        rule = LoadUrl(output_tags=frozenset({"response"}))

        pieces = list(await rule.apply(UrlPiece(url=url, remaining_loads=1), feed_builder))

        assert pieces == [
            ContentPiece(
                url=AbsoluteUrl("https://news.example"),
                content=content,
                encoding="windows-1252",
                tags=frozenset({"response"}),
                remaining_loads=0,
            )
        ]

    @pytest.mark.asyncio
    async def test_apply__skips_loading_when_the_budget_is_exhausted(
        self, feed_builder: FeedBuilder, respx_mock: MockRouter
    ) -> None:
        piece = UrlPiece(url=AbsoluteUrl("https://news.example/index.html"), remaining_loads=0)

        pieces = list(await LoadUrl(output_tags=frozenset()).apply(piece, feed_builder))

        assert pieces == []
        assert not respx_mock.calls

    @pytest.mark.asyncio
    async def test_apply__rejects_a_response_url_that_cannot_be_normalized(
        self, feed_builder: FeedBuilder, mocker: MockerFixture
    ) -> None:
        url = AbsoluteUrl("https://news.example/start")
        response_url = "ftp://news.example/archive"
        response = httpx.Response(200, request=httpx.Request("GET", response_url), text="Story preview")
        mocker.patch("ffun.loader.domain.load_content_with_proxies", return_value=response)
        rule = LoadUrl(output_tags=frozenset())

        with pytest.raises(InvalidLoadedUrl) as raised:
            await rule.apply(UrlPiece(url=url, remaining_loads=1), feed_builder)

        assert response_url in str(raised.value)


class TestParseHtml:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("base_markup", "expected_base_url"),
        [
            ("", "https://news.example/digest/index.html"),
            ('<base href="stories/"><base href="/other/">', "https://news.example/digest/stories/"),
            ('<base href="mailto:news@news.example">', "https://news.example/digest/index.html"),
        ],
    )
    async def test_apply__chooses_the_html_base(
        self, feed_builder: FeedBuilder, base_markup: str, expected_base_url: str
    ) -> None:
        url = AbsoluteUrl("https://news.example/digest/index.html")
        source = ContentPiece(
            url=url, content=f"<head>{base_markup}<title>City News</title></head>", remaining_loads=2
        )
        rule = ParseHtml(output_tags=frozenset({"document"}))

        (piece,) = await rule.apply(source, feed_builder)

        assert isinstance(piece, HtmlPiece)
        assert piece.url == url
        assert piece.base_url == expected_base_url
        assert piece.tags == frozenset({"document"})
        assert piece.remaining_loads == 2
        assert html.first_text(piece.element, "//title") == "City News"

    @pytest.mark.asyncio
    async def test_apply__parses_decoded_xhtml_with_an_encoding_declaration(self, feed_builder: FeedBuilder) -> None:
        url = AbsoluteUrl("https://news.example/index.html")
        content = (
            '<?xml version="1.0" encoding="windows-1252"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Café News</title></head></html>'
        )

        (piece,) = await ParseHtml(output_tags=frozenset()).apply(ContentPiece(url=url, content=content), feed_builder)

        assert isinstance(piece, HtmlPiece)
        assert html.first_text(piece.element, "//title") == "Café News"


class TestHtmlRule:
    @pytest.mark.asyncio
    async def test_apply__returns_the_transformation_output(
        self, article_piece: HtmlPiece, feed_builder: FeedBuilder
    ) -> None:
        rule: _HtmlRule = ExtractFeedTitle(output_tags=frozenset(), xpath="(//h1)[1]")

        assert list(await rule.apply(article_piece, feed_builder)) == [
            FeedTitlePiece(title="First article", remaining_loads=2)
        ]


class TestRemoveHtml:
    @pytest.mark.parametrize(
        ("xpath", "expected_text"),
        [("//span", "Before  after"), ("//aside", "Before menu after")],
    )
    def test_transform__removes_matches_on_a_copy(
        self, article_piece: HtmlPiece, xpath: str, expected_text: str
    ) -> None:
        rule = RemoveHtml(xpath=xpath, output_tags=frozenset({"clean"}))

        (piece,) = rule.transform(article_piece)

        assert isinstance(piece, HtmlPiece)
        assert html.first_text(piece.element, "//p") == expected_text
        assert html.first_text(article_piece.element, "//p") == "Before menu after"
        assert piece.tags == frozenset({"clean"})
        assert piece.remaining_loads == article_piece.remaining_loads

    def test_transform__emits_no_piece_when_removing_the_root(self, article_piece: HtmlPiece) -> None:
        rule = RemoveHtml(xpath="/html", output_tags=frozenset())

        assert list(rule.transform(article_piece)) == []


class TestExtractHtml:
    def test_transform__emits_matching_elements_in_document_order(self, article_piece: HtmlPiece) -> None:
        rule = ExtractHtml(xpath="//article", output_tags=frozenset({"fragment"}))

        first, second = rule.transform(article_piece)

        assert isinstance(first, HtmlPiece)
        assert isinstance(second, HtmlPiece)
        assert html.first_text(first.element, ".//h1") == "First article"
        assert html.first_text(second.element, ".//h1") == "Second article"
        assert first.tags == second.tags == frozenset({"fragment"})
        assert first.remaining_loads == second.remaining_loads == article_piece.remaining_loads

    def test_transform__copies_the_selected_element(self, article_piece: HtmlPiece) -> None:
        rule = ExtractHtml(xpath="(//article)[1]", output_tags=frozenset())
        (piece,) = rule.transform(article_piece)
        assert isinstance(piece, HtmlPiece)

        next(html.select_elements(piece.element, ".//h1")).drop_tree()

        assert html.first_text(piece.element, ".//h1") is None
        assert html.first_text(article_piece.element, "(//h1)[1]") == "First article"

    def test_transform__emits_no_pieces_for_scalar_matches(self, article_piece: HtmlPiece) -> None:
        rule = ExtractHtml(xpath="//h1/text()", output_tags=frozenset())

        assert list(rule.transform(article_piece)) == []


class TestExtractUrls:
    def test_transform__resolves_a_relative_url_against_the_page_base(self, article_piece: HtmlPiece) -> None:
        rule = ExtractUrls(xpath="'first'", output_tags=frozenset({"link"}))

        assert list(rule.transform(article_piece)) == [
            UrlPiece(
                url=AbsoluteUrl("https://news.example/stories/first"), tags=frozenset({"link"}), remaining_loads=2
            )
        ]

    def test_transform__repairs_a_bare_hostname(self, article_piece: HtmlPiece) -> None:
        rule = ExtractUrls(xpath="'archive.com'", output_tags=frozenset())

        assert list(rule.transform(article_piece)) == [
            UrlPiece(url=AbsoluteUrl("https://archive.com"), remaining_loads=2)
        ]

    def test_transform__deduplicates_fragment_variants(self, article_piece: HtmlPiece) -> None:
        rule = ExtractUrls(
            xpath='("https://news.example/first#latest", "https://news.example/first#archive")',
            output_tags=frozenset(),
        )

        assert list(rule.transform(article_piece)) == [
            UrlPiece(url=AbsoluteUrl("https://news.example/first"), remaining_loads=2)
        ]

    @pytest.mark.parametrize("xpath", ["'mailto:news@news.example'", "42", "''", "'  '"])
    def test_transform__skips_an_unusable_result(self, article_piece: HtmlPiece, xpath: str) -> None:
        rule = ExtractUrls(xpath=xpath, output_tags=frozenset())

        assert list(rule.transform(article_piece)) == []


class TestEntryFieldRule:
    @pytest.mark.parametrize(
        ("url_xpath", "expected_url"),
        [
            (None, "https://news.example/digest/index.html"),
            ("//link[@rel='canonical']/@href", "https://news.example/stories/first"),
            ("//link[@rel='alternate']/@href", None),
            ("'mailto:news@news.example'", None),
        ],
    )
    def test_entry_url__selects_the_entry_url(
        self, article_piece: HtmlPiece, url_xpath: str | None, expected_url: str | None
    ) -> None:
        rule: _EntryFieldRule = ExtractEntryTitle(xpath="(//h1)[1]", output_tags=frozenset(), url_xpath=url_xpath)

        assert rule.entry_url(article_piece) == expected_url

    def test_transform__emits_the_field_with_the_resolved_url(self, article_piece: HtmlPiece) -> None:
        rule: _EntryFieldRule = ExtractEntryTitle(
            xpath="(//h1)[1]", output_tags=frozenset(), url_xpath="//link[@rel='canonical']/@href"
        )

        assert list(rule.transform(article_piece)) == [
            EntryTitlePiece(
                url=AbsoluteUrl("https://news.example/stories/first"), title="First article", remaining_loads=2
            )
        ]

    @pytest.mark.parametrize("url_xpath", ["//link[@rel='alternate']/@href", "'mailto:news@news.example'"])
    def test_transform__emits_no_piece_when_the_url_is_unusable(
        self, article_piece: HtmlPiece, url_xpath: str
    ) -> None:
        rule: _EntryFieldRule = ExtractEntryTitle(xpath="(//h1)[1]", output_tags=frozenset(), url_xpath=url_xpath)

        assert list(rule.transform(article_piece)) == []

    def test_transform__emits_no_piece_when_the_field_is_missing(self, article_piece: HtmlPiece) -> None:
        rule: _EntryFieldRule = ExtractEntryTitle(xpath="//h2", output_tags=frozenset())

        assert list(rule.transform(article_piece)) == []


class TestExtractEntryTitle:
    def test_extract_field__returns_the_title_for_the_given_url(self, article_piece: HtmlPiece) -> None:
        url = AbsoluteUrl("https://news.example/stories/first")
        tags = frozenset({"result"})
        rule = ExtractEntryTitle(xpath="(//h1)[1]", output_tags=tags)

        assert rule.extract_field(article_piece, url) == EntryTitlePiece(
            url=url, title="First article", tags=tags, remaining_loads=2
        )

    def test_extract_field__returns_none_when_the_title_is_missing(self, article_piece: HtmlPiece) -> None:
        rule = ExtractEntryTitle(xpath="//h2", output_tags=frozenset())

        assert rule.extract_field(article_piece, article_piece.url) is None


class TestExtractEntryBody:
    def test_extract_field__returns_the_body_for_the_given_url(self, article_piece: HtmlPiece) -> None:
        url = AbsoluteUrl("https://news.example/stories/first")
        tags = frozenset({"result"})
        rule = ExtractEntryBody(xpath="//p", output_tags=tags)

        assert rule.extract_field(article_piece, url) == EntryBodyPiece(
            url=url, body="<p>Before <span>menu</span> after</p>", tags=tags, remaining_loads=2
        )

    @pytest.mark.parametrize("xpath", ["//aside", "normalize-space(//aside)"])
    def test_extract_field__returns_none_when_the_body_is_missing(self, article_piece: HtmlPiece, xpath: str) -> None:
        rule = ExtractEntryBody(xpath=xpath, output_tags=frozenset())

        assert rule.extract_field(article_piece, article_piece.url) is None


class TestExtractEntryPublishedAt:
    @pytest.mark.parametrize("offset", [None, datetime.timezone(datetime.timedelta(hours=2))])
    def test_extract_field__interprets_iso_timestamps(
        self, article_piece: HtmlPiece, offset: datetime.tzinfo | None
    ) -> None:
        timestamp = now().replace(tzinfo=offset)
        rule = ExtractEntryPublishedAt(xpath=f"'{timestamp.isoformat()}'", output_tags=frozenset())

        field = rule.extract_field(article_piece, article_piece.url)

        assert field is not None
        assert field.published_at == timestamp.replace(tzinfo=offset or datetime.UTC)
        assert field.published_at.utcoffset() == (offset or datetime.UTC).utcoffset(field.published_at)

    def test_extract_field__interprets_calendar_dates_at_midnight_utc(self, article_piece: HtmlPiece) -> None:
        url = AbsoluteUrl("https://news.example/stories/first")
        tags = frozenset({"result"})
        rule = ExtractEntryPublishedAt(xpath="//time/@datetime", output_tags=tags)

        assert rule.extract_field(article_piece, url) == EntryPublishedAtPiece(
            url=url, published_at=datetime.datetime(2024, 2, 29, tzinfo=datetime.UTC), tags=tags, remaining_loads=2
        )

    @pytest.mark.parametrize("xpath", ["//meta[@name='missing']/@content", "'unknown'"])
    def test_extract_field__returns_none_for_unusable_timestamps(self, article_piece: HtmlPiece, xpath: str) -> None:
        rule = ExtractEntryPublishedAt(xpath=xpath, output_tags=frozenset())

        assert rule.extract_field(article_piece, article_piece.url) is None


class TestAddToFeed:
    @pytest.mark.asyncio
    async def test_apply__adds_the_feed_title(self, feed_builder: FeedBuilder) -> None:
        await AddToFeed().apply(FeedTitlePiece(title="City News"), feed_builder)

        assert feed_builder.build().title == "City News"

    @pytest.mark.asyncio
    async def test_apply__adds_the_feed_description(self, feed_builder: FeedBuilder) -> None:
        await AddToFeed().apply(FeedDescriptionPiece(description="Weekly reports"), feed_builder)

        assert feed_builder.build().description == "Weekly reports"

    @pytest.mark.asyncio
    async def test_apply__adds_the_feed_site_url(self, feed_builder: FeedBuilder) -> None:
        site_url = AbsoluteUrl("https://news.example/")

        await AddToFeed().apply(FeedSiteUrlPiece(site_url=site_url), feed_builder)

        assert feed_builder.build().site_url == site_url

    @pytest.mark.asyncio
    async def test_apply__adds_an_entry_title_at_the_piece_url(self, feed_builder: FeedBuilder) -> None:
        url = AbsoluteUrl("https://news.example/stories/first")
        piece = EntryTitlePiece(url=url, title="First article")

        await AddToFeed().apply(piece, feed_builder)
        (entry,) = feed_builder.build().entries

        assert entry.external_url == url
        assert entry.title == "First article"

    @pytest.mark.asyncio
    async def test_apply__adds_an_entry_body_at_the_piece_url(self, feed_builder: FeedBuilder) -> None:
        url = AbsoluteUrl("https://news.example/stories/first")
        feed_builder.get_or_create(url).add_title("First article")
        piece = EntryBodyPiece(url=url, body="<p>Latest reports</p>")

        await AddToFeed().apply(piece, feed_builder)
        (entry,) = feed_builder.build().entries

        assert entry.body == "<p>Latest reports</p>"

    @pytest.mark.asyncio
    async def test_apply__adds_an_entry_publication_time_at_the_piece_url(self, feed_builder: FeedBuilder) -> None:
        url = AbsoluteUrl("https://news.example/stories/first")
        feed_builder.get_or_create(url).add_title("First article")
        published_at = now()

        await AddToFeed().apply(EntryPublishedAtPiece(url=url, published_at=published_at), feed_builder)
        (entry,) = feed_builder.build().entries

        assert entry.published_at == published_at

    @pytest.mark.asyncio
    async def test_apply__emits_no_new_pieces(self, feed_builder: FeedBuilder) -> None:
        pieces = await AddToFeed().apply(FeedTitlePiece(title="City News"), feed_builder)

        assert list(pieces) == []

    @pytest.mark.asyncio
    async def test_apply__rejects_an_unsupported_piece(self, feed_builder: FeedBuilder) -> None:
        piece = UrlPiece(url=AbsoluteUrl("https://news.example/"))

        with pytest.raises(AssertionError, match="AddToFeed received an unsupported data piece"):
            await AddToFeed().apply(piece, feed_builder)
