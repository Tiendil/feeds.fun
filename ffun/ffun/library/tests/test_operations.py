
from itertools import chain

import pytest

from ffun.feeds import domain as f_domain
from ffun.feeds.tests import make as f_make
from ffun.library.operations import all_entries_iterator, catalog_entries
from ffun.library.tests import make


class TestAllEntriesIterator:

    @pytest.mark.parametrize('chunk', [1, 2, 3, 4, 5, 6, 7])
    @pytest.mark.asyncio
    async def test(self, chunk: int) -> None:
        feed_1_data = f_make.fake_feed()
        feed_1_id = await f_domain.save_feed(feed_1_data)

        feed_2_data = f_make.fake_feed()
        feed_2_id = await f_domain.save_feed(feed_2_data)

        entries_1_data = [make.fake_entry(feed_1_id) for _ in range(3)]
        entries_2_data = [make.fake_entry(feed_2_id) for _ in range(3)]

        await catalog_entries(entries_1_data)
        await catalog_entries(entries_2_data)

        ids = [(e.feed_id, e.id) for e in chain(entries_1_data, entries_2_data)]

        ids.sort()

        found_ids = [(entry.feed_id, entry.id)
                     async for entry in all_entries_iterator(chunk=chunk)
                     if (entry.feed_id, entry.id) in ids]

        assert found_ids == ids
