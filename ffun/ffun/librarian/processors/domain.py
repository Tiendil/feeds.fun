from urllib.parse import urlparse

from ffun.core import logging
from ffun.librarian.processors import base
from ffun.library.entities import Entry
from ffun.ontology.entities import ProcessorTag, TagCategory

logger = logging.get_module_logger()


def domain_to_parts(domain: str) -> list[str]:
    if domain.startswith("www."):
        domain = domain[4:]

    parts = []

    while domain:
        if "." not in domain:
            # do not add top level domains like .com
            # they are always on top of the tags list
            # and it is very rare situation when user wants to score by them
            break

        parts.append(domain)

        domain = domain.split(".", 1)[1]

    return parts


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        tags: list[ProcessorTag] = []

        if not entry.external_url:
            return tags

        try:
            parsed_url = urlparse(entry.external_url)
        except Exception:
            # TODO: log error somewhere, link it to the entry
            logger.exception("failed_to_parse_url", url=entry.external_url)
            return tags

        domain = parsed_url.netloc

        for subdomain in domain_to_parts(domain):
            tags.append(
                ProcessorTag(
                    raw_uid=subdomain,
                    link=parsed_url.scheme + "://" + subdomain,
                    categories={TagCategory.network_domain},
                )
            )

        return tags
