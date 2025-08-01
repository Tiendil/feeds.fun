import datetime
import enum

import pydantic

from ffun.core import utils
from ffun.core.entities import BaseEntity
from ffun.domain.entities import TagId, TagUid


class TagPropertyType(int, enum.Enum):
    link = 2
    categories = 3


class TagCategory(str, enum.Enum):
    network_domain = "network-domain"
    feed_tag = "feed-tag"


class TagProperty(BaseEntity):
    tag_id: TagId
    type: TagPropertyType
    value: str
    processor_id: int
    created_at: datetime.datetime


class RawTag(pydantic.BaseModel):
    raw_uid: str

    name: str | None = None
    link: str | None = None
    categories: set[TagCategory] = pydantic.Field(default_factory=set)


class NormalizedTag(pydantic.BaseModel):
    uid: TagUid

    name: str | None = None
    link: str | None = None
    categories: set[TagCategory] = pydantic.Field(default_factory=set)

    def build_properties_for(self, tag_id: TagId, processor_id: int) -> list[TagProperty]:
        properties = []

        created_at = utils.now()

        if self.link:
            properties.append(
                TagProperty(
                    tag_id=tag_id,
                    type=TagPropertyType.link,
                    value=self.link,
                    processor_id=processor_id,
                    created_at=created_at,
                )
            )

        if self.categories:
            categories_dump = ",".join(sorted(c.value for c in self.categories))
            properties.append(
                TagProperty(
                    tag_id=tag_id,
                    type=TagPropertyType.categories,
                    value=categories_dump,
                    processor_id=processor_id,
                    created_at=created_at,
                )
            )

        return properties


class Tag(pydantic.BaseModel):
    id: int
    name: str | None = None
    link: str | None = None
    categories: set[TagCategory] = pydantic.Field(default_factory=set)


class TagStatsBucket(BaseEntity):
    lower_bound: int
    upper_bound: int | None
    count: int
