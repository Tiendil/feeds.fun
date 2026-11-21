# Backend layers and slices

## Goal of the document

This document describes the Feeds Fun backend layout by layer and slice.

## Scope

This specification applies to Python source files under `ffun/ffun`.

## File and package layout

The backend layout follows the [shared layers and slices specification](../programming/layers_and_slices.md).

A declared top-level slice named `ffun.<name>` MUST use `./ffun/ffun/<name>/` as its source directory.
A declared sub-slice MUST use the subdirectory of its parent slice that matches the final component of its package name.

## Slices

A top-level slice MUST own the definitions and behavior that directly implement its responsibilities.

- `ffun.api` owns the backend's HTTP entry points.
- `ffun.application` owns application construction and application-wide settings.
- `ffun.audit` owns the audit records produced by backend workflows.
- `ffun.auth` owns authentication and authorization logic.
- `ffun.benefits` owns benefit package templates and the benefit transactions that coordinate changes to purchased state and its corresponding entitlements.
- `ffun.cli` owns the command-line interface for managing the backend.
- `ffun.core` owns the domain-neutral technical infrastructure shared by backend slices.
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
- `ffun.product` owns product-specific definitions and behavior with no more specific domain owner when multiple top-level slices need them directly for their own production responsibilities.
- `ffun.queues` owns the shared infrastructure for persistent work queues.
- `ffun.resources` owns per-user resource accounting and enforces caller-supplied limits on reservations.
- `ffun.scores` owns score rules and score calculation.
- `ffun.subscriptions` owns durable provider-independent purchased-subscription identities, provider-subscription references, and lifecycle snapshots linked to causal benefit transactions.
- `ffun.tags` owns tag normalization and validation logic that is not ontology storage.
- `ffun.user_settings` owns user-specific settings storage and behavior.
- `ffun.users` owns user storage and management.

### `ffun.api`

The `ffun.api.spa` sub-slice owns the HTTP endpoints used by the frontend.

### `ffun.core`

The shared `entities` submodule in `ffun.core` MUST define the common entity base used by higher-level modules.

### `ffun.domain`

Semantic identifiers owned by `ffun.domain` MUST be dependency-neutral and shared across independent domain modules.

A semantic identifier shared by independent domain-level slices SHOULD belong to `ffun.domain` when placing it in a narrower owning slice would reverse the intended dependency direction or create a cycle.

## Layers

Paths in layer placement rules are relative to the source directory of the file's most specific declared slice.

An **orphaned file** is a Python file in a declared slice whose path matches no placement rule for a layer other than Public or Private.

### Domain

`domain.py` belongs to the Domain layer.

The Domain layer implements the business logic owned by its slice.

Domain functions SHOULD hide low-level communication details from callers.
Callers should not need to know whether a workflow uses PostgreSQL, HTTP, providers, local tools, or multiple operation calls.

### Entities

`entities.py` belongs to the Entities layer.

The Entities layer defines types, semantic identifiers, enums, and entities that represent the slice's concepts.
Entities SHOULD describe domain data and boundary data.
Entities SHOULD omit storage implementation details unless storage metadata is itself part of the domain concept.

### Errors

`errors.py` belongs to the Errors layer.

The Errors layer defines the slice's exception types and error values.
Errors SHOULD express failures in terms of the slice's responsibilities so callers can decide how to respond.

Production errors MUST be defined in production modules.
Test modules MAY define test-only error classes when they need them to verify error handling.

See the [backend error architecture](errors.md) for detailed error rules.

### Migrations

Python files matching `migrations/*.py` belong to the Migrations layer.

The Migrations layer implements changes to the database schema and stored data.

Dedicated tests MAY be omitted for Yoyo migrations in the Migrations layer.

