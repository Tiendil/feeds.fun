from typing import cast

import markdown  # type: ignore
from bs4 import BeautifulSoup
from bs4.element import Tag

from ffun.core import logging
from ffun.domain.urls import construct_f_url
from ffun.feeds_discoverer import entities as fd_entities
from ffun.integrations.plugin import Plugin as BasePlugin
from ffun.parsers import entities as p_entities

logger = logging.get_module_logger()


def _rewrite_pre_body(body: str) -> str:
    soup = BeautifulSoup(body, "html.parser")
    meaningful_top_level_nodes = [
        child
        for child in soup.contents
        if not (isinstance(child, str) and child.strip() == "")
    ]

    if len(meaningful_top_level_nodes) != 1:
        return body

    pre = meaningful_top_level_nodes[0]

    if not isinstance(pre, Tag) or pre.name != "pre":
        return body

    markdown_source = pre.get_text()

    if markdown_source == "":
        return body

    return markdown.markdown(markdown_source)  # type: ignore


# Note: there are no official documentation on GitHub feed URLs,
#       so we use whatever the community has discovered and documented in various places.
# TODO: there are some other feeds that are dependent on the `Accept` header, rather than the URL structure
#       for example: `https://github.com/{user}` + `Accept: application/atom+xml`
#       we do not support such feeds for now, to not overcomplicate the plugin.
class Plugin(BasePlugin):
    __slots__ = (
        "_canonical_host",
        "_domains",
        "_owners_to_skip",
        "_owner_feed_urls",
        "_owner_repo_feed_urls",
        "_owner_repo_branch_feed_urls",
        "_owner_repo_discussion_category_feed_urls",
    )

    def __init__(  # noqa: CFQ002
        self,
        canonical_host: str,
        domains: list[str],
        owners_to_skip: list[str],
        owner_feed_urls: list[str],
        owner_repo_feed_urls: list[str],
        owner_repo_branch_feed_urls: list[str],
        owner_repo_discussion_category_feed_urls: list[str],
    ):
        self._canonical_host = canonical_host
        self._domains = set(domains)
        self._owners_to_skip = set(owners_to_skip)
        self._owner_feed_urls = tuple(owner_feed_urls)
        self._owner_repo_feed_urls = tuple(owner_repo_feed_urls)
        self._owner_repo_branch_feed_urls = tuple(owner_repo_branch_feed_urls)
        self._owner_repo_discussion_category_feed_urls = tuple(owner_repo_discussion_category_feed_urls)

    def _extract_owner(self, segments: list[str]) -> str | None:
        if not segments:
            return None

        owner = segments[0].removesuffix(".atom")

        if owner in self._owners_to_skip:
            return None

        if owner == "":
            return None

        return owner

    def _extract_branch(self, segments: list[str]) -> str | None:
        if len(segments) < 4:
            return None

        if segments[2] == "commits":
            branch = "/".join(segments[3:]).removesuffix(".atom")
            return branch or None

        if segments[2] == "tree" and len(segments) == 4:
            return segments[3] or None

        return None

    def _extract_discussion_category_slug(self, segments: list[str]) -> str | None:
        if len(segments) != 5:
            return None

        if segments[2] != "discussions" or segments[3] != "categories":
            return None

        return segments[4].removesuffix(".atom") or None

    def _is_feed_path(self, path: str) -> bool:
        return path.endswith(".atom")

    def _construct_owner_feed_urls(self, owner: str) -> set[str]:
        return {url.format(owner=owner) for url in self._owner_feed_urls}

    def _construct_owner_repo_feed_urls(self, owner: str, repo: str) -> set[str]:
        return {url.format(owner=owner, repo=repo) for url in self._owner_repo_feed_urls}

    def _construct_owner_repo_branch_feed_urls(self, owner: str, repo: str, branch: str) -> set[str]:
        return {url.format(owner=owner, repo=repo, branch=branch) for url in self._owner_repo_branch_feed_urls}

    def _construct_owner_repo_discussion_category_feed_urls(
        self, owner: str, repo: str, category_slug: str
    ) -> set[str]:
        return {
            url.format(owner=owner, repo=repo, category_slug=category_slug)
            for url in self._owner_repo_discussion_category_feed_urls
        }

    def postprocess_entry(self, entry: p_entities.EntryInfo) -> p_entities.EntryInfo:
        return entry.replace(body=_rewrite_pre_body(entry.body))

    async def discover_feed_urls(self, context: fd_entities.Context) -> fd_entities.DiscoverResult:  # noqa: CCR001
        assert context.url is not None

        logger.info("discovering_github_extracting_feeds", url=context.url)

        f_url = construct_f_url(context.url)

        assert f_url is not None

        if f_url.host not in self._domains:
            logger.info("discovering_github_not_github_domain")
            return context, None

        path = str(f_url.path)

        if self._is_feed_path(path):
            logger.info("discovering_github_feed_url_received")
            return context, None

        segments = [segment for segment in path.split("/") if segment]

        owner = self._extract_owner(segments)

        if owner is None:
            logger.info("discovering_github_owner_not_found")
            return context, None

        candidate_urls: set[str] = self._construct_owner_feed_urls(owner)

        if len(segments) >= 2:
            repo = segments[1]
            candidate_urls.update(self._construct_owner_repo_feed_urls(owner, repo))

            branch = self._extract_branch(segments)

            if branch is not None:
                candidate_urls.update(self._construct_owner_repo_branch_feed_urls(owner, repo, branch))

            category_slug = self._extract_discussion_category_slug(segments)

            if category_slug is not None:
                candidate_urls.update(
                    self._construct_owner_repo_discussion_category_feed_urls(owner, repo, category_slug)
                )

        candidate_urls.discard(context.url)

        if not candidate_urls:
            logger.info("discovering_github_no_constructable_feeds")
            return context, None

        feed_urls: list[str] = sorted(candidate_urls)
        logger.info("discovering_github_feeds_constructed", feed_urls=feed_urls)

        return context.replace(candidate_urls=set(candidate_urls)), None


