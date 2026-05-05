# Backend architecture

## Goal of the document

This document describes the stable backend package layout and ownership boundaries for Feeds Fun.

## Scope

This specification covers Python source code under `ffun/ffun`.

This specification does not cover frontend code, Docker configuration, deployment examples, or database schema details.

## Package layout

The backend MUST be implemented as the `ffun` Python package under `ffun/ffun`.

Backend modules SHOULD keep tests in colocated `tests` packages when the module has testable behavior.

Migration files SHOULD stay in module-local `migrations` packages for the domain area they modify.

## Module responsibilities

- `ffun.api` owns HTTP API endpoint wiring.
- `ffun.api.spa` owns API endpoints used by the frontend.
- `ffun.application` owns application construction and application-wide settings.
- `ffun.auth` owns authentication and authorization logic.
- `ffun.cli` owns command-line commands for managing the application.
- `ffun.core` owns framework-level base classes, utilities, logging, metrics, PostgreSQL helpers, plugins, and shared infrastructure.
- `ffun.data_protection` owns data protection and privacy-related behavior.
- `ffun.domain` owns cross-domain entities and domain utilities.
- `ffun.feeds` owns feed storage and feed management.
- `ffun.feeds_collections` owns curated feed collection configuration and behavior.
- `ffun.feeds_discoverer` owns discovery of feeds for external sites.
- `ffun.feeds_links` owns relationships between feeds and users.
- `ffun.google` owns Google service integrations.
- `ffun.integrations` owns source-specific integration plugins.
- `ffun.librarian` owns tag processor orchestration and processor implementations.
- `ffun.library` owns storage and management of news entries.
- `ffun.llms_framework` owns provider-neutral LLM framework logic.
- `ffun.loader` owns loading news entries from feeds.
- `ffun.markers` owns read/unread and similar entry markers.
- `ffun.meta` owns business logic that coordinates multiple domain modules.
- `ffun.ontology` owns stored tag ontology behavior.
- `ffun.openai` owns OpenAI service integration.
- `ffun.parsers` owns feed, entry, site, and OPML parsing logic.
- `ffun.processors_quality` owns quality validation for tagging processors.
- `ffun.resources` owns per-user quotas and resource accounting.
- `ffun.scores` owns score rules and score calculation.
- `ffun.site` owns backend support for serving or integrating with the site when present.
- `ffun.tags` owns tag normalization and validation logic that is not ontology storage.
- `ffun.users` owns user storage and management.
- `ffun.user_settings` owns user-specific settings storage and behavior.

## Submodules

Backend modules can have submodules that are responsible for more specific parts of the parent module's functionality.

When a module contains a small closed family of interchangeable components, and each component has meaningful component-specific behavior, the module SHOULD prefer one implementation submodule per component.

Shared package-level code for such component families SHOULD be limited to common types, public unions, selection helpers, and iteration glue.

Some submodules have specific names that reflect their responsibilities and SHOULD be similar across different backend modules.

List of specific submodules:

- `utils` - submodule responsible for utility functions that are not related to domain logic.
- `errors` - submodule responsible for defining custom exception types.
- `domain` - submodule responsible for domain-specific logic related to the module's responsibilities.
- `entities` - submodule responsible for defining types and entities related to the module's responsibilities.
- `operations` - submodule responsible for persistence-backed commands and state changes owned by the module.
- `settings` - submodule responsible for module-specific configuration.
- `migrations` - submodule containing database migrations owned by the module.
- `fixtures` - submodule containing reusable configuration or data fixtures owned by the module.
- `tests` - submodule containing module tests.

The `errors`, `entities`, `migrations`, and `tests` submodules MUST follow the corresponding architecture specifications when they are present.

The shared `entities` submodule in `ffun.core` MUST define the common entity base used by higher-level modules.

## Cross-module dependencies

Top-level backend modules that need types or values from another top-level backend module MUST use only that module's `domain`, `entities`, and `errors` submodules.

Top-level backend modules MAY import another module's `errors` submodule when they need to catch or raise errors owned by that module.

Top-level backend modules MUST NOT import implementation submodules from another top-level backend module.

Top-level backend modules MUST NOT import another top-level backend module's `operations` submodule.

## Data structures

Backend domain data structures SHOULD inherit from `ffun.core.entities.BaseEntity` unless a third-party interface or standard-library protocol requires another type.

Backend data structures MUST NOT use `dataclass` for domain entities.
