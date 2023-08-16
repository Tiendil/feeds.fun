from urllib.parse import urlparse

from ffun.core import logging
from ffun.library.entities import Entry
from ffun.ontology.entities import ProcessorTag, TagCategory

from . import base


logger = logging.get_module_logger()


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        if entry.title.isupper():
            return [ProcessorTag(raw_uid="upper-case-title")]

        return []
