from ffun.core import logging
from ffun.tags.entities import NormalizerType
from ffun.tags.normalizers.base import Normalizer
from ffun.tags.normalizers.part_blacklist import PartBlacklistNormalizer
from ffun.tags.normalizers.part_replacer import PartReplacerNormalizer
from ffun.tags.settings import settings

logger = logging.get_module_logger()


class NormalizerInfo:
    __slots__ = ("id", "name", "normalizer", "type")

    def __init__(self, id: int, name: str, type: NormalizerType, normalizer: Normalizer) -> None:
        self.id = id
        self.name = name
        self.type = type
        self.normalizer = normalizer


normalizers: list[NormalizerInfo] = []


for normalizer_config in settings.tag_normalizers:
    if not normalizer_config.enabled:
        logger.info(
            "tag_normalizer_is_disabled",
            normalizer_id=normalizer_config.id,
            normalizer_name=normalizer_config.name,
        )
        continue

    logger.info("add_tag_normalizer", normalizer_id=normalizer_config.id, normalizer_name=normalizer_config.name)

    if normalizer_config.type == NormalizerType.part_blacklist:
        normalizer = PartBlacklistNormalizer(blacklist=normalizer_config.blacklist)
    elif normalizer_config.type == NormalizerType.part_replacer:
        normalizer = PartReplacerNormalizer(replacements=normalizer_config.replacements)
    else:
        raise NotImplementedError(f"Unknown normalizer type: {normalizer_config.type}")

    info = NormalizerInfo(
        id=normalizer_config.id,
        name=normalizer_config.name,
        type=normalizer_config.type,
        normalizer=normalizer,
    )

    normalizers.append(info)
