import pytest

from ffun.librarian.processors import upper_case_title
from ffun.library.entities import Entry
from ffun.ontology.entities import ProcessorTag, TagCategory


processor = upper_case_title.Processor(name="upper_case_title")

expected_tag = "upper-case-title"


class TestEncodeSpecialCharacters:
    @pytest.mark.parametrize(
        "title, has_tag",
        [
            ("", False),
            ("UPPER CASE", True),
            ("  UPPER ,CASE  ", True),
            ("«СЛОЖНЫЙ ЮНИКОД» #324", True),
            ("«Сложный Юникод» #324", False),
            ("Normal title?", False),
            ("lower case only title", False),
            ("только нижний кейс юникод", False),
        ],
    )
    @pytest.mark.asyncio
    async def test(self, fake_entry: Entry, title: str, has_tag: bool) -> None:
        fake_entry.title = title

        tags = await processor.process(fake_entry)

        expected_tags = []

        if has_tag:
            expected_tags.append(ProcessorTag(raw_uid=expected_tag))

        assert tags == expected_tags
