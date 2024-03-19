import datetime
import uuid
from itertools import chain
from typing import Iterable

import pytest
from ffun.core import utils
from ffun.core.postgresql import ExecuteType, execute, run_in_transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.librarian import errors, operations
from ffun.librarian.entities import ProcessorPointer
from ffun.library import operations as l_operations
from ffun.library.tests import make as l_make


async def clean_failed_storage(processor_ids: Iterable[int]) -> None:
    for processor_id in processor_ids:
        while True:
            failed_entries = await operations.get_failed_entries(execute, processor_id, limit=1000)
            await operations.remove_failed_entries(execute, processor_id, failed_entries)

            if not failed_entries:
                break
