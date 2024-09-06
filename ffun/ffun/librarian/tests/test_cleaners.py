
import pytest

from ffun.librarian.text_cleaners import clear_nothing, clear_html


class TestClearNothing:

    @pytest.mark.parametrize("input_text, expected_text",
                             [('', ''),
                              ('some-text some-text', 'some-text some-text'),
                              ('some <tagged> text</tagged>', 'some <tagged> text</tagged>')])
    def test(self, input_text: str, expected_text: str) -> None:
        assert clear_nothing(input_text) == expected_text


class TestClearHTML:

    def test(self) -> None:
        input_text = """
<h1>Some title</h1>
<div>
<script>some script</script>
<style>some style</style>
        Test to keep
<meta>some meta</meta>
<iframe>some iframe</iframe>
<img>some img</img>
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
        expected_text = """<h1>Some title</h1> Test to keep some meta some img <h2>Some other title 2</h2> <h3>Some other title 3</h3> <h4>Some other title 4</h4> <h5>Some other title 5</h5> <h6>Some other title 6</h6> <a href="https://example.com">Some link</a> Just text <p>Some paragraph</p> <ul> <li>Some list item 1</li> <li>Some list item 2</li> <li><ol><li>Some nestedlist item 3</li> <li>Some nestedlist item 4</li></ol></li> </ul>"""

        assert clear_html(input_text) == expected_text
