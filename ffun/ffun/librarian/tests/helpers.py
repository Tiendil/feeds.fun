from typing import Iterable

from ffun.core.postgresql import execute
from ffun.librarian import operations


async def clean_failed_storage(processor_ids: Iterable[int]) -> None:
    for processor_id in processor_ids:
        while True:
            failed_entries = await operations.get_failed_entries(execute, processor_id, limit=1000)
            await operations.remove_failed_entries(execute, processor_id, failed_entries)

            if not failed_entries:
                break
