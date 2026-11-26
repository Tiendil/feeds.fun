from html import escape
from types import ModuleType
from typing import Callable, Iterator, Protocol, cast, runtime_checkable

import elementpath
from elementpath.protocols import LxmlElementProtocol
from lxml import etree, html  # type: ignore[import-untyped]

from ffun.domain.entities import AbsoluteUrl
from ffun.extractors import errors


@runtime_checkable
class HtmlElement(LxmlElementProtocol, Protocol):
    def text_content(self) -> str:
        pass

    def drop_tree(self) -> None:
        pass


_lxml_html: ModuleType = html
_lxml_etree: ModuleType = etree
_html_parser: Callable[..., object] = _lxml_html.HTMLParser
_document_from_string: Callable[..., HtmlElement] = _lxml_html.document_fromstring
_serialize_element: Callable[..., object] = _lxml_html.tostring
_parser_error: type[Exception] = _lxml_etree.ParserError


def parse_document(content: bytes | str, url: AbsoluteUrl, encoding: str | None) -> HtmlElement:
    if isinstance(content, str):
        content = content.encode("utf-8")
        encoding = "utf-8"

    try:
        parser = _html_parser(encoding=encoding)
    except LookupError:
        parser = _html_parser()

    try:
        return _document_from_string(content, parser=parser)
    except _parser_error as error:
        raise errors.InvalidHtml(url=url) from error


def select(element: HtmlElement, xpath: str) -> Iterator[object]:
    return cast(Iterator[object], elementpath.iter_select(element, xpath, fragment=False, item=element))


def select_elements(element: HtmlElement, xpath: str) -> Iterator[HtmlElement]:
    return (result for result in select(element, xpath) if isinstance(result, HtmlElement))


def first_text(element: HtmlElement, xpath: str | None) -> str | None:
    if xpath is None:
        return None

    for result in select(element, xpath):
        if isinstance(result, HtmlElement):
            result = result.text_content()
        if isinstance(result, str) and (text := result.strip()):
            return text

    return None


def first_body(element: HtmlElement, xpath: str | None) -> str | None:
    if xpath is None:
        return None

    for result in select(element, xpath):
        if isinstance(result, HtmlElement):
            return cast(str, _serialize_element(result, encoding="unicode", with_tail=False))
        if isinstance(result, str) and (text := result.strip()):
            return escape(text)

    return None
