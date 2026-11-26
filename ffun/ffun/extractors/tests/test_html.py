import pytest

from ffun.domain.entities import AbsoluteUrl
from ffun.extractors.errors import InvalidHtml
from ffun.extractors.html import first_body, first_text, parse_document, select, select_elements

_PAGE_URL = AbsoluteUrl("https://news.example/edition/index.html")


class TestParseDocument:
    def test_preserves_decoded_text_with_a_conflicting_encoding(self) -> None:
        document = parse_document(
            '<meta charset="windows-1252"><p>Café — latest reports</p>',
            _PAGE_URL,
            encoding="windows-1252",
        )

        assert document.text_content() == "Café — latest reports"

    def test_decodes_bytes_using_the_supplied_encoding(self) -> None:
        content = "<p>Price €5</p>".encode("windows-1252")

        document = parse_document(content, _PAGE_URL, encoding="windows-1252")

        assert document.text_content() == "Price €5"

    @pytest.mark.parametrize("encoding", [None, "unrecognized-charset"])
    def test_falls_back_to_the_document_charset(self, encoding: str | None) -> None:
        content = '<meta charset="windows-1252"><p>Café — latest reports</p>'.encode("windows-1252")

        document = parse_document(content, _PAGE_URL, encoding=encoding)

        assert document.text_content() == "Café — latest reports"

    def test_reports_empty_html_with_its_source_url(self) -> None:
        with pytest.raises(InvalidHtml) as raised:
            parse_document(b"", _PAGE_URL, encoding=None)

        assert _PAGE_URL in str(raised.value)


class TestSelect:
    def test_returns_relative_matches_in_document_order(self) -> None:
        document = parse_document("<main><p>First</p><p>Second</p></main><p>Outside</p>", _PAGE_URL, encoding=None)
        (main,) = select_elements(document, "//main")

        assert list(select(main, "./p/text()")) == ["First", "Second"]

    def test_returns_a_scalar_xpath_result(self) -> None:
        document = parse_document("<p>First</p><p>Second</p>", _PAGE_URL, encoding=None)

        assert list(select(document, "count(/html/body/p)")) == [2]


class TestSelectElements:
    def test_returns_the_matching_elements(self) -> None:
        document = parse_document("<p>First</p><p>Second</p>", _PAGE_URL, encoding=None)

        assert [element.text_content() for element in select_elements(document, "//p")] == ["First", "Second"]

    def test_excludes_xpath_text_results(self) -> None:
        document = parse_document("<p>Text</p>", _PAGE_URL, encoding=None)

        assert list(select_elements(document, "//p/text()")) == []


class TestFirstText:
    def test_returns_the_first_non_blank_element_text(self) -> None:
        document = parse_document("<p> </p><p> First <b>headline</b> </p><p>Later</p>", _PAGE_URL, encoding=None)

        assert first_text(document, "//p") == "First headline"

    def test_trims_a_selected_attribute(self) -> None:
        document = parse_document('<a href="  /posts/report  ">Report</a>', _PAGE_URL, encoding=None)

        assert first_text(document, "//a/@href") == "/posts/report"

    @pytest.mark.parametrize("xpath", [None, "//missing", "'   '", "count(//p)"])
    def test_returns_none_without_usable_text(self, xpath: str | None) -> None:
        document = parse_document("<p>Text</p>", _PAGE_URL, encoding=None)

        assert first_text(document, xpath) is None


class TestFirstBody:
    def test_serializes_the_first_matching_element_without_its_tail(self) -> None:
        document = parse_document(
            "<div><p>Read <b>more</b></p>Outside the body<p>Later</p></div>",
            _PAGE_URL,
            encoding=None,
        )

        assert first_body(document, "//p") == "<p>Read <b>more</b></p>"

    def test_escapes_selected_text(self) -> None:
        content = '<p title=" Use &lt;strong&gt; &amp; keep the text ">Text</p>'
        document = parse_document(content, _PAGE_URL, encoding=None)

        assert first_body(document, "//p/@title") == "Use &lt;strong&gt; &amp; keep the text"

    @pytest.mark.parametrize("xpath", [None, "//missing", "'   '", "count(//p)"])
    def test_returns_none_without_a_usable_body(self, xpath: str | None) -> None:
        document = parse_document("<p>Text</p>", _PAGE_URL, encoding=None)

        assert first_body(document, xpath) is None
