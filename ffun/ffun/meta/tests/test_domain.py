import uuid
from itertools import chain

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from ffun.core import utils
from ffun.core.postgresql import execute
from ffun.domain.entities import TagId, TagUid, UserId
from ffun.domain.urls import str_to_feed_url, url_to_source_uid, url_to_uid
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed
from ffun.feeds.tests import make as f_make
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library.tests import make as l_make
from ffun.meta.domain import (
    _apply_renormalized_tags,
    _normalize_tag_uid,
    _renormalize_tag,
    add_feeds,
    clean_orphaned_entries,
    clean_orphaned_feeds,
    clean_orphaned_tags,
    remove_entries,
    remove_tags,
    renormalize_tags,
)
from ffun.ontology import domain as o_domain
from ffun.ontology.entities import NormalizedTag, RawTag, TagProperty, TagPropertyType
from ffun.parsers import entities as p_entities
from ffun.tags.entities import TagCategory


class TestRemoveEntries:
    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        await remove_entries([])

    @pytest.mark.asyncio
    async def test_success(
        self,
        loaded_feed: Feed,
        another_loaded_feed: Feed,
        fake_processor_id: int,
        another_fake_processor_id: int,
        three_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag],
    ) -> None:
        entries = await l_make.n_entries_list(loaded_feed, 3)
        another_entries = await l_make.n_entries_list(another_loaded_feed, 3)

        tag_a, tag_b, tag_c = three_processor_tags

        # fill feed 1
        await o_domain.apply_tags_to_entry(entry_id=entries[0].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(entry_id=entries[1].id, processor_id=fake_processor_id, tags=[tag_a])

        await o_domain.apply_tags_to_entry(
            entry_id=entries[1].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        # fill feed 2
        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[1].id, processor_id=fake_processor_id, tags=[tag_a]
        )

        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[1].id, processor_id=another_fake_processor_id, tags=[tag_b]
        )

        await o_domain.apply_tags_to_entry(
            entry_id=another_entries[2].id, processor_id=another_fake_processor_id, tags=[tag_c]
        )

        await remove_entries([entries[0].id, another_entries[1].id, entries[2].id])

        loaded_entries = await l_domain.get_entries_by_ids(
            [entry.id for entry in entries] + [entry.id for entry in another_entries]
        )

        assert loaded_entries == {
            entries[0].id: None,
            entries[1].id: entries[1],
            entries[2].id: None,
            another_entries[0].id: another_entries[0],
            another_entries[1].id: None,
            another_entries[2].id: another_entries[2],
        }


class TestAddFeeds:

    @pytest.mark.asyncio
    async def test_no_feeds_to_add(self, internal_user_id: UserId) -> None:
        await add_feeds([], internal_user_id)

    @pytest.mark.asyncio
    async def test_add(self, internal_user_id: UserId, another_internal_user_id: UserId) -> None:

        urls = [str_to_feed_url(f"{uuid.uuid4().hex}.com") for _ in range(3)]

        feeds = [
            p_entities.FeedInfo(
                url=urls[0],
                title=uuid.uuid4().hex,
                description=uuid.uuid4().hex,
                entries=[],
                uid=url_to_uid(urls[0]),
            ),
            p_entities.FeedInfo(
                url=urls[1],
                title=uuid.uuid4().hex,
                description=uuid.uuid4().hex,
                entries=[],
                uid=url_to_uid(urls[1]),
            ),
            p_entities.FeedInfo(
                url=urls[2], title=uuid.uuid4().hex, description=uuid.uuid4().hex, entries=[], uid=url_to_uid(urls[2])
            ),
        ]

        await add_feeds(feeds[:2], internal_user_id)
        await add_feeds(feeds[1:], another_internal_user_id)

        links_1 = await fl_domain.get_linked_feeds(internal_user_id)
        links_2 = await fl_domain.get_linked_feeds(another_internal_user_id)

        feeds_1 = await f_domain.get_feeds([link.feed_id for link in links_1])
        feeds_2 = await f_domain.get_feeds([link.feed_id for link in links_2])

        assert len({feed.id for feed in feeds_1} & {feed.id for feed in feeds_2}) == 1

        assert {feed.url for feed in feeds_1} == {feed.url for feed in feeds[:2]}
        assert {feed.url for feed in feeds_2} == {feed.url for feed in feeds[1:]}

        source_uids = {url: url_to_source_uid(url) for url in urls}
        source_ids = await f_domain.get_source_ids(source_uids.values())

        for feed in chain(feeds_1, feeds_2):
            assert feed.source_id == source_ids[source_uids[feed.url]]


