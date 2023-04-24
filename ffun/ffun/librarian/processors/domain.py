from urllib.parse import urlparse

from ffun.core import logging
from ffun.library.entities import Entry

from . import base

logger = logging.get_module_logger()


def domain_to_parts(domain: str) -> list[str]:

    if domain.startswith("www."):
        domain = domain[4:]

    parts = []

    while domain:
        if "." not in domain:
            parts.append(f'top-level-domain-{domain}')
            break

        parts.append(domain)

        domain = domain.split(".", 1)[1]

    return parts


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

        return set(domain_to_parts(domain))
