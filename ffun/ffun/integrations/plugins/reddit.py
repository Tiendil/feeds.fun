import re
from ffun.core import logging
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.domain.urls import construct_f_url
from ffun.feeds_discoverer import entities as fd_entities

logger = logging.get_module_logger()


class Plugin(BasePlugin):
    __slots__ = ('_path_prefix_regex',
                 '_domains',
                 '_domains_to_skip')

    def __init__(self, path_prefix_regex: str, domains: list[str], domains_to_skip: list[str]):
        self._path_prefix_regex = re.compile(path_prefix_regex)
        self._domains = set(domains)
        self._domains_to_skip = set(domains_to_skip)

    # TODO: test
    async def discover_feed_urls(self, context: fd_entities.Context) -> tuple[fd_entities.Context, fd_entities.Result | None]:
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


def construct(**kwargs) -> Plugin:
    return Plugin(
        path_prefix_regex=kwargs.get("path_prefix_regex", r"^/r/[^/]+/?"),
        domains=kwargs.get("domains", ["www.reddit.com", "reddit.com", "old.reddit.com"]),
        domains_to_skip=kwargs.get("domains_to_skip", ["old.reddit.com"]),
    )
