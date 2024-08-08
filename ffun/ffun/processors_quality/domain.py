from ffun.core import utils
from ffun.librarian.processors.domain import Processor as DomainProcessor
from ffun.librarian.processors.native_tags import Processor as NativeTagsProcessor
from ffun.librarian.processors.openai_general import Processor as OpenGeneralProcessor
from ffun.librarian.processors.upper_case_title import Processor as UpperCaseTitleProcessor
from ffun.librarian.settings import settings as ln_settings
from ffun.ontology import domain as o_domain
from ffun.processors_quality.entities import ProcessorResult, ProcessorResultDiff
from ffun.processors_quality.knowlege_base import KnowlegeBase

_domain_processor = DomainProcessor(name="domain")
_native_tags_processor = NativeTagsProcessor(name="native_tags")
_openai_general_processor = OpenGeneralProcessor(
    name="openai_general", model=ln_settings.openai_general_processor.model
)
_upper_case_title_processor = UpperCaseTitleProcessor(name="upper_case_title")


processors = {
    "domain": _domain_processor,
    "native_tags": _native_tags_processor,
    "openai_general": _openai_general_processor,
    "upper_case_title": _upper_case_title_processor,
}


async def run_processor(kb: KnowlegeBase, processor_name: str, entry_id: int) -> ProcessorResult:

    entry = kb.get_news_entry(entry_id)

    processor = processors[processor_name]

    raw_tags = await processor.process(entry)

    raw_tags_to_uids = await o_domain.normalize_tags(raw_tags)

    tags = set(raw_tags_to_uids.values())

    result = ProcessorResult(
        tags=list(sorted(tags)),
        created_at=utils.now(),
    )

    return result


def diff_processor_results(kb: KnowlegeBase, processor_name: str, entry_ids: list[int]) -> list[ProcessorResultDiff]:

    diffs: list[ProcessorResultDiff] = []

    for entry_id in sorted(entry_ids):
        expected = kb.get_expected_tags(processor_name, entry_id)
        actual = kb.get_actual_results(processor_name, entry_id)
        last = kb.get_last_results(processor_name, entry_id)

        actual_tags = set(actual.tags)
        last_tags = set(last.tags)

        diff = ProcessorResultDiff(entry_id=entry_id,
                                   must_have_total=len(expected.must_have),
                                   should_have_total=len(expected.should_have),

                                   actual_must_have_found=len(expected.must_have & actual_tags),
                                   actual_must_have_missing=list(expected.must_have - actual_tags),
                                   actual_should_have_found=len(expected.should_have & actual_tags),

                                   last_must_have_found=len(expected.must_have & last_tags),
                                   last_must_have_missing=list(expected.must_have - last_tags),
                                   last_should_have_found=len(expected.should_have & last_tags))

        diffs.append(diff)

    return diffs
