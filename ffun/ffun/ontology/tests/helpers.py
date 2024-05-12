import datetime
import uuid
from itertools import chain
from typing import Iterable

import pytest
import pytest_asyncio
from ffun.core import utils
from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_times_is_near
from ffun.feeds import domain as f_domain
from ffun.feeds.tests import make as f_make
from ffun.library.domain import get_entry
from ffun.library.entities import Entry
from ffun.ontology.operations import (_get_relations_for_entry_and_tags, _register_relations_processors, _save_tags,
                                      apply_tags, get_tags_for_entries, remove_relations_for_entries)


async def assert_has_tags(tags_ids: dict[uuid.UUID, Iterable[int]]) -> None:
    tags = await get_tags_for_entries(execute, [entry_id for entry_id in tags_ids])

    for entry_id, tag_ids in tags_ids.items():
        assert tags.get(entry_id, set()) >= set(tag_ids)