def construct(**kwargs: object) -> Plugin:
    canonical_host = cast(str, kwargs.get("canonical_host", "github.com"))
    domains = cast(list[str], kwargs.get("domains", ["github.com", "www.github.com"]))
    owners_to_skip = cast(
        list[str],
        kwargs.get(
            "owners_to_skip",
            [
                "about",
                "apps",
                "codespaces",
                "collections",
                "contact",
                "events",
                "explore",
                "features",
                "issues",
                "login",
                "marketplace",
                "new",
                "notifications",
                "orgs",
                "organizations",
                "pricing",
                "pulls",
                "search",
                "settings",
                "site",
                "sponsors",
                "topics",
                "trending",
            ],
        ),
    )
    owner_feed_urls = cast(list[str], kwargs.get("owner_feed_urls", [f"https://{canonical_host}/{{owner}}.atom"]))
    owner_repo_feed_urls = cast(
        list[str],
        kwargs.get(
            "owner_repo_feed_urls",
            [
                f"https://{canonical_host}/{{owner}}/{{repo}}/releases.atom",
                f"https://{canonical_host}/{{owner}}/{{repo}}/commits.atom",
                f"https://{canonical_host}/{{owner}}/{{repo}}/tags.atom",
                f"https://{canonical_host}/{{owner}}/{{repo}}/discussions.atom",
                f"https://{canonical_host}/{{owner}}/{{repo}}/wiki.atom",
            ],
        ),
    )
    owner_repo_branch_feed_urls = cast(
        list[str],
        kwargs.get(
            "owner_repo_branch_feed_urls",
            [f"https://{canonical_host}/{{owner}}/{{repo}}/commits/{{branch}}.atom"],
        ),
    )
    owner_repo_discussion_category_feed_urls = cast(
        list[str],
        kwargs.get(
            "owner_repo_discussion_category_feed_urls",
            [f"https://{canonical_host}/{{owner}}/{{repo}}/discussions/categories/{{category_slug}}.atom"],
        ),
    )

    return Plugin(
        canonical_host=canonical_host,
        domains=domains,
        owners_to_skip=owners_to_skip,
        owner_feed_urls=owner_feed_urls,
        owner_repo_feed_urls=owner_repo_feed_urls,
        owner_repo_branch_feed_urls=owner_repo_branch_feed_urls,
        owner_repo_discussion_category_feed_urls=owner_repo_discussion_category_feed_urls,
    )
