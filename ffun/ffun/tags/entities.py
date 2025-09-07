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

    link: str | None
    categories: set[TagCategory]


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
# 2. Removing suffixes from numbers like `-s`, `-th`, `-nd`, `-rd`: `1990s` -> `1990`, `4th` -> `4`
#    For now there is no enough evidence that this is a common problem.
# 3. Doing something with 's` suffix: `tail-s` -> `tail`, `garry-s-mod` -> `garry-mod`
#    There are a few different cases here, we should solve them separately, when tags become cleaner.
###############################################


class NormalizerType(enum.StrEnum):
    fake = "fake"
    part_blacklist = "part_blacklist"
    part_replacer = "part_replacer"
    splitter = "splitter"


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
