import asyncio
import uuid
import pathlib

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.meta import domain as m_domain

from ffun.librarian.processors.base import Processor
from ffun.librarian.processors.domain import Processor as DomainProcessor
from ffun.librarian.processors.native_tags import Processor as NativeTagsProcessor
from ffun.librarian.processors.openai_general import Processor as OpenGeneralProcessor
from ffun.librarian.processors.upper_case_title import Processor as UpperCaseTitleProcessor
from ffun.librarian.settings import settings as ln_settings
from ffun.processors_quality.knowlege_base import KnowlegeBase
from ffun.ontology import domain as o_domain

logger = logging.get_module_logger()

cli_app = typer.Typer()


_domain_processor = DomainProcessor(name="domain")
_native_tags_processor = NativeTagsProcessor(name="native_tags")
_openai_general_processor = OpenGeneralProcessor(name="openai_general", model=ln_settings.openai_general_processor.model)
_upper_case_title_processor = UpperCaseTitleProcessor(name="upper_case_title")


processors = {
    "domain": _domain_processor,
    "native_tags": _native_tags_processor,
    "openai_general": _openai_general_processor,
    "upper_case_title": _upper_case_title_processor,
}


async def run(processor_name: str, entry_id: int, knowlege_root: pathlib.Path) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        entry = kb.get_news_entry(entry_id)

        expected_tags = kb.get_expected_tags(processor_name, entry_id)

        processor = processors[processor_name]

        raw_tags = await processor.process(entry)

        raw_tags_to_uids = await o_domain.normalize_tags(raw_tags)

        tags = set(raw_tags_to_uids.values())

        must_tags = expected_tags.must_have & tags
        should_tags = expected_tags.should_have & tags

        print(f'must tags: {len(must_tags)}/{len(expected_tags.must_have)}')
        print(f'should tags: {len(should_tags)}/{len(expected_tags.should_have)}')

        print(f'all tags: {tags}')


@cli_app.command()
def test(processor: str, entry: int, knowlege_root: pathlib.Path = pathlib.Path('./tags_quality_base/')) -> None:
    asyncio.run(run(processor, entry, knowlege_root))
