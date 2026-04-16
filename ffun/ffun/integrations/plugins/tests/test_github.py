import pytest

from ffun.feeds_discoverer.tests import make as fd_make
from ffun.integrations.plugins import github
from ffun.integrations.plugins.github import _rewrite_pre_body
from ffun.parsers.tests import make as p_make


@pytest.fixture  # type: ignore
def plugin() -> github.Plugin:
    return github.construct()


class TestConstruct:
    def test_construct__uses_default_values(self) -> None:
        plugin = github.construct()

        assert plugin._canonical_host == "github.com"
        assert plugin._domains == {"github.com", "www.github.com"}
        assert "features" in plugin._owners_to_skip
        assert plugin._owner_feed_urls == ("https://github.com/{owner}.atom",)
        assert plugin._owner_repo_feed_urls == (
            "https://github.com/{owner}/{repo}/releases.atom",
            "https://github.com/{owner}/{repo}/commits.atom",
            "https://github.com/{owner}/{repo}/tags.atom",
            "https://github.com/{owner}/{repo}/discussions.atom",
            "https://github.com/{owner}/{repo}/wiki.atom",
        )
        assert plugin._owner_repo_branch_feed_urls == ("https://github.com/{owner}/{repo}/commits/{branch}.atom",)
        assert plugin._owner_repo_discussion_category_feed_urls == (
            "https://github.com/{owner}/{repo}/discussions/categories/{category_slug}.atom",
        )

    def test_construct__uses_passed_values(self) -> None:
        plugin = github.construct(
            canonical_host="feeds.example",
            domains=["feeds.example"],
            owners_to_skip=["skip-me"],
            owner_feed_urls=["https://feeds.example/{owner}.xml"],
            owner_repo_feed_urls=["https://feeds.example/{owner}/{repo}/updates.xml"],
            owner_repo_branch_feed_urls=["https://feeds.example/{owner}/{repo}/branches/{branch}.xml"],
            owner_repo_discussion_category_feed_urls=[
                "https://feeds.example/{owner}/{repo}/categories/{category_slug}.xml"
            ],
        )

        assert plugin._canonical_host == "feeds.example"
        assert plugin._domains == {"feeds.example"}
        assert plugin._owners_to_skip == {"skip-me"}
        assert plugin._owner_feed_urls == ("https://feeds.example/{owner}.xml",)
        assert plugin._owner_repo_feed_urls == ("https://feeds.example/{owner}/{repo}/updates.xml",)
        assert plugin._owner_repo_branch_feed_urls == ("https://feeds.example/{owner}/{repo}/branches/{branch}.xml",)
        assert plugin._owner_repo_discussion_category_feed_urls == (
            "https://feeds.example/{owner}/{repo}/categories/{category_slug}.xml",
        )


