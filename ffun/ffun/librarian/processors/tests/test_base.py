import pytest

from ffun.dispatcher.entities import ProcessorRouteId
from ffun.librarian import errors
from ffun.librarian.processors.base import (
    AlwaysConstantProcessor,
    AlwaysErrorProcessor,
    AlwaysSkipEntryProcessor,
    AlwaysTemporaryErrorProcessor,
    Processor,
    ProcessorContext,
)
from ffun.library.entities import Entry
from ffun.ontology.entities import RawTag
from ffun.tags.entities import TagCategory


class TestProcessor:
    @pytest.mark.asyncio
    async def test_process__is_not_implemented(self, cataloged_entry: Entry) -> None:
        processor = Processor(name="test-processor")

        with pytest.raises(NotImplementedError):
            await processor.process(cataloged_entry, context=ProcessorContext(route_id=ProcessorRouteId("default")))


class TestAlwaysConstantProcessor:
    @pytest.mark.asyncio
    async def test_process__returns_configured_tags(self, cataloged_entry: Entry) -> None:
        processor = AlwaysConstantProcessor(name="test-processor", tags=["first", "second"])

        assert await processor.process(
            cataloged_entry, context=ProcessorContext(route_id=ProcessorRouteId("default"))
        ) == [
            RawTag(raw_uid="first", categories={TagCategory.test_final}),
            RawTag(raw_uid="second", categories={TagCategory.test_final}),
        ]


class TestAlwaysSkipEntryProcessor:
    @pytest.mark.asyncio
    async def test_process__raises_skip_error(self, cataloged_entry: Entry) -> None:
        processor = AlwaysSkipEntryProcessor(name="test-processor")

        with pytest.raises(errors.SkipEntryProcessing):
            await processor.process(cataloged_entry, context=ProcessorContext(route_id=ProcessorRouteId("default")))


class TestAlwaysErrorProcessor:
    @pytest.mark.asyncio
    async def test_process__raises_custom_error(self, cataloged_entry: Entry) -> None:
        processor = AlwaysErrorProcessor(name="test-processor")

        with pytest.raises(AlwaysErrorProcessor.CustomError):
            await processor.process(cataloged_entry, context=ProcessorContext(route_id=ProcessorRouteId("default")))


class TestAlwaysTemporaryErrorProcessor:
    @pytest.mark.asyncio
    async def test_process__raises_temporary_error(self, cataloged_entry: Entry) -> None:
        processor = AlwaysTemporaryErrorProcessor(name="test-processor")

        with pytest.raises(errors.TemporaryErrorInProcessor):
            await processor.process(cataloged_entry, context=ProcessorContext(route_id=ProcessorRouteId("default")))
