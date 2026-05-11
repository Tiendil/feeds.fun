import pytest

from ffun.dispatcher.entities import ProcessorRouteId
from ffun.domain.urls import str_to_absolute_url
from ffun.librarian.processors import domain
from ffun.librarian.processors.base import ProcessorContext
from ffun.library.entities import Entry
from ffun.ontology.entities import RawTag
from ffun.tags.entities import TagCategory


class TestDomainToParts:
    @pytest.mark.parametrize(
        "raw_domain, expected_parts",
        [
            ("example.com", ["example.com"]),
            ("www.example.com", ["example.com"]),
            ("blog.news.example.com", ["blog.news.example.com", "news.example.com", "example.com"]),
            ("com", []),
            ("", []),
        ],
    )
    def test_domain_parts(self, raw_domain: str, expected_parts: list[str]) -> None:
        assert domain.domain_to_parts(raw_domain) == expected_parts


class TestProcessor:
    @pytest.mark.asyncio
    async def test_process__empty_url(self, cataloged_entry: Entry) -> None:
        processor = domain.Processor(name="domain")
        entry = cataloged_entry.replace(external_url=None)

        assert await processor.process(entry, context=ProcessorContext(route_id=ProcessorRouteId("default"))) == []

    @pytest.mark.asyncio
    async def test_process__extracts_domain_tags(self, cataloged_entry: Entry) -> None:
        processor = domain.Processor(name="domain")
        entry = cataloged_entry.replace(external_url=str_to_absolute_url("https://blog.news.example.com/path"))

        assert await processor.process(entry, context=ProcessorContext(route_id=ProcessorRouteId("default"))) == [
            RawTag(
                raw_uid="blog.news.example.com",
                link="https://blog.news.example.com",
                categories={TagCategory.network_domain},
            ),
            RawTag(
                raw_uid="news.example.com",
                link="https://news.example.com",
                categories={TagCategory.network_domain},
            ),
            RawTag(
                raw_uid="example.com",
                link="https://example.com",
                categories={TagCategory.network_domain},
            ),
        ]
