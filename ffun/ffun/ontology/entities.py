import enum

import pydantic


class TagPropertyType(int, enum.Enum):
    tag_name = 1  # "name" is reserved
    link = 2
    category = 3


class TagCategory(str, enum.Enum):
    network_domain = "network-domain"
    feed_tag = "feed-tag"


class TagProperty(pydantic.BaseModel):
    tag_id: int
    type: TagPropertyType
    value: str


class ProcessorTag(pydantic.BaseModel):
    raw_uid: str

    name: str|None = None
    link: str|None = None
    categories: set[TagCategory] = pydantic.Field(default_factory=set)

    def build_properties_for(self, tag_id: int) -> list[TagProperty]:
        properties = []

        if self.name:
            properties.append(TagProperty(tag_id=tag_id,
                                          type=TagPropertyType.tag_name,
                                          value=self.name))

        if self.link:
            properties.append(TagProperty(tag_id=tag_id,
                                          type=TagPropertyType.link,
                                          value=self.link))

        if self.categories:
            categories_dump = ",".join(sorted(c.value for c in self.categories))
            properties.append(TagProperty(tag_id=tag_id,
                                          type=TagPropertyType.category,
                                          value=categories_dump))

        return properties
