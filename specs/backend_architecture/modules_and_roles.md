# Backend modules and roles

## Goal of the document

This document describes the Feeds Fun backend layout by module and role.

## Scope

This specification applies to Python source files under `ffun/ffun`.

## File and package layout

The backend layout follows the [shared modules and roles specification](../programming/modules_and_roles.md).
Each declared module is implemented as a Python package.

A declared top-level module named `ffun.<name>` MUST use `./ffun/ffun/<name>/` as its source directory.
A declared nested module MUST use the subdirectory of its parent module that matches the final component of its package name.

## Dedicated specifications

A top-level module MAY have a dedicated specification at `specs/backend_architecture/modules/<module>.md`, where `<module>` is its package name without the `ffun.` prefix.
A role MAY have a dedicated specification at `specs/backend_architecture/roles/<role>.md`, where `<role>` is its lowercase name.

The goal of a dedicated specification MUST name the module or role it governs.
If a role has a source filename or path pattern, the goal SHOULD mention it.
The scope MUST state which code the specification governs.
Its requirements apply alongside the layout rules in this specification.

## Modules

A top-level module MUST own the definitions and behavior that directly implement its responsibilities.

- `ffun.api` owns the backend's HTTP entry points.
- `ffun.application` owns application construction and application-wide settings.
- `ffun.audit` owns the audit records produced by backend workflows.
- `ffun.auth` owns authentication and authorization logic.
- `ffun.benefits` owns benefit package templates and the benefit transactions that coordinate changes to purchased state and its corresponding entitlements.
- `ffun.cli` owns the command-line interface for managing the backend.
- `ffun.core` owns the domain-neutral technical infrastructure shared by backend modules.
- `ffun.data_protection` owns data protection and privacy-related behavior.
- `ffun.dispatcher` owns dispatching entries to tag processor queues and tracking per-processor entry processing status.
- `ffun.domain` owns the shared code that represents and supports foundational Feeds Fun domain concepts.
- `ffun.entitlements` owns source-specific user entitlement state and merged effective entitlements.
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
- `ffun.locks` provides transaction-scoped logical mutual exclusion for backend workflows.
- `ffun.markers` owns read/unread and similar entry markers.
- `ffun.meta` owns business logic that coordinates multiple domain modules.
- `ffun.one_time_purchases` owns durable provider-independent one-time-purchase identities, provider-purchase references, and lifecycle snapshots linked to causal benefit transactions.
- `ffun.ontology` owns stored tag ontology behavior.
- `ffun.openai` owns OpenAI service integration.
- `ffun.parsers` owns feed, entry, site, and OPML parsing logic.
- `ffun.processors_quality` owns quality validation for tagging processors.
- `ffun.product` owns product-specific definitions and behavior with no more specific domain owner when multiple top-level modules need them directly for their own production responsibilities.
- `ffun.queues` owns the shared infrastructure for persistent work queues.
- `ffun.resources` owns per-user resource accounting and enforces caller-supplied limits on reservations.
- `ffun.scores` owns score rules and score calculation.
- `ffun.subscriptions` owns durable provider-independent purchased-subscription identities, provider-subscription references, and lifecycle snapshots linked to causal benefit transactions.
- `ffun.tags` owns tag normalization and validation logic that is not ontology storage.
- `ffun.user_settings` owns user-specific settings storage and behavior.
- `ffun.users` owns user storage and management.

### `ffun.api`

The `ffun.api.spa` nested module owns the HTTP endpoints used by the frontend.

### `ffun.core`

The shared `entities.py` file in `ffun.core` MUST define the common entity base used by higher-level modules.

### `ffun.domain`

Semantic identifiers owned by `ffun.domain` MUST be dependency-neutral and shared across independent domain modules.

A semantic identifier shared by independent domain-level modules SHOULD belong to `ffun.domain` when placing it in a narrower owning module would reverse the intended dependency direction or create a cycle.

## Roles

Paths in role placement rules are relative to the source directory of the file's most specific declared module.

An **orphaned file** is a Python file in a declared module whose path matches no placement rule for a role other than Public or Private.

### Domain

`domain.py` has the Domain role.

