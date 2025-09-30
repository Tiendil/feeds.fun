from ffun.core import logging
from ffun.tags.entities import NormalizerType
from ffun.tags.normalizers import form_normalizer, part_blacklist, part_replacer, splitter
from ffun.tags.normalizers.base import FakeNormalizer, Normalizer, NormalizerAlwaysError, NormalizerInfo
from ffun.tags.settings import settings

logger = logging.get_module_logger()


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

    normalizer: Normalizer

    if normalizer_config.type == NormalizerType.part_blacklist:
        normalizer = part_blacklist.Normalizer(blacklist=normalizer_config.blacklist)
    elif normalizer_config.type == NormalizerType.part_replacer:
        normalizer = part_replacer.Normalizer(replacements=normalizer_config.replacements)
    elif normalizer_config.type == NormalizerType.splitter:
        normalizer = splitter.Normalizer(separators=list(normalizer_config.separators))
    elif normalizer_config.type == NormalizerType.form_normalizer:
        normalizer = form_normalizer.Normalizer(
            model=normalizer_config.spacy_model,
            cos_cache_size=normalizer_config.cos_cache_size,
            forms_cache_size=normalizer_config.forms_cache_size,
        )
    else:
        raise NotImplementedError(f"Unknown normalizer type: {normalizer_config.type}")

    info = NormalizerInfo(
        id=normalizer_config.id,
        name=normalizer_config.name,
        normalizer=normalizer,
    )

    normalizers.append(info)


__all__ = ["Normalizer", "NormalizerInfo", "FakeNormalizer", "NormalizerAlwaysError", "normalizers"]
