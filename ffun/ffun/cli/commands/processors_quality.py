import asyncio
import uuid
import pathlib

from ffun.application.application import with_app
from ffun.cli.application import app
from ffun.core import logging
from ffun.meta import domain as m_domain

from ffun.librarian.processors.base import Processor
from ffun.librarian.processors.domain import Processor as DomainProcessor
from ffun.librarian.processors.native_tags import Processor as NativeTagsProcessor
from ffun.librarian.processors.openai_general import Processor as OpenGeneralProcessor
from ffun.librarian.processors.upper_case_title import Processor as UpperCaseTitleProcessor
from ffun.librarian.settings import settings as ln_settings
from ffun.processors_quality.knowlege_base import KnowlegeBase

logger = logging.get_module_logger()


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


async def run(processor_name: str, test: int, knowlege_root: pathlib.Path) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        entry = kb.get_news_entry(processor_name)

        expected_tags = kb.get_expected_tags(processor_name, test)

        processor = processors[processor_name]

        raw_tags_to_uids = await processor.process(entry)

        tags = set(raw_tags_to_uids.values())

        correct_tags = expected_tags & tags

        print(f'tags: {len(correct_tags)}/{len(expected_tags)}')


@app.command()
def test(processor: str, test: int, knowlege_root: pathlib.Path) -> None:
    asyncio.run(run(processor, test, knowlege_root))
