import re
from typing import cast

from ffun.core import logging
from ffun.domain.entities import AbsoluteUrl
from ffun.domain.urls import construct_f_url
from ffun.feeds_discoverer import entities as fd_entities
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.library.entities import Reference, ReferenceSemantics
from ffun.parsers import entities as p_entities

logger = logging.get_module_logger()


def _rewrite_preview_image_reference(reference: Reference) -> Reference:
    # Reddit often expose images via links on the `preview.redd.it` domain:
    #
    #   https://preview.redd.it/<asset-id>.<ext>?width=140&height=140&crop=1:1,smart&auto=webp&s=<hash>
    #
    # However, Reddit restricts access to the images in that domain
    # (return 403 or redirect through reddit.com media pages).
    #
    # => we rewrite urls to point to the domain that supports external access to images.
    #
    # We rewrite: https://preview.redd.it/<asset-id>.<ext>?...
    #
    # into: https://i.redd.it/<asset-id>.<ext>

    if reference.semantics != ReferenceSemantics.image:
        return reference

    f_url = construct_f_url(reference.url)

    if f_url is None or f_url.host != "preview.redd.it":
        return reference

    f_url.host = "i.redd.it"
    f_url.query = ""  # type: ignore
    f_url.fragment = None

    return reference.replace(url=AbsoluteUrl(str(f_url)))


class Plugin(BasePlugin):
    __slots__ = ("_path_prefix_regex", "_domains", "_domains_to_skip")

    def __init__(self, path_prefix_regex: str, domains: list[str], domains_to_skip: list[str]):
        self._path_prefix_regex = re.compile(path_prefix_regex)
        self._domains = set(domains)
        self._domains_to_skip = set(domains_to_skip)

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:
        """Construct RSS URLs for new Reddit pages that do not expose feed links.

        Detects reddit.com subreddit paths, synthesizes the `.rss` URL, and adds it
        as a candidate unless it matches the current URL.
        """
        assert context.url is not None

        logger.info("discovering_reddit_extracting_feeds", url=context.url)

        f_url = construct_f_url(context.url)

        assert f_url is not None

        if f_url.host not in self._domains:
            # We are not interested in not reddit.com domains
            logger.info("discovering_reddit_not_reddit_domain")
            return context, None

        if f_url.host in self._domains_to_skip:
            # Old Reddit site has marked RSS urls in the header
            # => we can skip it — it is better to rely on the standard discovery process
            logger.info("discovering_reddit_old_reddit_domain")
            return context, None

        match = self._path_prefix_regex.match(str(f_url.path))

        if match is None:
            logger.info("discovering_reddit_not_reddit_path")
            return context, None

        base_path = match.group()

        if not base_path.endswith("/"):
            base_path += "/"

        f_url.path = f"{base_path}.rss"  # type: ignore
        f_url.query = ""  # type: ignore

        # this check is required to stop recursion on _discover_check_candidate_links
        if str(f_url) == context.url:
            logger.info("discovering_reddit_same_url")
            return context, None

        logger.info("discovering_reddit_feed", feed_url=f_url)

        return context.replace(candidate_urls={str(f_url)}), None

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return entry.replace(
            references=[_rewrite_preview_image_reference(reference) for reference in entry.references]
        )


def construct(**kwargs: object) -> Plugin:
    path_prefix_regex = cast(str, kwargs.get("path_prefix_regex", r"^/r/[^/]+/?"))
    domains = cast(list[str], kwargs.get("domains", ["www.reddit.com", "reddit.com", "old.reddit.com"]))
    domains_to_skip = cast(list[str], kwargs.get("domains_to_skip", ["old.reddit.com"]))

    return Plugin(
        path_prefix_regex=path_prefix_regex,
        domains=domains,
        domains_to_skip=domains_to_skip,
    )
