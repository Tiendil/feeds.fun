import datetime
import uuid
from itertools import chain

import pytest
import pytest_asyncio
from ffun.core import utils
from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_times_is_near
from ffun.feeds import domain as f_domain
from ffun.feeds.tests import make as f_make
from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.library.tests import make as l_make
from ffun.meta.domain import remove_feed
from ffun.ontology import domain as o_domain
from ffun.ontology.entities import ProcessorTag


class TestRemoveFeed:

    @pytest.mark.asyncio
    async def test_no_feed(self) -> None:
        await remove_feed(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_success(self,
                           loaded_feed_id: uuid.UUID,
                           another_loaded_feed_id: uuid.UUID,
                           fake_processor_id: int,
                           another_fake_processor_id: int,
                           three_processor_tags: tuple[ProcessorTag, ProcessorTag, ProcessorTag]) -> None:
        entries = await l_make.n_entries_list(loaded_feed_id, 3)
        another_entries = await l_make.n_entries_list(another_loaded_feed_id, 3)

        tag_a, tag_b, tag_c = three_processor_tags

        # fill feed 1
        await o_domain.apply_tags_to_entry(entry_id=entries[0].id,
                                           processor_id=fake_processor_id,
                                           tags=[tag_a])

        await o_domain.apply_tags_to_entry(entry_id=entries[1].id,
                                           processor_id=fake_processor_id,
                                           tags=[tag_a])

        await o_domain.apply_tags_to_entry(entry_id=entries[1].id,
                                           processor_id=another_fake_processor_id,
                                           tags=[tag_b])

        # fill feed 2
        await o_domain.apply_tags_to_entry(entry_id=another_entries[1].id,
                                           processor_id=fake_processor_id,
                                           tags=[tag_a])

        await o_domain.apply_tags_to_entry(entry_id=another_entries[1].id,
                                           processor_id=another_fake_processor_id,
                                           tags=[tag_b])

        await o_domain.apply_tags_to_entry(entry_id=another_entries[2].id,
                                           processor_id=another_fake_processor_id,
                                           tags=[tag_c])

        await remove_feed(loaded_feed_id)

        loaded_entries = await l_domain.get_entries_by_ids([entry.id for entry in entries] +
                                                           [entry.id for entry in another_entries])

        assert loaded_entries == {entries[0].id: None,
                                  entries[1].id: None,
                                  entries[2].id: None,
                                  another_entries[0].id: another_entries[0],
                                  another_entries[1].id: another_entries[1],
                                  another_entries[2].id: another_entries[2]}