Files with the Domain role implement the business logic owned by their module.

See the [Domain role specification](roles/domain.md).

### Entities

`entities.py` has the Entities role.

Files with the Entities role define types, semantic identifiers, enums, and entities that represent their module's concepts.

See the [Entities role specification](roles/entities.md).

### Errors

`errors.py` has the Errors role.

Files with the Errors role define their module's exception types and error values.

See the [Errors role specification](roles/errors.md).

### Migrations

Python files matching `migrations/*.py` have the Migrations role.

Files with the Migrations role implement changes to the database schema and stored data.

See the [database migration rules](db.md#schema-migrations) for migration ownership and behavior.

### Operations

`operations.py` has the Operations role.

Files with the Operations role implement the technical details of their module's communication with storage and other external systems.

See the [Operations role specification](roles/operations.md).

### Settings

`settings.py` has the Settings role.

Files with the Settings role define how a module produces validated, typed settings from configuration inputs and defaults.

See the [Settings role specification](roles/settings.md).

### Tests

Python files under directories named `tests` at any depth have the Tests role.

Files with the Tests role contain their module's colocated tests and test support code.

The `make` Python submodule MAY appear only inside tests packages, as `<module>.tests.make`.

See the [Tests role specification](roles/tests.md).

### Utilities

`utils.py` has the Utilities role.

Files with the Utilities role provide technical helpers that support their module's implementation.

### Public

An orphaned file has the Public role when its module permits that role.

Files with the Public role contain public interfaces specific to their module.

### Private

An orphaned file has the Private role when its module permits that role.

Files with the Private role contain implementation code specific to their module.

## Permitted module and role pairs

Every declared module MAY contain files with any role in this list.

- Domain.
- Entities.
- Errors.
- Settings.
- Tests.
- Utilities.

A module MAY contain files with the Migrations role for changes it owns under the database migration rules.
A module MAY contain files with the Operations role when it owns the interaction with an external system that those files implement.

Foundational modules and `ffun.product` MAY contain files with the Public role.
Other declared modules MAY contain files with the Private role.

## Dependencies and public interfaces

Dependency rules apply to direct Python imports between files with different roles or owning modules.

### Import paths

For each definition it exposes at a boundary, a module SHOULD provide a single public import path.

When importing a named Python definition, code MUST use its defining Python module or an import path explicitly documented as a public facade in a specification or code comment.
A caller SHOULD import a definition from its defining Python module when that Python module exposes the definition to the caller as part of a public interface.

**Rationale:** A single public path gives callers a consistent way to import a definition.

**Example:** The Feeds module defines `Feed` in its public `entities.py` file.
A caller with access to that interface uses `from ffun.feeds.entities import Feed`.

When moving a definition makes an import path obsolete, the same change MUST update affected imports to a supported path and remove the obsolete path.

When a public interface exposes a definition from a private Python module, it MUST re-export the definition directly unless it adds behavior that belongs to its role or owning module.

**Rationale:** A direct re-export preserves the definition's identity and contract.

**Example:** `ffun.feeds.domain` exposes `save_feed` through `save_feed = operations.save_feed`.
A caller outside the module with access to that interface uses `from ffun.feeds.domain import save_feed`.

**Example:** `ffun.library.domain` wraps `operations.unlink_all` to own the transaction.

### Public import interfaces

A module MUST expose public interfaces only through Python modules assigned a role unless this specification explicitly allows a broader set of Python modules for it.
A Python module is private to its owning module unless explicitly declared a public interface.

The Python submodules in this list are public interfaces of their owning modules.

- `domain`.
- `entities`.
- `errors`.

Files with the Public role are public import interfaces for functionality owned by their module.
Other production files in foundational modules and `ffun.product` are also public import interfaces for functionality owned by their module.

A file with the Private role MAY be imported only by a file belonging directly to the same module.

All `tests.make` and `tests.helpers` Python submodules are public interfaces for code with the Tests role in another module.

Backend production code MUST NOT import `tests.make` or `tests.helpers`.

### Role dependencies

Role dependency rules apply only to imports between different roles when both files belong directly to the same module.

Within that scope, files with any role MAY import files with the Public or Private role.
Files with the Public or Private role MAY import files with any role except Tests.
Other imports within that scope are allowed only when their direction is listed below.

- Domain: Entities, Errors, Operations, Settings, Utilities
- Entities: Errors, Utilities
- Errors: Entities
- Operations: Entities, Errors, Settings, Utilities
- Settings: Entities
- Tests: Domain, Entities, Errors, Operations, Settings, Utilities
- Utilities: Entities, Errors, Settings

### Module kinds

#### Definitions

- **Foundational modules** provide shared technical infrastructure or foundational domain concepts.
- **Shared-service modules** provide common services for backend modules.
- **Edge modules** own boundaries through which external callers start or use the backend.
- **Domain-level modules** implement backend capabilities and workflows within their areas of responsibility.

#### Membership

- Foundational: `ffun.core`, `ffun.domain`
- Shared-service: `ffun.audit`, `ffun.locks`, `ffun.queues`
- Edge: `ffun.api`, `ffun.application`, `ffun.cli`, and their nested modules at any depth
- Domain-level: every other declared top-level module except `ffun.product`

### Module dependencies

A dependency between modules is allowed only when this specification permits its direction.

- Foundational: Foundational
- Shared-service: Foundational, Shared-service
- Domain-level: Foundational, Shared-service, Domain-level, `ffun.product`
- `ffun.product`: Foundational, Shared-service, Domain-level
- Edge: Foundational, Shared-service, Domain-level, `ffun.product`, Edge

Permissions to depend on `ffun.product` apply to the product-specific definitions and behavior the caller uses.

TODO Resolve how the foundational module dependency rule applies to `ffun.core.migrations`.
The [Tach configuration](../../ffun/tach.toml) permits `ffun.core.migrations` to depend on `ffun.application`.

## Current boundary problems that should be fixed

- Break the API–Application module cycle.
  Application imports API’s private root route handlers to register routes, and the root handlers import Application’s private settings to get the site domain. [Application wiring](../../ffun/ffun/application/application.py#L9) · [Root handlers](../../ffun/ffun/api/root/http_handlers.py#L8)

- CLI queue and metrics tests and Librarian’s background processor tests use Queues’ private `operations.py` to prepare or inspect queues.
  The CLI queue test also imports the private `FakeQueueItem` test type. [CLI queue tests](../../ffun/ffun/cli/commands/tests/test_queues.py) · [CLI metrics tests](../../ffun/ffun/cli/commands/tests/test_metrics.py) · [Librarian background processor tests](../../ffun/ffun/librarian/tests/test_background_processors.py)

  ```python
  from ffun.queues import operations as q_operations
  from ffun.queues.tests.entities import FakeQueueItem
  ```

- Feed Discovery’s `domain.py` imports Integrations’ private `settings.py` to look up a plugin for the source URL.
  Integrations tests import Feed Discovery’s `entities.py`, forming a module dependency cycle. [Feed Discovery Domain](../../ffun/ffun/feeds_discoverer/domain.py) · [Integrations plugin test](../../ffun/ffun/integrations/tests/test_plugin.py)

  ```python
  # ffun.feeds_discoverer.domain
  from ffun.integrations.settings import settings as i_settings

  # ffun.integrations.tests.test_plugin
  from ffun.feeds_discoverer import entities as fd_entities
  ```

  Loader and Parsers are also part of this cyclic group. Feed Discovery imports Loader’s Errors and Parsers’ Entities, and Loader imports Parsers’ Entities. The two test imports below also form a direct cycle between Integrations and Parsers. [Feed Discovery Domain](../../ffun/ffun/feeds_discoverer/domain.py) · [Loader Domain](../../ffun/ffun/loader/domain.py) · [Integrations plugin test](../../ffun/ffun/integrations/tests/test_plugin.py) · [Parser tests](../../ffun/ffun/parsers/tests/test_feed.py)

  ```python
  # ffun.integrations.tests.test_plugin
  from ffun.parsers import entities as p_entities

  # ffun.parsers.tests.test_feed
  from ffun.integrations.tests.helpers import FakeIntegration
  ```

- Meta’s `domain.py` imports Ontology’s private `cache.py` to look up tag IDs and UIDs during tag renormalization. [Meta Domain](../../ffun/ffun/meta/domain.py)

  ```python
  from ffun.ontology import cache as o_cache
  ```

- Tags and Ontology form a module dependency cycle. Tag normalization uses Ontology’s tag types, and those types use Tags’ category type. [Tags Domain](../../ffun/ffun/tags/domain.py) · [Ontology Entities](../../ffun/ffun/ontology/entities.py)

  ```python
  # ffun.tags.domain
  from ffun.ontology.entities import NormalizedTag, RawTag

  # ffun.ontology.entities
  from ffun.tags.entities import TagCategories
  ```

- Ontology’s `domain.py` imports Tags’ private `converters.py` to turn tag UIDs into display names. [Ontology Domain](../../ffun/ffun/ontology/domain.py)

  ```python
  from ffun.tags import converters
  ```

- Users test fixtures, factories, and Domain and Operations tests import `primary_oidc_service_id` from Auth’s private `settings.py` for test user mappings.
  The Operations tests also import `single_user_service_id` to test mappings across providers. [Fixtures](../../ffun/ffun/users/tests/fixtures.py) · [Factories](../../ffun/ffun/users/tests/make.py) · [Domain tests](../../ffun/ffun/users/tests/test_domains.py) · [Operations tests](../../ffun/ffun/users/tests/test_operations.py)

  Auth’s `domain.py` imports Users’ `domain.py`, so these test imports form a module dependency cycle. [Auth Domain](../../ffun/ffun/auth/domain.py)

  ```python
  # ffun.users.tests.test_operations
  from ffun.auth.settings import primary_oidc_service_id, single_user_service_id

  # ffun.auth.domain
  from ffun.users import domain as u_domain
  ```

- Google’s `entities.py` imports its chat request and response base classes through LLM Framework’s private `provider_interface.py`. Both classes are defined in LLM Framework’s public `entities.py`. [Google Entities](../../ffun/ffun/google/entities.py) · [LLM Framework Entities](../../ffun/ffun/llms_framework/entities.py)

  ```python
  from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse
  ```

- Librarian’s processor tests import `ChatResponseTest` from LLM Framework’s private `provider_interface.py` to build fake responses for a tag deduplication test. [Librarian processor tests](../../ffun/ffun/librarian/processors/tests/test_llm_general.py)

  ```python
  from ffun.llms_framework.provider_interface import ChatResponseTest
  ```

- Dispatcher’s cache tests import LLM Framework’s private provider registry to set API key statuses.
  Google and OpenAI’s provider tests import the private `Statuses` class in their key-status tests. [Dispatcher cache tests](../../ffun/ffun/dispatcher/tests/test_entries_cache.py) · [Google provider tests](../../ffun/ffun/google/tests/test_provider_interface.py) · [OpenAI provider tests](../../ffun/ffun/openai/tests/test_provider_interface.py)

  ```python
  from ffun.llms_framework.providers import llm_providers
  from ffun.llms_framework.keys_statuses import Statuses
  ```

- Processor Quality’s `domain.py` imports Librarian’s private processor registry and context class to run a configured processor on its quality route. [Processor Quality Domain](../../ffun/ffun/processors_quality/domain.py)

  ```python
  from ffun.librarian.background_processors import processors as ln_processors
  from ffun.librarian.processors.base import ProcessorContext
  ```

- Core and Domain form a module dependency cycle. Core’s test helpers import Domain’s `UserId` for log assertions, and Domain’s entities use Core’s base types. [Core test helpers](../../ffun/ffun/core/tests/helpers.py) · [Domain Entities](../../ffun/ffun/domain/entities.py)

  ```python
  # ffun.core.tests.helpers
  from ffun.domain.entities import UserId

  # ffun.domain.entities
  from ffun.core.entities import BaseEntity, NonEmptyString
  ```

- Feeds Links Operations and Loader Domain import Feed Collections’ private `collections` singleton to check membership or read collection metadata. [Feeds Links Operations](../../ffun/ffun/feeds_links/operations.py) · [Loader Domain](../../ffun/ffun/loader/domain.py)

  Dispatcher, Feeds Links, LLM Framework, and Loader tests import the same singleton to add feeds to test collections. Loader tests also read collection metadata through it. [Dispatcher tests](../../ffun/ffun/dispatcher/tests/test_domain.py) · [Feeds Links tests](../../ffun/ffun/feeds_links/tests/test_operations.py) · [LLM Framework tests](../../ffun/ffun/llms_framework/tests/test_keys_rotator.py) · [Loader tests](../../ffun/ffun/loader/tests/test_domain.py)

  ```python
  from ffun.feeds_collections.collections import collections
  ```

- Several Python modules use shared types through incidental imports in another Python module. The types are defined in `ffun.domain.entities`. The following files expose the names as a side effect of importing them for local use.

  - Feeds Entities exposes `FeedId`, which Loader Domain imports directly and SPA Entities accesses through Feeds’ `entities.py`. [Loader Domain](../../ffun/ffun/loader/domain.py) · [SPA Entities](../../ffun/ffun/api/spa/entities.py)
  - Feed Collections Entities exposes `CollectionId`, which Loader tests import and SPA Entities accesses through Feed Collections’ `entities.py`. [Loader tests](../../ffun/ffun/loader/tests/test_domain.py) · [SPA Entities](../../ffun/ffun/api/spa/entities.py)
  - LLM Framework Entities exposes `LLMTokens` and `USDCost`, which LLM Framework Domain and tests import. Google, OpenAI, and Librarian tests also import `LLMTokens` through that `entities.py` file. [LLM Framework Domain](../../ffun/ffun/llms_framework/domain.py) · [Google provider tests](../../ffun/ffun/google/tests/test_provider_interface.py) · [OpenAI provider tests](../../ffun/ffun/openai/tests/test_provider_interface.py) · [Librarian processor tests](../../ffun/ffun/librarian/processors/tests/test_llm_general.py)
  - Tags Entities exposes `TagUidPart`, which Tags’ utilities tests import. [Tags utilities tests](../../ffun/ffun/tags/tests/test_utils.py)
  - Users Entities exposes `UserId`, which Auth Domain uses as `u_entities.UserId`. [Auth Domain](../../ffun/ffun/auth/domain.py)

  ```python
  # ffun.loader.domain
  from ffun.feeds.entities import Feed, FeedId, FeedState
  ```

- Queues’ package initializer declares a public import path for five names already defined in its public `entities.py` file. The initializer has the Private role. [Queues initializer](../../ffun/ffun/queues/__init__.py)

  ```python
  __all__ = ("BaseQueueItem", "DEFAULT_SECONDARY_ID", "QueueKind", "QueueRecord", "QueueRecordId")
  ```

- Several public functions wrap private definitions by forwarding the same arguments and results. The direct re-export rule applies to these functions.

  - Parsers Domain’s `parse_opml` forwards to `opml.extract_feeds`. [Parsers Domain](../../ffun/ffun/parsers/domain.py)
  - Feed Collections Domain’s `collection`, `collection_by_slug`, `all_collections`, and `collections_for_feed` forward to the `collections` singleton. [Feed Collections Domain](../../ffun/ffun/feeds_collections/domain.py)
  - Ontology Domain’s `get_ids_by_uids` and `get_tags_by_ids` forward to methods on `_tags_cache`. [Ontology Domain](../../ffun/ffun/ontology/domain.py)
  - LLM Framework Domain’s `cost_points_to_usd_cost` forwards to `_cost_points.to_cost`. [LLM Framework Domain](../../ffun/ffun/llms_framework/domain.py)
  - Feed Collections’ `add_feed_to_collection` and Entitlements’ `load_source_entitlement` forward to private implementations through public test helpers. [Feed Collections test helpers](../../ffun/ffun/feeds_collections/tests/helpers.py) · [Entitlements test helpers](../../ffun/ffun/entitlements/tests/helpers.py)

  ```python
  # ffun.parsers.domain
  def parse_opml(data: str) -> list[FeedInfo]:
      return opml.extract_feeds(data)
  ```
