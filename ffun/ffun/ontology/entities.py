import enum

import pydantic


class TagPropertyType(int, enum.Enum):
    tag_name = 1  # "name" is reserved
    link = 2
    category = 3


class TagProperty(pydantic.BaseModel):
    tag_id: int
    type: TagPropertyType
    value: str


class Tag(pydantic.BaseModel):
    uid: str

    name: str|None = None
    link: str|None = None
    categories: set[str] = pydantic.Field(default_factory=set)

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
            categories_dump = ",".join(sorted(self.categories))
            properties.append(TagProperty(tag_id=tag_id,
                                          type=TagPropertyType.category,
                                          value=categories_dump))

        return properties
