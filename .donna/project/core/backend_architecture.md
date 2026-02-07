# Feeds Fun backend architecture

```toml donna
kind = "donna.lib.specification"
```

Top-level description of the Feeds Fun backend architecture and code structure.

## Modules

All backend is placed in the `./ffun/ffun` directory, which is a Python package. The main modules of the backend are:

- `ffun.api` — all API endpoints.
- `ffun.api.spa` — API endpoints used by the frontend.
- `ffun.application` — application construction and configs.
- `ffun.auth` — authentication and authorization logic.
- `ffun.cli` — CLI commands for managing the application.
- `ffun.core` — core/framework code — base classes and utilities.
- `ffun.data_protection` — code related to data protection and privacy.
- `ffun.domain` — domain logic — base logic related to the whole domain / used by the whole domain — base classes and building blocks for the domain logic.
- `ffun.feeds` — storing and managing feeds.
- `ffun.feeds_collections` — managing collections of feeds.
- `ffun.feeds_discoverer` — discovering feeds for sites.
- `ffun.feeds_links` — storing and managing links between feeds and users.
- `ffun.google` — code related to Google services, like Gemini API.
- `ffun.librarian` — tag processors meta logic and processors implementations.
- `ffun.library` — storing and managing news articles.
- `ffun.llms_framework` — universal logic for working with LLMs.
- `ffun.loader` — loading news articles from feeds.
- `ffun.markers` — storing and managing markers for news articles (e.g., read/unread).
- `ffun.meta` — business logic that requires integration of multiple domain modules.
- `ffun.ontology` — storing and managing tags.
- `ffun.openai` — code related to OpenAI services, API.
- `ffun.parsers` — parsers for everything — news articles, feeds, sites, etc.
- `ffun.processors_quality` — validating quality of tagging.
- `ffun.resources` — tracking usage quotas and other per-user resources.
- `ffun.scores` — storing and managing rules and scores for news.
- `ffun.tags` — tag-related code: normalization, validation. Not managing or storing tags — only domain-specific logic related to tags.
- `ffun.users` — storing and managing users.
- `ffun.user_settings` — storing and managing user settings.
