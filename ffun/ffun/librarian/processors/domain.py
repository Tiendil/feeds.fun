import logging
from urllib.parse import urlparse

from ffun.library.entities import Entry

from . import base

logger = logging.getLogger(__name__)


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> set[str]:
        if not entry.external_url:
            return set()

        try:
            parsed_url = urlparse(entry.external_url)
        except Exception:
            # TODO: log error somewhere, link it to the entry
            logger.exception("Failed to parse URL: %s", entry.external_url)
            return set()

        domain = parsed_url.netloc

        tags = set()

        while domain:
            tags.add(f'domain-name:{domain}')

            if "." not in domain:
                break

            domain = domain.split(".", 1)[1]

        return tags