# test that everything is connected correctly
# detailed cases are covered in tests of functions called in clean_orphaned_entries
class TestCleanOrphanedEntries:

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_orphaned_entries(self) -> None:
        await execute("DELETE FROM l_orphaned_entries")

    @pytest.mark.asyncio
    async def test(self, loaded_feed: Feed) -> None:
        entries = await l_make.n_entries_list(loaded_feed, n=10)

        await l_domain.unlink_feed_tail(loaded_feed.id, offset=3)

        removed_1 = await clean_orphaned_entries(chunk=5)

        assert removed_1 == 5

        removed_2 = await clean_orphaned_entries(chunk=5)

        assert removed_2 == 2

        loaded_entries = await l_domain.get_entries_by_ids([entry.id for entry in entries])

        assert loaded_entries == {entry.id: entry for entry in entries[:3]} | {entry.id: None for entry in entries[3:]}


# test that everything is connected correctly
# detailed cases are covered in tests of functions called in clean_orphaned_entries
class TestCleanOrphanedFeeds:

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_orphaned_feeds(self) -> None:
        orphanes = await f_domain.get_orphaned_feeds(limit=10000, loaded_before=utils.now())

        for orphane_id in orphanes:
            await f_domain.tech_remove_feed(orphane_id)

    @pytest.mark.asyncio
    async def test_chunks(self) -> None:
        feeds = await f_make.n_feeds(10)

        for feed in feeds:
            await f_domain.mark_feed_as_orphaned(feed.id)

        assert await clean_orphaned_feeds(chunk=3) == 3
        assert await clean_orphaned_feeds(chunk=4) == 4
        assert await clean_orphaned_feeds(chunk=5) == 3

    @pytest.mark.asyncio
    async def test_all_logic_called(self, mocker: MockerFixture) -> None:
        feeds = await f_make.n_feeds(3)

        feeds.sort(key=lambda feed: feed.id)

        for feed in feeds:
            await f_domain.mark_feed_as_orphaned(feed.id)

        unlink_feed_tail_mock = mocker.patch("ffun.library.domain.unlink_feed_tail")
        tech_remove_feed_mock = mocker.patch("ffun.feeds.domain.tech_remove_feed")
        tech_remove_all_links = mocker.patch("ffun.feeds_links.domain.tech_remove_all_links")

        assert await clean_orphaned_feeds(chunk=100) == 3

        assert unlink_feed_tail_mock.call_args_list == [mocker.call(feed.id, offset=0) for feed in feeds]

        assert tech_remove_feed_mock.call_args_list == [mocker.call(feed.id) for feed in feeds]

        assert tech_remove_all_links.call_args_list == [mocker.call([feed.id for feed in feeds])]


# test that everything is connected correctly
# detailed cases are covered in tests of functions called in clean_orphaned_tags
class TestCleanOrphanedTags:

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_orphaned_tags(self) -> None:
        while await clean_orphaned_tags(chunk=10000):
            pass

    @pytest.mark.asyncio
    async def test_chunks(
        self, five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId]
    ) -> None:  # pylint: disable=W0613
        assert await clean_orphaned_tags(chunk=2) == 2
        assert await clean_orphaned_feeds(chunk=1) == 1
        assert await clean_orphaned_feeds(chunk=5) == 2

    @pytest.mark.asyncio
    async def test_all_logic_called(self, mocker: MockerFixture) -> None:
        protected_tags = [1, 3, 5]

        get_all_tags_in_rules_mock = mocker.patch(
            "ffun.scores.domain.get_all_tags_in_rules", return_value=protected_tags
        )
        remove_orphaned_tags_mock = mocker.patch("ffun.ontology.domain.remove_orphaned_tags", return_value=7)

        assert await clean_orphaned_tags(chunk=100) == 7

        assert get_all_tags_in_rules_mock.call_args_list == [mocker.call()]
        assert remove_orphaned_tags_mock.call_args_list == [mocker.call(chunk=100, protected_tags=protected_tags)]


