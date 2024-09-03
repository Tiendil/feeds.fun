import sys

import tabulate

from ffun.core import utils
from ffun.librarian.background_processors import processors as ln_processors
from ffun.ontology import domain as o_domain
from ffun.processors_quality.entities import ProcessorResult, ProcessorResultDiff
from ffun.processors_quality.knowlege_base import KnowlegeBase, id_to_name

processors = {info.processor.name: info.processor for info in ln_processors}


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

        diff = ProcessorResultDiff(
            entry_id=entry_id,
            must_have_total=len(expected.must_have),
            should_have_total=len(expected.should_have),
            actual_total=len(actual_tags),
            actual_must_have_found=len(expected.must_have & actual_tags),
            actual_must_have_missing=list(expected.must_have - actual_tags),
            actual_should_have_found=len(expected.should_have & actual_tags),
            actual_has_and_last_not=list(actual_tags - last_tags),
            last_total=len(last_tags),
            last_must_have_found=len(expected.must_have & last_tags),
            last_must_have_missing=list(expected.must_have - last_tags),
            last_should_have_found=len(expected.should_have & last_tags),
            last_has_and_actual_not=list(last_tags - actual_tags),
        )

        diffs.append(diff)

    return diffs


def display_diffs(diffs: list[ProcessorResultDiff], show_tag_diffs: bool) -> None:  # noqa: CCR001
    table = []

    if not show_tag_diffs:
        headers = ["entry id", "total", "must have", "should have", "should have %"]
    else:
        headers = [
            "entry id",
            "total",
            "must have",
            "should have",
            "should have %",
            "actual has and last not",
            "last has and actual not",
        ]

    missing_must_have = 0

    should_diffs = []
    total_diffs = []

    for diff in diffs:

        if diff.actual_must_have_found != diff.must_have_total:
            raise NotImplementedError(
                f'Currently we expect that actual will always have "must" tags, tags: {diff.actual_must_have_missing}'
            )  # noqa: E501

        if diff.actual_must_have_found == diff.last_must_have_found:
            must_have = "ok"
        elif diff.actual_must_have_found > diff.last_must_have_found:
            must_have = ", ".join(f"?{tag}" for tag in diff.last_must_have_missing)
            missing_must_have += 1
        else:
            raise NotImplementedError("We should not reach this point")

        should_delta = diff.last_should_have_found - diff.actual_should_have_found

        should_have = f"{should_delta:+} / {diff.should_have_total}"

        if diff.should_have_total == 0:
            should_diff = 0.0
        else:
            should_diff = should_delta / diff.should_have_total

        should_diffs.append(should_diff)

        should_have_percent = f"{should_diff:+.2%}"

        if diff.actual_total == 0:
            total_fraction = 1.0
        else:
            total_fraction = diff.last_total / diff.actual_total - 1

        total = f"{diff.actual_total} vs {diff.last_total} [{total_fraction:+.2%}]"

        total_diffs.append(total_fraction)

        row = [id_to_name(diff.entry_id), total, must_have, should_have, should_have_percent]

        if show_tag_diffs:
            actual_has_and_last_not = "\n".join(diff.actual_has_and_last_not)
            last_has_and_actual_not = "\n".join(diff.last_has_and_actual_not)
            row.extend([actual_has_and_last_not, last_has_and_actual_not])

        table.append(row)

    sys.stdout.write("\n")
    sys.stdout.write(tabulate.tabulate(table, headers=headers, tablefmt="grid"))
    sys.stdout.write("\n")
    sys.stdout.write("\n")

    if missing_must_have:
        sys.stdout.write(f"ERROR: entries with m must have tags: {missing_must_have}\n\n")

    # should diffs
    should_diffs = list(sorted(should_diffs))

    sys.stdout.write("should diffs:\n")

    should_median = should_diffs[len(should_diffs) // 2]

    sys.stdout.write(f"worst: {should_diffs[0]:.2%}, median: {should_median:.2%}, best: {should_diffs[-1]:.2%}\n")

    should_diff_average = sum(should_diffs) / len(should_diffs)

    sys.stdout.write(f"average: {should_diff_average:.2%}\n\n")

    # total diffs
    total_diffs = list(sorted(total_diffs))

    sys.stdout.write("total diffs:\n")

    sys.stdout.write(
        f"worst: {total_diffs[0]:.2%}, median: {total_diffs[len(total_diffs) // 2]:.2%}, best: {total_diffs[-1]:.2%}\n"
    )

    total_diff_average = sum(total_diffs) / len(total_diffs)

    sys.stdout.write(f"average: {total_diff_average:.2%}\n\n")
