from ffun.domain.entities import ProcessorId, TagId, TagUid
from ffun.ontology.entities import NormalizedTag, TagPropertyType
from ffun.tags.entities import TagCategory


class TestNormalizedTag:
    def test_build_properties_for__no_link(self) -> None:
        tag = NormalizedTag(uid=TagUid("tag"), link=None, categories={TagCategory.feed_tag})

        properties = tag.build_properties_for(tag_id=TagId(1), processor_id=ProcessorId(101))

        assert len(properties) == 1
        assert properties[0].tag_id == TagId(1)
        assert properties[0].type == TagPropertyType.categories
        assert properties[0].value == "feed-tag"
        assert properties[0].processor_id == ProcessorId(101)

    def test_build_properties_for__link_and_sorted_categories(self) -> None:
        tag = NormalizedTag(
            uid=TagUid("tag"),
            link="https://example.com",
            categories={TagCategory.network_domain, TagCategory.feed_tag},
        )

        properties = tag.build_properties_for(tag_id=TagId(1), processor_id=ProcessorId(101))

        assert len(properties) == 2
        assert properties[0].tag_id == TagId(1)
        assert properties[0].type == TagPropertyType.link
        assert properties[0].value == "https://example.com"
        assert properties[0].processor_id == ProcessorId(101)
        assert properties[1].tag_id == TagId(1)
        assert properties[1].type == TagPropertyType.categories
        assert properties[1].value == "feed-tag,network-domain"
        assert properties[1].processor_id == ProcessorId(101)