See the [database migration rules](db.md#schema-migrations) for migration ownership and behavior.

### Operations

`operations.py` belongs to the Operations layer.

The Operations layer implements the technical details of a slice's communication with storage and other external systems.

Operation functions SHOULD provide individual actions that the slice’s Domain layer can compose into workflows.

See the [backend database architecture](db.md) for PostgreSQL-specific rules.

#### Function names

Operation function names MUST describe caller-visible semantics rather than SQL statements or other implementation mechanisms.

- `load_<object>` MUST be used to retrieve or materialize data from storage or an external system.
  The object name SHOULD use singular or plural form according to the result cardinality.
  Selection qualifiers SHOULD follow the object as `_by_<key>` or `_for_<scope>`, while state qualifiers SHOULD precede it, as in `load_active_intervals`.
- `save_<object>` MUST be used to make a complete logical value durable when the operation may:
  - create the value.
  - replace the value.
  - reuse existing data.
  - perform an idempotent no-op.
- `update_<object-or-aspect>` MUST be used to mutate existing logical state.
  When only part of an object is changed, the name SHOULD identify that aspect, as in `update_feed_info`.

An operation that uses an upsert internally SHOULD still use `save_` or `update_` according to its caller-visible contract and SHOULD NOT expose the storage mechanism in its name.

### Settings

`settings.py` belongs to the Settings layer.

The Settings layer defines how a slice produces validated, typed settings from configuration inputs and defaults.
Modules in the Settings layer MUST NOT perform business operations, database queries, provider calls, or other runtime side effects.

The following rules apply to configuration entities and settings objects throughout `ffun/ffun`.

Configuration entities SHOULD use Pydantic to reject malformed data before it reaches lower layers.

Settings classes that load configuration from environment variables or `.env` files SHOULD inherit from `ffun.core.settings.BaseSettings` to keep environment loading consistent across slices.

A settings object acting as the configuration-loading boundary MAY read configuration files from explicitly configured or declared paths.
It MUST limit its filesystem access to reading those files.

### Tests

Python files under directories named `tests` at any depth belong to the Tests layer.

The Tests layer contains the slice's colocated tests and their support code.

The `make` submodule MAY appear only inside tests packages, as `<module>.tests.make`.

Object constructors and pure fake data factories SHOULD live in `tests.make`.
Helpers that perform actions or coordinate multiple calls SHOULD live in `tests.helpers`.
These placement preferences apply even when only one test module uses the factory or helper.

#### Direct public function re-exports

A test of a direct public function re-export SHOULD only verify that the public name refers to the original function.
Tests dedicated to the function’s behavior MUST live with the module that defines it.

Example:

```python
class TestGetEntry:
    def test_reexports_operation(self) -> None:
        assert domain.get_entry is operations.get_entry
```

### Utilities

`utils.py` belongs to the Utilities layer.

The Utilities layer provides technical helpers that support the slice's implementation.

### Public

An orphaned file belongs to the Public layer when its slice permits that layer.

The Public layer contains slice-specific public interfaces.

### Private

An orphaned file belongs to the Private layer when its slice permits that layer.

The Private layer contains slice-specific implementation modules.

## Permitted layer and slice pairs

Every declared slice MAY contain files assigned to any layer in this list.

- Domain.
- Entities.
- Errors.
- Settings.
- Tests.
- Utilities.

A slice MAY contain files in the Migrations layer for changes it owns under the database migration rules.
A slice MAY contain files in the Operations layer when it owns the interaction with an external system that those files implement.

Foundational slices and `ffun.product` MAY contain files in the Public layer.
Other declared slices MAY contain files in the Private layer.

## Dependencies and public interfaces

Dependency rules apply to direct Python imports across layer or slice boundaries.

### Import paths

For each definition it exposes at a boundary, a slice SHOULD provide a single public import path.

When importing a named Python definition, code MUST use its defining module or an import path explicitly documented as a public facade in a specification or code comment.
A caller SHOULD import a definition from its defining module when that module exposes the definition to the caller as part of a public interface.

**Rationale:** A single public path gives callers a consistent way to import a definition.

**Example:** The Feeds slice defines `Feed` in its public `entities` submodule.
A caller with access to that interface uses `from ffun.feeds.entities import Feed`.

When moving a definition makes an import path obsolete, the same change MUST update affected imports to a supported path and remove the obsolete path.

When a public interface exposes a definition from a private module, it MUST re-export the definition directly unless it adds behavior that belongs to its layer or slice.

**Rationale:** A direct re-export preserves the definition's identity and contract.

**Example:** `ffun.feeds.domain` exposes `save_feed` through `save_feed = operations.save_feed`.
A caller outside the slice with access to that interface uses `from ffun.feeds.domain import save_feed`.

**Example:** `ffun.library.domain` wraps `operations.unlink_all` to own the transaction.

### Public import interfaces

A slice MUST expose public interfaces only through modules assigned to a layer unless this specification explicitly allows a broader set of modules for that slice.
A module is private to its slice unless explicitly declared a public interface.

The submodules in this list are public interfaces of the slices that contain them.

- `domain`.
- `entities`.
- `errors`.

Modules in the Public layer are public import interfaces for functionality owned by their slice.
Other production modules in foundational slices and `ffun.product` are also public import interfaces for functionality owned by their slice.

A module in the Private layer MAY be imported only by a module directly assigned to the same slice.

All `tests.make` and `tests.helpers` submodules are public interfaces for code in another slice’s Tests layer.

Backend production code MUST NOT import `tests.make` or `tests.helpers`.

### Layer dependencies

Layer dependency rules apply only to imports between different layers when both files belong directly to the same slice.

Within that scope, modules in any layer MAY import modules in Public or Private.
Modules in Public or Private MAY import modules in any layer except Tests.
Other imports within that scope are allowed only when their direction is listed below.

- Domain: Entities, Errors, Operations, Settings, Utilities
- Entities: Errors, Utilities
- Errors: Entities
- Operations: Entities, Errors, Settings, Utilities
- Settings: Entities
- Tests: Domain, Entities, Errors, Operations, Settings, Utilities
- Utilities: Entities, Errors, Settings

### Slice roles

#### Role definitions

- **Foundational slices** provide shared technical infrastructure or foundational domain concepts.
- **Shared-service slices** provide common services for backend slices.
- **Edge slices** own boundaries through which external callers start or use the backend.
- **Domain-level slices** implement backend capabilities and workflows within their areas of responsibility.

#### Role membership

- Foundational: `ffun.core`, `ffun.domain`
- Shared-service: `ffun.audit`, `ffun.locks`, `ffun.queues`
- Edge: `ffun.api`, `ffun.application`, `ffun.cli`, and their sub-slices at any depth
- Domain-level: every other declared top-level slice except `ffun.product`

### Slice dependencies

A dependency between slices is allowed only when this specification permits its direction.

- Foundational: Foundational
- Shared-service: Foundational, Shared-service
- Domain-level: Foundational, Shared-service, Domain-level, `ffun.product`
- `ffun.product`: Foundational, Shared-service, Domain-level
- Edge: Foundational, Shared-service, Domain-level, `ffun.product`, Edge

Permissions to depend on `ffun.product` apply to the product-specific definitions and behavior the caller uses.

TODO Resolve how the foundational slice dependency rule applies to `ffun.core.migrations`.
The [Tach configuration](../../ffun/tach.toml) permits `ffun.core.migrations` to depend on `ffun.application`.

## Current boundary problems that should be fixed

- Break the API–Application slice cycle.
  Application imports API’s private root route handlers to register routes, and the root handlers import Application’s private settings to get the site domain. [Application wiring](../../ffun/ffun/application/application.py#L9) · [Root handlers](../../ffun/ffun/api/root/http_handlers.py#L8)

- CLI queue and metrics tests and Librarian’s background processor tests use Queues’ private `operations` module to prepare or inspect queues.
  The CLI queue test also imports the private `FakeQueueItem` test type. [CLI queue tests](../../ffun/ffun/cli/commands/tests/test_queues.py) · [CLI metrics tests](../../ffun/ffun/cli/commands/tests/test_metrics.py) · [Librarian background processor tests](../../ffun/ffun/librarian/tests/test_background_processors.py)

  ```python
  from ffun.queues import operations as q_operations
  from ffun.queues.tests.entities import FakeQueueItem
  ```

- Feed Discovery’s Domain module imports the Integrations slice’s private `settings` module to look up a plugin for the source URL.
  Integrations tests import Feed Discovery’s Entities module, forming a slice dependency cycle. [Feed Discovery Domain](../../ffun/ffun/feeds_discoverer/domain.py) · [Integrations plugin test](../../ffun/ffun/integrations/tests/test_plugin.py)

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

- Meta’s Domain module imports Ontology’s private `cache` module to look up tag IDs and UIDs during tag renormalization. [Meta Domain](../../ffun/ffun/meta/domain.py)

  ```python
  from ffun.ontology import cache as o_cache
  ```

- Tags and Ontology form a slice dependency cycle. Tag normalization uses Ontology’s tag types, and those types use Tags’ category type. [Tags Domain](../../ffun/ffun/tags/domain.py) · [Ontology Entities](../../ffun/ffun/ontology/entities.py)

  ```python
  # ffun.tags.domain
  from ffun.ontology.entities import NormalizedTag, RawTag

  # ffun.ontology.entities
  from ffun.tags.entities import TagCategories
  ```

- Ontology’s Domain module imports Tags’ private `converters` module to turn tag UIDs into display names. [Ontology Domain](../../ffun/ffun/ontology/domain.py)

  ```python
  from ffun.tags import converters
  ```

- Users test fixtures, factories, and Domain and Operations tests import `primary_oidc_service_id` from Auth’s private `settings` module for test user mappings.
  The Operations tests also import `single_user_service_id` to test mappings across providers. [Fixtures](../../ffun/ffun/users/tests/fixtures.py) · [Factories](../../ffun/ffun/users/tests/make.py) · [Domain tests](../../ffun/ffun/users/tests/test_domains.py) · [Operations tests](../../ffun/ffun/users/tests/test_operations.py)

  Auth’s Domain module imports Users’ Domain module, so these test imports form a slice dependency cycle. [Auth Domain](../../ffun/ffun/auth/domain.py)

  ```python
  # ffun.users.tests.test_operations
  from ffun.auth.settings import primary_oidc_service_id, single_user_service_id

  # ffun.auth.domain
  from ffun.users import domain as u_domain
  ```

- Google’s Entities module imports its chat request and response base classes through LLM Framework’s private `provider_interface` module. Both classes are defined in LLM Framework’s public `entities` module. [Google Entities](../../ffun/ffun/google/entities.py) · [LLM Framework Entities](../../ffun/ffun/llms_framework/entities.py)

  ```python
  from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse
  ```

- Librarian’s processor tests import `ChatResponseTest` from LLM Framework’s private `provider_interface` module to build fake responses for a tag deduplication test. [Librarian processor tests](../../ffun/ffun/librarian/processors/tests/test_llm_general.py)

  ```python
  from ffun.llms_framework.provider_interface import ChatResponseTest
  ```

- Dispatcher’s cache tests import LLM Framework’s private provider registry to set API key statuses.
  Google and OpenAI’s provider tests import the private `Statuses` class in their key-status tests. [Dispatcher cache tests](../../ffun/ffun/dispatcher/tests/test_entries_cache.py) · [Google provider tests](../../ffun/ffun/google/tests/test_provider_interface.py) · [OpenAI provider tests](../../ffun/ffun/openai/tests/test_provider_interface.py)

  ```python
  from ffun.llms_framework.providers import llm_providers
  from ffun.llms_framework.keys_statuses import Statuses
  ```

- Processor Quality’s Domain module imports Librarian’s private processor registry and context class to run a configured processor on its quality route. [Processor Quality Domain](../../ffun/ffun/processors_quality/domain.py)

  ```python
  from ffun.librarian.background_processors import processors as ln_processors
  from ffun.librarian.processors.base import ProcessorContext
  ```

- Core and Domain form a slice dependency cycle. Core’s test helpers import Domain’s `UserId` for log assertions, and Domain’s entities use Core’s base types. [Core test helpers](../../ffun/ffun/core/tests/helpers.py) · [Domain Entities](../../ffun/ffun/domain/entities.py)

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

- Several modules use shared types through incidental imports in another module. The types are defined in `ffun.domain.entities`. The following modules expose the names as a side effect of importing them for local use.

  - Feeds Entities exposes `FeedId`, which Loader Domain imports directly and SPA Entities accesses through the Feeds Entities module. [Loader Domain](../../ffun/ffun/loader/domain.py) · [SPA Entities](../../ffun/ffun/api/spa/entities.py)
  - Feed Collections Entities exposes `CollectionId`, which Loader tests import and SPA Entities accesses through the Feed Collections Entities module. [Loader tests](../../ffun/ffun/loader/tests/test_domain.py) · [SPA Entities](../../ffun/ffun/api/spa/entities.py)
  - LLM Framework Entities exposes `LLMTokens` and `USDCost`, which LLM Framework Domain and tests import. Google, OpenAI, and Librarian tests also import `LLMTokens` through this module. [LLM Framework Domain](../../ffun/ffun/llms_framework/domain.py) · [Google provider tests](../../ffun/ffun/google/tests/test_provider_interface.py) · [OpenAI provider tests](../../ffun/ffun/openai/tests/test_provider_interface.py) · [Librarian processor tests](../../ffun/ffun/librarian/processors/tests/test_llm_general.py)
  - Tags Entities exposes `TagUidPart`, which Tags’ utilities tests import. [Tags utilities tests](../../ffun/ffun/tags/tests/test_utils.py)
  - Users Entities exposes `UserId`, which Auth Domain uses as `u_entities.UserId`. [Auth Domain](../../ffun/ffun/auth/domain.py)

  ```python
  # ffun.loader.domain
  from ffun.feeds.entities import Feed, FeedId, FeedState
  ```

- Queues’ package initializer declares a public import path for five names already defined in its public Entities module. The initializer belongs to the Private layer. [Queues initializer](../../ffun/ffun/queues/__init__.py)

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
