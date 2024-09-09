import pytest

from ffun.librarian.tag_extractors import dog_tags_extractor


class TestDogTagsExtractor:

    raw_answer = """\
Here is a list of tags to describe the provided text, categorized as requested:

### Topics
- @singlwordtag
- @multi-word-tag
- @duplicated-tag


### Areas
- @tag-with-34-numbers-324
- @duplicated-tag

@tag-in-the-line-1, @tag-in-the-line-2, @tag-in-the-line-3

@__broken_taG-that-should-be-found

@-_this-----tag-will-be-found-too

this-tag-will-not-be-found
andthistagtoo

и-этот-тег-тоже-не-найдут

-and-this-one-tag-is-wrong
"""

    @pytest.mark.asyncio
    async def test(self) -> None:
        tags = dog_tags_extractor(self.raw_answer)

        expected_tags = {
            "singlwordtag",
            "multi-word-tag",
            "duplicated-tag",
            "tag-with-34-numbers-324",
            "tag-in-the-line-1",
            "tag-in-the-line-2",
            "tag-in-the-line-3",
            "__broken_tag-that-should-be-found",
            "-_this-----tag-will-be-found-too",
        }

        assert tags == expected_tags
