import enum
from typing import Annotated, Literal

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import TagUid, TagUidPart


class TagCategory(enum.StrEnum):
    network_domain = "network-domain"
    feed_tag = "feed-tag"


class NormalizationMode(enum.StrEnum):
    raw = "raw"  # tag should be processed by normalizers and can be removed
    preserve = "preserve"  # tag should be processed by normalizers but can not be removed
    final = "final"  # tag should not be processed by normalizers and can not be removed


class TagInNormalization(BaseEntity):
    uid: TagUid
    parts: list[TagUidPart]

    mode: NormalizationMode

    link: str | None
    categories: set[TagCategory]


class NormalizerType(enum.StrEnum):
    fake = "fake"
    part_blacklist = "part_blacklist"
    part_replacer = "part_replacer"
    splitter = "splitter"
    form_normalizer = "form_normalizer"


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


class FormNormalizer(BaseNormalizer):
    type: Literal[NormalizerType.form_normalizer] = NormalizerType.form_normalizer
    spacy_model: str
    cos_cache_size: int
    forms_cache_size: int


TagNormalizer = Annotated[
    PartBlacklist | PartReplacer | Splitter | FormNormalizer,
    pydantic.Field(discriminator="type"),
]


class NormalizersConfig(pydantic.BaseModel):
    tag_normalizer: tuple[TagNormalizer, ...]
