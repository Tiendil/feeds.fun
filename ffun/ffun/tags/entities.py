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

###############################################
# Normalizes that we do not implement for now.
# We may introduce them later when we have specialized tag processors that hover problem cases.
#
# 1. Duplicates removal like `xxx-xxx` -> `xxx`
#    Because there is a lot of contradictions and corners cases:
#    - duplicates are parts of naming and idioms: `c-plus-plus`, `yo-yo-dieting`, `day-to-day`, `end-to-end`
#    - numbers also duplicate, for example, in versions: `python-3-11-3`
#    - duplicates may be correctly processed by other normalizes:
#      `brain-implants-and-brain-decoding` -> `brain-implants` & `brain-decoding`
###############################################

class NormalizerType(enum.StrEnum):
    fake = "fake"
    part_blacklist = "part_blacklist"
    part_replacer = "part_replacer"
    splitter = "splitter"

# TODO: split by part `rest-api-for-graph-processing` -> `rest-api` & `graph-processing`
#       `social-media-impact-on-innovation` -> `social-media-impact` & `innovation`
#       artistic-expression-through-artistic-skills -> `artistic-expression` & `artistic-skills`
#       MUST be before duplication detection
# TODO: push to left `tail-s` -> `tails`, `garry-s-mod` -> `garrys-mod`, etc.


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


class Splitter(BaseNormalizer):
    type: Literal[NormalizerType.splitter] = NormalizerType.splitter
    separators: set[str] = pydantic.Field(default_factory=set)


TagNormalizer = Annotated[
    PartBlacklist | PartReplacer | Splitter,
    pydantic.Field(discriminator="type"),
]


class NormalizersConfig(pydantic.BaseModel):
    tag_normalizer: tuple[TagNormalizer, ...]
