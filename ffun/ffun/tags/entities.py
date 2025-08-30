import datetime
import enum
from typing import Annotated, Literal

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import TagUid, TagUidPart


class TagCategory(str, enum.Enum):
    network_domain = "network-domain"
    feed_tag = "feed-tag"


class TagInNormalization(BaseEntity):
    uid: TagUid
    parts: list[TagUidPart]

    preserve: bool

    name: str | None
    link: str | None
    categories: set[TagCategory]


# TODO: check most common parts
# TODO: check most common rules
# TODO: remove duplicates like `xxx-xxx` -> `xxx`

class NormalizerType(enum.StrEnum):
    fake = "fake"
    part_blacklist = "part_blacklist"
    part_replacer = "part_replacer"

# TODO: split by part `rest-api-for-graph-processing` -> `rest-api` & `graph-processing`
#       `social-media-impact-on-innovation` -> `social-media-impact` & `innovation`
# TODO: unite multiple parts `q-a` -> `qa`, `start-up` -> `startup`, `e-mail` -> `email`, etc.
# TODO: push to left `tail-s` -> `tails`


class BaseNormalizer(BaseEntity):
    id: int
    enabled: bool
    name: str
    type: NormalizerType


class PartBlacklist(BaseNormalizer):
    type: Literal[NormalizerType.part_blacklist] = NormalizerType.part_blacklist
    blacklist: set[str] = pydantic.Field(default_factory=set)


class PartReplacer(BaseNormalizer):
    type: Literal[NormalizerType.part_replacer] = NormalizerType.part_replacer
    replacements: dict[str, str] = pydantic.Field(default_factory=dict)


TagNormalizer = Annotated[
    PartBlacklist | PartReplacer,
    pydantic.Field(discriminator="type"),
]


class NormalizersConfig(pydantic.BaseModel):
    tag_processors: tuple[TagNormalizer, ...]
