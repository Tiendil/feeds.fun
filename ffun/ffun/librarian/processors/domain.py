from urllib.parse import urlparse

from ffun.core import logging
from ffun.library.entities import Entry

from . import base

logger = logging.get_module_logger()


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> set[str]:
        if not entry.external_url:
            return set()

        try:
            parsed_url = urlparse(entry.external_url)
        except Exception:
            # TODO: log error somewhere, link it to the entry
            logger.exception("failed_to_parse_url", url=entry.external_url)
            return set()

        domain = parsed_url.netloc

        tags = set()

        while domain:
            tags.add(f'network-domain:{domain}')

            if "." not in domain:
                break

            domain = domain.split(".", 1)[1]

        return tags
