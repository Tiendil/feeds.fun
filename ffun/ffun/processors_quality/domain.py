from ffun.core import utils
from ffun.librarian.processors.base import Processor
from ffun.processors_quality.knowlege_base import KnowlegeBase
from ffun.librarian.processors.domain import Processor as DomainProcessor
from ffun.librarian.processors.native_tags import Processor as NativeTagsProcessor
from ffun.librarian.processors.openai_general import Processor as OpenGeneralProcessor
from ffun.librarian.processors.upper_case_title import Processor as UpperCaseTitleProcessor
from ffun.librarian.settings import settings as ln_settings
from ffun.processors_quality.entities import ProcessorResult
from ffun.ontology import domain as o_domain


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


async def run_processor(kb: KnowlegeBase, processor_name: str, entry_id: int) -> ProcessorResult:

    entry = kb.get_news_entry(entry_id)

    expected_tags = kb.get_expected_tags(processor_name, entry_id)

    processor = processors[processor_name]

    raw_tags = await processor.process(entry)

    raw_tags_to_uids = await o_domain.normalize_tags(raw_tags)

    tags = set(raw_tags_to_uids.values())

    must_tags_found = expected_tags.must_have & tags
    should_tags_found = expected_tags.should_have & tags

    result = ProcessorResult(
        tags=list(sorted(tags)),

        must_tags_found=list(sorted(must_tags_found)),
        must_tags_missing=list(sorted(expected_tags.must_have - must_tags_found)),

        should_tags_found=list(sorted(should_tags_found)),
        should_tags_missing=list(sorted(expected_tags.should_have - should_tags_found)),

        created_at=utils.now(),
    )

    return result