# test that everything is connected correctly
class TestRemoveTags:

    @pytest.mark.asyncio
    async def test_no_tags(self) -> None:
        await remove_tags([])

    @pytest.mark.asyncio
    async def test(self, mocker: MockerFixture, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:
        remove_relations_for_tags = mocker.patch("ffun.ontology.domain.remove_relations_for_tags")
        remove_rules_with_tags = mocker.patch("ffun.scores.domain.remove_rules_with_tags")

        await remove_tags(list(three_tags_ids))

        assert remove_relations_for_tags.call_args_list == [mocker.call(list(three_tags_ids))]
        assert remove_rules_with_tags.call_args_list == [mocker.call(list(three_tags_ids))]


# test that everything is connected correctly
class TestApplyRenormalizedTags:

    @pytest.mark.asyncio
    async def test_no_changes(self, fake_processor_id: int, three_tags_ids: tuple[TagId, TagId, TagId]) -> None:
        await _apply_renormalized_tags(
            processor_id=fake_processor_id, old_tag_id=three_tags_ids[0], new_tag_id=three_tags_ids[1]
        )

    @pytest.mark.asyncio
    async def test(
        self, mocker: MockerFixture, fake_processor_id: int, three_tags_ids: tuple[TagId, TagId, TagId]
    ) -> None:
        copy_tag_properties = mocker.patch("ffun.ontology.domain.copy_tag_properties")
        copy_relations = mocker.patch("ffun.ontology.domain.copy_relations")
        clone_rules_for_replacements = mocker.patch("ffun.scores.domain.clone_rules_for_replacements")

        await _apply_renormalized_tags(
            processor_id=fake_processor_id, old_tag_id=three_tags_ids[0], new_tag_id=three_tags_ids[1]
        )

        assert copy_tag_properties.call_args_list == [
            mocker.call(processor_id=fake_processor_id, old_tag_id=three_tags_ids[0], new_tag_id=three_tags_ids[1])
        ]
        assert copy_relations.call_args_list == [
            mocker.call(processor_id=fake_processor_id, old_tag_id=three_tags_ids[0], new_tag_id=three_tags_ids[1])
        ]
        assert clone_rules_for_replacements.call_args_list == [mocker.call({three_tags_ids[0]: three_tags_ids[1]})]


class TestNormalizeTagUid:

    @pytest.mark.asyncio
    async def test_no_categories(self, fake_processor_id: int) -> None:
        assert await _normalize_tag_uid(
            old_tag_uid=TagUid("some-test-tag"), categories=set(), processor_id=fake_processor_id
        ) == (False, [])

    @pytest.mark.asyncio
    async def test_no_norm_forms(self, mocker: MockerFixture, fake_processor_id: int) -> None:
        normalize = mocker.patch("ffun.tags.domain.normalize", return_value=[])

        categories = {TagCategory.test_raw, TagCategory.test_final}

        old_tag_uid = TagUid("some-test-tag")

        assert await _normalize_tag_uid(
            old_tag_uid=old_tag_uid, categories=categories, processor_id=fake_processor_id
        ) == (False, [])

        assert normalize.call_args_list == [
            mocker.call([RawTag(raw_uid=old_tag_uid, link=None, categories=categories)])
        ]

    @pytest.mark.asyncio
    async def test_normalized__no_original_form(self, mocker: MockerFixture, fake_processor_id: int) -> None:
        norm_tag_1 = NormalizedTag(
            uid=TagUid("norm-tag-1"), link=None, categories={TagCategory.test_final, TagCategory.test_preserve}
        )
        norm_tag_2 = NormalizedTag(uid=TagUid("norm-tag-2"), link=None, categories={TagCategory.test_raw})

        old_tag_uid = TagUid("some-test-tag")

        uids_to_ids = await o_domain.get_ids_by_uids(
            [old_tag_uid, norm_tag_1.uid, norm_tag_2.uid]  # make sure tags exist in the database
        )

        normalize = mocker.patch("ffun.tags.domain.normalize", return_value=[norm_tag_1, norm_tag_2])

        categories = {TagCategory.test_raw, TagCategory.test_final}

        (keep_old_tag, new_tags) = await _normalize_tag_uid(
            old_tag_uid=old_tag_uid, categories=categories, processor_id=fake_processor_id
        )

        assert not keep_old_tag
        assert set(new_tags) == {uids_to_ids[norm_tag_1.uid], uids_to_ids[norm_tag_2.uid]}

        assert normalize.call_args_list == [
            mocker.call([RawTag(raw_uid=old_tag_uid, link=None, categories=categories)])
        ]

        properties = await o_domain.get_tags_properties([uids_to_ids[norm_tag_1.uid], uids_to_ids[norm_tag_2.uid]])
        properties = [property for property in properties if property.processor_id == fake_processor_id]
        assert len(properties) == 2
        assert all(property.type == TagPropertyType.categories for property in properties)

        tag_1_property = [property for property in properties if property.tag_id == uids_to_ids[norm_tag_1.uid]][0]
        tag_2_property = [property for property in properties if property.tag_id == uids_to_ids[norm_tag_2.uid]][0]

        assert tag_1_property.value == ",".join(sorted(category.value for category in norm_tag_1.categories))
        assert tag_2_property.value == ",".join(sorted(category.value for category in norm_tag_2.categories))

    @pytest.mark.asyncio
    async def test_normalized__keep_original_form(self, mocker: MockerFixture, fake_processor_id: int) -> None:
        norm_tag_1 = NormalizedTag(uid=TagUid("norm-tag-1"), link=None, categories={TagCategory.test_final})
        norm_tag_2 = NormalizedTag(
            uid=TagUid("norm-tag-2"), link=None, categories={TagCategory.test_raw, TagCategory.test_preserve}
        )
        norm_tag_3 = NormalizedTag(uid=TagUid("norm-tag-3"), link=None, categories={TagCategory.test_raw})

        uids_to_ids = await o_domain.get_ids_by_uids(
            [norm_tag_1.uid, norm_tag_2.uid, norm_tag_3.uid]  # make sure tags exist in the database
        )

        normalize = mocker.patch("ffun.tags.domain.normalize", return_value=[norm_tag_1, norm_tag_2, norm_tag_3])

        categories = {TagCategory.test_raw, TagCategory.test_final}

        (keep_old_tag, new_tags) = await _normalize_tag_uid(
            old_tag_uid=norm_tag_2.uid, categories=categories, processor_id=fake_processor_id
        )

        assert keep_old_tag
        assert set(new_tags) == {uids_to_ids[norm_tag_1.uid], uids_to_ids[norm_tag_3.uid]}

        assert normalize.call_args_list == [
            mocker.call([RawTag(raw_uid=norm_tag_2.uid, link=None, categories=categories)])
        ]

        properties = await o_domain.get_tags_properties(list(uids_to_ids.values()))
        properties = [property for property in properties if property.processor_id == fake_processor_id]
        assert len(properties) == 3
        assert all(property.type == TagPropertyType.categories for property in properties)

        tag_1_property = [property for property in properties if property.tag_id == uids_to_ids[norm_tag_1.uid]][0]
        tag_2_property = [property for property in properties if property.tag_id == uids_to_ids[norm_tag_2.uid]][0]
        tag_3_property = [property for property in properties if property.tag_id == uids_to_ids[norm_tag_3.uid]][0]

        assert tag_1_property.value == ",".join(sorted(category.value for category in norm_tag_1.categories))
        assert tag_2_property.value == ",".join(sorted(category.value for category in norm_tag_2.categories))
        assert tag_3_property.value == ",".join(sorted(category.value for category in norm_tag_3.categories))


# test that everything is connected correctly
class TestRenormalizeTag:

    @pytest.mark.asyncio
    async def test_no_removing(
        self,
        fake_processor_id: int,
        three_tags_ids: tuple[TagId, TagId, TagId],
        three_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag],
        mocker: MockerFixture,
    ) -> None:

        normalize_tag_uid = mocker.patch(
            "ffun.meta.domain._normalize_tag_uid", return_value=(True, [three_tags_ids[1], three_tags_ids[2]])
        )
        apply_renormalized_tags = mocker.patch("ffun.meta.domain._apply_renormalized_tags")
        remove_tags = mocker.patch("ffun.meta.domain.remove_tags")

        categories = {TagCategory.test_raw, TagCategory.test_final}

        await _renormalize_tag(
            processor_id=fake_processor_id,
            old_tag_id=three_tags_ids[0],
            old_tag_uid=three_processor_tags[0].uid,
            categories=categories,
        )

        assert normalize_tag_uid.call_args_list == [
            mocker.call(old_tag_uid=three_processor_tags[0].uid, categories=categories, processor_id=fake_processor_id)
        ]
        assert apply_renormalized_tags.call_args_list == [
            mocker.call(processor_id=fake_processor_id, old_tag_id=three_tags_ids[0], new_tag_id=three_tags_ids[1]),
            mocker.call(processor_id=fake_processor_id, old_tag_id=three_tags_ids[0], new_tag_id=three_tags_ids[2]),
        ]
        assert remove_tags.call_args_list == []

    @pytest.mark.asyncio
    async def test_removing(
        self,
        fake_processor_id: int,
        three_tags_ids: tuple[TagId, TagId, TagId],
        three_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag],
        mocker: MockerFixture,
    ) -> None:

        normalize_tag_uid = mocker.patch(
            "ffun.meta.domain._normalize_tag_uid", return_value=(False, [three_tags_ids[1], three_tags_ids[2]])
        )
        apply_renormalized_tags = mocker.patch("ffun.meta.domain._apply_renormalized_tags")
        remove_tags = mocker.patch("ffun.meta.domain.remove_tags")

        categories = {TagCategory.test_raw, TagCategory.test_final}

        await _renormalize_tag(
            processor_id=fake_processor_id,
            old_tag_id=three_tags_ids[0],
            old_tag_uid=three_processor_tags[0].uid,
            categories=categories,
        )

        assert normalize_tag_uid.call_args_list == [
            mocker.call(old_tag_uid=three_processor_tags[0].uid, categories=categories, processor_id=fake_processor_id)
        ]
        assert apply_renormalized_tags.call_args_list == [
            mocker.call(processor_id=fake_processor_id, old_tag_id=three_tags_ids[0], new_tag_id=three_tags_ids[1]),
            mocker.call(processor_id=fake_processor_id, old_tag_id=three_tags_ids[0], new_tag_id=three_tags_ids[2]),
        ]
        assert remove_tags.call_args_list == [mocker.call([three_tags_ids[0]])]


