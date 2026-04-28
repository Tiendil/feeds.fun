from typing import cast

import pytest
from bs4 import BeautifulSoup, Tag

from ffun.core.entities import BaseEntity
from ffun.librarian.text_cleaners import _remove_non_semantic_attributes, clear_html, clear_nothing


class TestClearNothing:

    @pytest.mark.parametrize(
        "input_text, expected_text",
        [
            ("", ""),
            ("some-text some-text", "some-text some-text"),
            ("some <tagged> text</tagged>", "some <tagged> text</tagged>"),
        ],
    )
    def test(self, input_text: str, expected_text: str) -> None:
        assert clear_nothing(input_text) == expected_text


class TestRemoveNonSemanticAttributes:

    def test(self) -> None:
        soup = BeautifulSoup(
            """
<a aria-label="Link label" class="link" data-id="42" href="https://example.com"
   id="main" lang="en" onclick="alert()" style="display: block" target="_blank"
   title="Example">Some link</a>
""",
            "html.parser",
        )

        tag = cast(Tag, soup.find("a"))

        _remove_non_semantic_attributes(tag)

        assert cast(dict[str, object], tag.attrs) == {
            "aria-label": "Link label",
            "href": "https://example.com",
            "lang": "en",
            "title": "Example",
        }


class TestClearHTML:

    def test(self) -> None:
        input_text = """
<h1>Some title</h1>
<div>
<script>some script</script>
<style>some style</style>
        Text to keep
<meta content="some meta"/>
<iframe>some iframe</iframe>
<img alt="some img" src="some src" title="some title" width="100" height="100" class="some class" style="some style" />
</div>

<h2>Some other title 2</h2>
        <h3>Some other title 3</h3>
        <h4>Some other title 4</h4>
        <h5>Some other title 5</h5>
        <h6>Some other title 6</h6>

<a href="https://example.com">Some link</a>

Just text

<p>Some paragraph</p>

<ul>
<li>Some list item 1</li>
<li>Some list item 2</li>
<li><ol><li>Some nestedlist item 3</li>
<li>Some nestedlist item 4</li></ol></li>
</ul>
"""
        expected_text = """<h1>Some title</h1> Text to keep <img alt="some img" src="some src" title="some title"/> <h2>Some other title 2</h2> <h3>Some other title 3</h3> <h4>Some other title 4</h4> <h5>Some other title 5</h5> <h6>Some other title 6</h6> <a href="https://example.com">Some link</a> Just text <p>Some paragraph</p> <ul> <li>Some list item 1</li> <li>Some list item 2</li> <li><ol><li>Some nestedlist item 3</li> <li>Some nestedlist item 4</li></ol></li> </ul>"""  # noqa

        assert clear_html(input_text) == expected_text

    def test_removes_non_semantic_attributes(self) -> None:
        input_text = """
<h1 class="title" id="main">Some title</h1>
<p class="lead" style="color: red" data-id="42" onclick="alert()">Some paragraph</p>
<a class="link" style="display: block" href="https://example.com" title="Example" target="_blank">Some link</a>
"""
        expected_text = (
            "<h1>Some title</h1> "
            "<p>Some paragraph</p> "
            '<a href="https://example.com" title="Example">Some link</a>'
        )

        assert clear_html(input_text) == expected_text

    def test_keeps_semantic_attributes(self) -> None:
        input_text = """
<p aria-label="Short label" lang="en" title="Title">Some paragraph</p>
<a href="https://example.com" hreflang="en" title="Example">Some link</a>
<img alt="Chart" class="chart" height="100" longdesc="https://example.com/chart"
     src="https://example.com/chart.png" srcset="https://example.com/chart-2x.png 2x"
     style="width: 100px" title="Chart title" width="100" />
"""
        expected_text = (
            '<p aria-label="Short label" lang="en" title="Title">Some paragraph</p> '
            '<a href="https://example.com" title="Example">Some link</a> '
            '<img alt="Chart" longdesc="https://example.com/chart" src="https://example.com/chart.png" '
            'srcset="https://example.com/chart-2x.png 2x" title="Chart title"/>'
        )

        assert clear_html(input_text) == expected_text

    def test_broken_unicode(self) -> None:
        input_text = "some text &#55358;bla-bla"

        expected_text = "some text bla-bla"

        processed_text = clear_html(input_text)

        assert processed_text == expected_text

        # parser resulting string with pydantic
        class TestModel(BaseEntity):
            text: str

        model = TestModel(text=processed_text)

        assert model.text == expected_text
