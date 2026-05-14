from collections.abc import Iterable

from ffun.library.entities import Reference


def merge_references_list(references: Iterable[Reference | None]) -> list[Reference]:
    merged_references: dict[str, Reference] = {}

    for reference in references:
        if reference is None:
            continue

        existing_reference = merged_references.get(reference.url)

        if existing_reference is None:
            merged_references[reference.url] = reference
            continue

        merged_references[reference.url] = existing_reference.merge(reference)

    return [merged_references[url] for url in sorted(merged_references)]
