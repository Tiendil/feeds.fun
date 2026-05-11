import pytest

from ffun.dispatcher.entities import ProcessorRouteId
from ffun.librarian.processors.base import ProcessorContext
from ffun.librarian.processors.native_tags import Processor
from ffun.library.entities import Entry
from ffun.ontology.entities import RawTag
from ffun.tags.entities import TagCategory


def raw_uid(tag: RawTag) -> str:
    return tag.raw_uid


class TestProcessor:
    @pytest.mark.asyncio
    async def test_process__no_external_tags(self, cataloged_entry: Entry) -> None:
        processor = Processor(name="native-tags")
        entry = cataloged_entry.replace(external_tags=set())

        assert await processor.process(entry, context=ProcessorContext(route_id=ProcessorRouteId("default"))) == []

    @pytest.mark.asyncio
    async def test_process__converts_external_tags(self, cataloged_entry: Entry) -> None:
        processor = Processor(name="native-tags")
        entry = cataloged_entry.replace(external_tags={"first", "second"})
        tags = await processor.process(entry, context=ProcessorContext(route_id=ProcessorRouteId("default")))

        assert sorted(tags, key=raw_uid) == [
            RawTag(raw_uid="first", categories={TagCategory.feed_tag}),
            RawTag(raw_uid="second", categories={TagCategory.feed_tag}),
        ]