class TestPluginMethods:
    def test___init__setups_internal_collections(self) -> None:
        plugin = github.Plugin(
            canonical_host="github.example",
            domains=["github.example", "www.github.example"],
            owners_to_skip=["about", "pricing"],
            owner_feed_urls=["https://github.example/{owner}.atom"],
            owner_repo_feed_urls=["https://github.example/{owner}/{repo}/commits.atom"],
            owner_repo_branch_feed_urls=["https://github.example/{owner}/{repo}/commits/{branch}.atom"],
            owner_repo_discussion_category_feed_urls=[
                "https://github.example/{owner}/{repo}/discussions/categories/{category_slug}.atom"
            ],
        )

        assert plugin._canonical_host == "github.example"
        assert plugin._domains == {"github.example", "www.github.example"}
        assert plugin._owners_to_skip == {"about", "pricing"}
        assert plugin._owner_feed_urls == ("https://github.example/{owner}.atom",)
        assert plugin._owner_repo_feed_urls == ("https://github.example/{owner}/{repo}/commits.atom",)
        assert plugin._owner_repo_branch_feed_urls == ("https://github.example/{owner}/{repo}/commits/{branch}.atom",)
        assert plugin._owner_repo_discussion_category_feed_urls == (
            "https://github.example/{owner}/{repo}/discussions/categories/{category_slug}.atom",
        )

    def test__extract_owner__returns_none_for_empty_segments(self, plugin: github.Plugin) -> None:
        assert plugin._extract_owner([]) is None

    def test__extract_owner__returns_none_for_skipped_owner(self, plugin: github.Plugin) -> None:
        assert plugin._extract_owner(["features"]) is None

    def test__extract_owner__removes_atom_suffix(self, plugin: github.Plugin) -> None:
        assert plugin._extract_owner(["openai.atom"]) == "openai"

    def test__extract_branch__returns_none_for_short_segments(self, plugin: github.Plugin) -> None:
        assert plugin._extract_branch(["openai", "openai", "commits"]) is None

    def test__extract_branch__returns_branch_from_commits_path(self, plugin: github.Plugin) -> None:
        assert plugin._extract_branch(["openai", "openai", "commits", "main"]) == "main"
        assert plugin._extract_branch(["openai", "openai", "commits", "feature", "nested"]) == "feature/nested"

    def test__extract_branch__returns_branch_from_tree_path(self, plugin: github.Plugin) -> None:
        assert plugin._extract_branch(["openai", "openai", "tree", "main"]) == "main"

    def test__extract_branch__returns_none_for_non_constructable_tree_path(self, plugin: github.Plugin) -> None:
        assert plugin._extract_branch(["openai", "openai", "tree", "feature", "nested"]) is None

    def test__extract_discussion_category_slug__returns_none_for_non_matching_segments(
        self, plugin: github.Plugin
    ) -> None:
        assert plugin._extract_discussion_category_slug(["openai", "openai", "discussions"]) is None
        assert (
            plugin._extract_discussion_category_slug(["openai", "openai", "issues", "categories", "announcements"])
            is None
        )

    def test__extract_discussion_category_slug__returns_slug(self, plugin: github.Plugin) -> None:
        assert (
            plugin._extract_discussion_category_slug(
                ["openai", "openai", "discussions", "categories", "announcements.atom"]
            )
            == "announcements"
        )

    def test__is_feed_path__detects_atom_paths(self, plugin: github.Plugin) -> None:
        assert plugin._is_feed_path("/openai.atom") is True
        assert plugin._is_feed_path("/openai/openai/releases.atom") is True
        assert plugin._is_feed_path("/openai/openai/releases") is False

    def test__construct_owner_feed_urls__formats_templates(self, plugin: github.Plugin) -> None:
        assert plugin._construct_owner_feed_urls("openai") == {"https://github.com/openai.atom"}

    def test__construct_owner_repo_feed_urls__formats_templates(self, plugin: github.Plugin) -> None:
        assert plugin._construct_owner_repo_feed_urls("openai", "openai") == {
            "https://github.com/openai/openai/releases.atom",
            "https://github.com/openai/openai/commits.atom",
            "https://github.com/openai/openai/tags.atom",
            "https://github.com/openai/openai/discussions.atom",
            "https://github.com/openai/openai/wiki.atom",
        }

    def test__construct_owner_repo_branch_feed_urls__formats_templates(self, plugin: github.Plugin) -> None:
        assert plugin._construct_owner_repo_branch_feed_urls("openai", "openai", "main") == {
            "https://github.com/openai/openai/commits/main.atom"
        }

    def test__construct_owner_repo_discussion_category_feed_urls__formats_templates(
        self, plugin: github.Plugin
    ) -> None:
        assert plugin._construct_owner_repo_discussion_category_feed_urls("openai", "openai", "announcements") == {
            "https://github.com/openai/openai/discussions/categories/announcements.atom"
        }


class TestRewritePreBody:
    def test_rewrites_single_top_level_pre_block_as_markdown(self) -> None:
        body = "<pre># Release\n\n- first\n- second</pre>"

        rewritten_body = _rewrite_pre_body(body)

        assert "<h1>Release</h1>" in rewritten_body
        assert "<li>first</li>" in rewritten_body
        assert "<li>second</li>" in rewritten_body
        assert "<pre>" not in rewritten_body

    def test_keeps_body_when_pre_is_not_the_only_top_level_node(self) -> None:
        body = "<pre># Release</pre><p>Already formatted</p>"

        assert _rewrite_pre_body(body) == body

    def test_keeps_body_when_top_level_node_is_not_pre(self) -> None:
        body = "<div><pre># Release</pre></div>"

        assert _rewrite_pre_body(body) == body

    def test_keeps_body_when_pre_is_empty(self) -> None:
        body = "<pre></pre>"

        assert _rewrite_pre_body(body) == body


class TestPostprocessEntry:
    def test_rewrites_body_via_pre_body_helper(self, plugin: github.Plugin) -> None:
        body = "<pre># Release notes\n\n- item</pre>"
        entry = p_make.fake_entry_info(body=body)

        processed_entry = plugin.postprocess_entry(entry)

        assert processed_entry == entry.replace(body=_rewrite_pre_body(body))


