import pydantic
import pytest

from ffun.core.utils import now
from ffun.domain.entities import AbsoluteUrl
from ffun.extractors.entities import ContentPiece, DataPiece, EntryPublishedAtPiece, HtmlPiece
from ffun.extractors.html import parse_document

_URL = AbsoluteUrl("https://news.example/articles/first")


class TestDataPiece:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [({}, 0), ({"remaining_loads": 0}, 0), ({"remaining_loads": 2}, 2)],
    )
    def test_model_validate__accepts_a_nonnegative_load_budget(self, data: dict[str, int], expected: int) -> None:
        assert DataPiece.model_validate(data).remaining_loads == expected

    def test_model_validate__rejects_a_negative_load_budget(self) -> None:
        data: dict[str, int] = {"remaining_loads": -1}
        with pytest.raises(pydantic.ValidationError, match="remaining_loads"):
            DataPiece.model_validate(data)


class TestContentPiece:
    @pytest.mark.parametrize("content", ["    indented line\n\n", b"    indented line\n\n"])
    def test_model_validate__preserves_whitespace(self, content: str | bytes) -> None:
        data: dict[str, object] = {"url": _URL, "content": content}

        assert ContentPiece.model_validate(data).content == content


class TestHtmlPiece:
    def test_model_validate__accepts_a_parsed_html_element(self) -> None:
        element = parse_document("<p>Story preview</p>", _URL, None)
        data: dict[str, object] = {"url": _URL, "base_url": _URL, "element": element}

        piece = HtmlPiece.model_validate(data)

        assert piece.element.text_content() == "Story preview"

    def test_model_validate__rejects_an_object_without_the_html_protocol(self) -> None:
        data: dict[str, object] = {"url": _URL, "base_url": _URL, "element": object()}
        with pytest.raises(pydantic.ValidationError, match="element"):
            HtmlPiece.model_validate(data)


class TestEntryPublishedAtPiece:
    def test_model_validate__accepts_a_timezone_aware_publication_time(self) -> None:
        published_at = now()
        data: dict[str, object] = {"url": _URL, "published_at": published_at}

        piece = EntryPublishedAtPiece.model_validate(data)

        assert piece.published_at == published_at

    def test_model_validate__rejects_a_naive_publication_time(self) -> None:
        data: dict[str, object] = {"url": _URL, "published_at": now().replace(tzinfo=None)}
        with pytest.raises(pydantic.ValidationError, match="published_at"):
            EntryPublishedAtPiece.model_validate(data)