# test that everything is connected correctly
class TestRenormalizeTags:

    @pytest.mark.asyncio
    async def test_no_tags(self) -> None:
        await renormalize_tags(tag_ids=[])

    @pytest.mark.asyncio
    async def test(
        self,
        mocker: MockerFixture,
        five_tags_ids: tuple[TagId, TagId, TagId, TagId, TagId],
        five_processor_tags: tuple[NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag, NormalizedTag],
        fake_processor_id: int,
        another_fake_processor_id: int,
    ) -> None:

        tag_ids = five_tags_ids
        tag_uids = [tag.uid for tag in five_processor_tags]

        properties = [
            TagProperty(
                tag_id=tag_ids[0],
                type=TagPropertyType.categories,
                value=TagCategory.test_raw.value,
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[1],
                type=TagPropertyType.categories,
                value=",".join([TagCategory.test_raw.value, TagCategory.test_final.value]),
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[1],
                type=TagPropertyType.categories,
                value=TagCategory.special.value,
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[2],
                type=TagPropertyType.categories,
                value=TagCategory.test_final.value,
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[2],
                type=TagPropertyType.link,
                value="some-link",  # should be skipped
                processor_id=fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[3],
                type=TagPropertyType.link,
                value="some-link",  # should be skipped
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
            TagProperty(
                tag_id=tag_ids[4],
                type=TagPropertyType.categories,
                value=TagCategory.test_raw.value,
                processor_id=another_fake_processor_id,
                created_at=utils.now(),
            ),
        ]

        await o_domain.apply_tags_properties(properties)

        renormalize_tag = mocker.patch("ffun.meta.domain._renormalize_tag")

        await renormalize_tags([tag_ids[0], tag_ids[1], tag_ids[2], tag_ids[3]])

        call_list = [
            (
                call.kwargs["old_tag_id"],
                call.kwargs["old_tag_uid"],
                call.kwargs["processor_id"],
                frozenset(call.kwargs["categories"]),
            )
            for call in renormalize_tag.call_args_list
        ]
        call_list.sort()

        assert call_list == [
            (tag_ids[0], tag_uids[0], fake_processor_id, frozenset({TagCategory.test_raw.value})),
            (
                tag_ids[1],
                tag_uids[1],
                fake_processor_id,
                frozenset({TagCategory.test_raw.value, TagCategory.test_final.value}),
            ),
            (tag_ids[1], tag_uids[1], another_fake_processor_id, frozenset({TagCategory.special.value})),
            (tag_ids[2], tag_uids[2], another_fake_processor_id, frozenset({TagCategory.test_final.value})),
        ]
