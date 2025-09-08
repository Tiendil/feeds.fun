from ffun.core import logging
from ffun.librarian.processors import base
from ffun.library.entities import Entry
from ffun.ontology.entities import NormalizationMode, RawTag

logger = logging.get_module_logger()


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> list[RawTag]:
        if entry.title.isupper():
            return [
                RawTag(
                    raw_uid="upper-case-title",
                    normalization=NormalizationMode.final,
                )
            ]

        return []