class TestDiscoverFeedUrls:
    @pytest.mark.asyncio
    async def test_discover_feed_urls__returns_context_for_non_github_host(self, plugin: github.Plugin) -> None:
        context = fd_make.context("https://example.com/openai/gpt")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com",
            "https://github.com/features",
            "https://github.com/topics/ai",
        ],
    )
    @pytest.mark.asyncio
    async def test_discover_feed_urls__returns_context_when_owner_can_not_be_extracted(
        self, plugin: github.Plugin, url: str
    ) -> None:
        context = fd_make.context(url)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None

    @pytest.mark.parametrize(
        "url,expected_urls",
        [
            ("https://github.com/openai", {"https://github.com/openai.atom"}),
            ("https://www.github.com/openai?tab=repositories", {"https://github.com/openai.atom"}),
        ],
    )
    @pytest.mark.asyncio
    async def test_discover_feed_urls__constructs_owner_feeds(
        self, plugin: github.Plugin, url: str, expected_urls: set[str]
    ) -> None:
        context = fd_make.context(url)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(candidate_urls=expected_urls)
        assert result is None

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/openai/openai",
            "https://github.com/openai/openai/issues",
            "https://github.com/openai/openai/releases",
        ],
    )
    @pytest.mark.asyncio
    async def test_discover_feed_urls__constructs_repository_feeds(self, plugin: github.Plugin, url: str) -> None:
        context = fd_make.context(url)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://github.com/openai.atom",
                "https://github.com/openai/openai/releases.atom",
                "https://github.com/openai/openai/commits.atom",
                "https://github.com/openai/openai/tags.atom",
                "https://github.com/openai/openai/discussions.atom",
                "https://github.com/openai/openai/wiki.atom",
            }
        )
        assert result is None

    @pytest.mark.parametrize(
        "url,expected_extra_url",
        [
            ("https://github.com/openai/openai/commits/main", "https://github.com/openai/openai/commits/main.atom"),
            ("https://github.com/openai/openai/tree/main", "https://github.com/openai/openai/commits/main.atom"),
        ],
    )
    @pytest.mark.asyncio
    async def test_discover_feed_urls__constructs_branch_feeds(
        self, plugin: github.Plugin, url: str, expected_extra_url: str
    ) -> None:
        context = fd_make.context(url)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://github.com/openai.atom",
                "https://github.com/openai/openai/releases.atom",
                "https://github.com/openai/openai/commits.atom",
                "https://github.com/openai/openai/tags.atom",
                "https://github.com/openai/openai/discussions.atom",
                "https://github.com/openai/openai/wiki.atom",
                expected_extra_url,
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_discover_feed_urls__constructs_discussion_category_feeds(self, plugin: github.Plugin) -> None:
        context = fd_make.context("https://github.com/openai/openai/discussions/categories/announcements")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://github.com/openai.atom",
                "https://github.com/openai/openai/releases.atom",
                "https://github.com/openai/openai/commits.atom",
                "https://github.com/openai/openai/tags.atom",
                "https://github.com/openai/openai/discussions.atom",
                "https://github.com/openai/openai/discussions/categories/announcements.atom",
                "https://github.com/openai/openai/wiki.atom",
            }
        )
        assert result is None

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/openai.atom",
            "https://github.com/openai/openai/releases.atom",
            "https://github.com/openai/openai/commits/main.atom",
            "https://github.com/openai/openai/discussions/categories/announcements.atom",
        ],
    )
    @pytest.mark.asyncio
    async def test_discover_feed_urls__does_not_expand_feed_urls(self, plugin: github.Plugin, url: str) -> None:
        context = fd_make.context(url)

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context
        assert result is None

    @pytest.mark.asyncio
    async def test_discover_feed_urls__uses_configured_feed_templates(self) -> None:
        plugin = github.construct(
            canonical_host="github.com",
            domains=["github.com"],
            owners_to_skip=[],
            owner_feed_urls=["https://feeds.example/{owner}.xml"],
            owner_repo_feed_urls=["https://feeds.example/{owner}/{repo}/updates.xml"],
            owner_repo_branch_feed_urls=["https://feeds.example/{owner}/{repo}/branches/{branch}.xml"],
            owner_repo_discussion_category_feed_urls=[
                "https://feeds.example/{owner}/{repo}/categories/{category_slug}.xml"
            ],
        )
        context = fd_make.context("https://github.com/openai/openai/discussions/categories/announcements")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://feeds.example/openai.xml",
                "https://feeds.example/openai/openai/updates.xml",
                "https://feeds.example/openai/openai/categories/announcements.xml",
            }
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_discover_feed_urls__uses_configured_branch_feed_templates(self) -> None:
        plugin = github.construct(
            canonical_host="github.com",
            domains=["github.com"],
            owners_to_skip=[],
            owner_feed_urls=["https://feeds.example/{owner}.xml"],
            owner_repo_feed_urls=["https://feeds.example/{owner}/{repo}/updates.xml"],
            owner_repo_branch_feed_urls=["https://feeds.example/{owner}/{repo}/branches/{branch}.xml"],
            owner_repo_discussion_category_feed_urls=[],
        )
        context = fd_make.context("https://github.com/openai/openai/commits/main")

        new_context, result = await plugin.discover_feed_urls(context)

        assert new_context == context.replace(
            candidate_urls={
                "https://feeds.example/openai.xml",
                "https://feeds.example/openai/openai/updates.xml",
                "https://feeds.example/openai/openai/branches/main.xml",
            }
        )
        assert result is None
