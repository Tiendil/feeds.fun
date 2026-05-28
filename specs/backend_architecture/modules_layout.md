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

## Domain and product boundaries

Reusable domain modules SHOULD own generic behavior, storage, validation, and extension points for their domain area.
Product-specific choices that configure those reusable modules for Feeds Fun SHOULD stay outside the reusable domain
implementation. For example, `ffun.user_settings` owns the generic user settings machinery, while `ffun.product` owns
the concrete product setting definitions registered in that machinery.

## Module responsibilities

- `ffun.api` owns HTTP API endpoint wiring.
- `ffun.api.spa` owns API endpoints used by the frontend.
- `ffun.application` owns application construction and application-wide settings.
- `ffun.auth` owns authentication and authorization logic.
- `ffun.cli` owns command-line commands for managing the application.
- `ffun.core` owns framework-level base classes, utilities, logging, metrics, PostgreSQL helpers, plugins, and shared infrastructure.
- `ffun.data_protection` owns data protection and privacy-related behavior.
- `ffun.dispatcher` owns dispatching entries to tag processor queues and tracking per-processor entry processing status.
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
- `ffun.product` owns product-level configuration and registration glue that binds reusable domain modules to concrete product settings.
- `ffun.processors_quality` owns quality validation for tagging processors.
- `ffun.queues` owns persistent PostgreSQL-backed queue infrastructure.
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
- `domain` - submodule responsible for internal business logic related to the module's responsibilities.
- `entities` - submodule responsible for defining types and entities related to the module's responsibilities.
- `operations` - submodule responsible for low-level communication with storage, third-party services, and other external systems owned by the module.
- `settings` - submodule responsible for module-specific configuration.
- `migrations` - submodule containing database migrations owned by the module.
- `fixtures` - submodule containing reusable configuration or data fixtures owned by the module.
- `tests` - submodule containing module tests.
- `tests.make` - test-only submodule containing constructors for test objects related to the parent module.
- `tests.helpers` - test-only submodule containing reusable test setup, mutation, and workflow helpers.

The `errors`, `entities`, `migrations`, and `tests` submodules MUST follow the corresponding architecture specifications when they are present.

The shared `entities` submodule in `ffun.core` MUST define the common entity base used by higher-level modules.

## Sumbodules nuances

### `errors.py`

The `errors` submodule owns module-specific exception classes and error values.

Errors SHOULD express domain-level failure modes that callers can handle, not low-level persistence or library details.

Top-level modules MAY import another top-level module's `errors` submodule when they need to catch or raise errors owned by that module.

See `specs/backend_architecture/errors.md` for detailed error architecture rules.

### `operations.py`

The `operations` submodule owns low-level communication with systems outside the module's internal logic.

Operation functions MAY communicate with PostgreSQL, third-party services, provider APIs, HTTP endpoints, local external tools, or other infrastructure owned by the module's responsibility.

Operation functions SHOULD contain communication protocol details, low-level error translation, raw response handling, SQL, row-to-entity mapping, storage idempotency, and technical maintenance helpers owned by the module.

Operation functions SHOULD NOT own high-level business workflows. They SHOULD provide small communication primitives that the module's `domain.py` can compose.

Operation functions SHOULD NOT be imported by other top-level modules. Cross-module callers SHOULD use the owning module's `domain`, `entities`, or `errors` boundary instead.

See `specs/backend_architecture/db.md` for database-specific access, transaction, query, and migration rules.

### `entities.py`

The `entities` submodule owns module-specific types, semantic ids, enums, and entities that represent the module's concepts.

Entities SHOULD describe domain data and boundary data, not storage implementation details unless storage metadata is itself part of the domain concept.

Top-level modules MAY import another top-level module's `entities` submodule for shared boundary types.

See `specs/backend_architecture/entities.md` for detailed entity architecture rules.

### `domain.py`

The `domain` submodule owns the parent module's internal business logic and is the public behavior boundary for other top-level modules.

Domain functions SHOULD compose operation functions and other module boundaries into meaningful workflows, own new transaction boundaries for business workflows, make business decisions, convert or raise module-owned errors, and shape results for callers.

Domain functions SHOULD hide low-level communication details from callers. Callers should not need to know whether a workflow uses PostgreSQL, HTTP, providers, local tools, or multiple operation calls.

Top/input layers such as `ffun.api`, `ffun.api.spa`, and `ffun.cli` SHOULD call domain boundaries instead of operations when invoking business behavior.

When a domain-level function only exposes an operation function without adding behavior, `domain.py` SHOULD prefer a direct assignment alias, such as `save_feed = operations.save_feed`, instead of a trivial wrapper.

Domain wrappers SHOULD be used when they add real behavior, such as orchestration, validation, transaction ownership, fallback logic, caching, error conversion, or result shaping.

### `settings.py`

The `settings` submodule owns module-specific configuration parsing and defaults.

Settings classes SHOULD inherit from the shared settings base when they are loaded from environment or `.env` files.

Settings SHOULD validate configuration shape and expose typed values, but MUST NOT perform business operations, database queries, provider calls, or other runtime side effects.

### `utils.py`

The `utils` submodule owns small helpers that are not domain workflows and do not naturally belong to entities, operations, settings, or integration boundaries.

Utility functions SHOULD be pure or locally technical when practical. If a helper starts to encode module behavior, it SHOULD move to `domain.py`, `operations.py`, or a more specific submodule.

Top-level modules SHOULD avoid depending on another top-level module's `utils` submodule because utilities are not a stable cross-module boundary.

### `migrations.py`

The `migrations` submodule owns yoyo migration files for database schema or data changes owned by the parent module.

Migrations SHOULD stay close to the module that owns the changed tables or the main business reason for the change.

Migration files MUST define apply behavior and SHOULD define rollback behavior when rollback is reasonably possible.

See `specs/backend_architecture/db.md` for detailed schema ownership and migration rules.

### `tests.py`

The `tests` submodule owns colocated tests for the parent module and its submodules.

The `tests` submodule MUST follow the test architecture rules in `specs/backend_architecture/tests.md`.

Test files SHOULD mirror implementation module names with the `test_` prefix and organize test classes around the tested function or class.

See `specs/backend_architecture/tests.md` for detailed backend test architecture rules.

### `make.py`

The `make` submodule MAY appear only inside tests packages, as `<module>.tests.make`.

`tests.make` owns constructors and factory helpers for test objects related to the parent module.

Tests SHOULD put reusable object construction in `tests.make` instead of duplicating constructors across test files.

Production modules MUST NOT import `tests.make`.

### `helpers.py`

The `helpers` submodule MAY appear inside tests packages, as `<module>.tests.helpers`.

`tests.helpers` owns reusable test helpers that perform setup, mutate persisted test state, call module operations, or wrap common test workflows.

Object constructors and pure fake data factories SHOULD live in `tests.make`; helpers that perform actions or coordinate multiple calls SHOULD live in `tests.helpers`.

Production modules MUST NOT import `tests.helpers`.

## Cross-module dependencies

Backend modules have different dependency roles.

### Foundational modules

`ffun.core`, `ffun.domain`, and `ffun.product` are foundational modules. They own shared technical primitives,
cross-domain value types and utilities, and product-wide definitions that bind reusable domain mechanisms to Feeds Fun
product choices. Other backend modules MAY import any submodule of a foundational module when they need functionality
owned by that submodule. Foundational modules SHOULD avoid depending on domain-level or edge-layer modules, so shared
primitives do not acquire feature or interface dependencies.

### Domain-level modules

Most backend modules are domain-level modules. They own reusable business capabilities for one domain area and SHOULD
keep product-specific choices and application/interface wiring outside their implementation. Product-specific choices
SHOULD live in `ffun.product`; external interface concerns SHOULD live in edge-layer modules.

Production code in one domain-level module that needs types, values, behavior, or errors from another domain-level
module MUST use only that module's `domain`, `entities`, or `errors` submodules. Domain-level modules SHOULD expose
cross-module production API through those submodules when such API is needed.

A supported domain API MAY return or accept objects whose concrete classes are defined in the module's implementation
submodules. The cross-module dependency rule constrains the import path used by callers; it does not require every
object reachable through a public API to be defined in `domain`, `entities`, or `errors`. Callers MUST still import and
call the supported API through the allowed submodules, and MUST NOT import implementation submodules only to access the
same objects directly.

Tests MAY additionally import another domain-level module's `tests.make` and `tests.helpers` submodules for reusable
test data construction and setup helpers. Production code MUST NOT import another module's `tests`, `tests.make`, or
`tests.helpers` submodules.

Domain-level modules MUST NOT import implementation submodules from another domain-level module. Domain-level modules
MUST NOT import another domain-level module's `operations` submodule.

### Edge-layer modules

`ffun.application`, `ffun.api`, and `ffun.cli` are edge-layer modules. They adapt the backend to external entry points
such as application construction, HTTP APIs, and command-line interfaces. Edge-layer modules SHOULD follow the same
cross-module dependency rules as domain-level modules when they use domain-level modules. Foundational and domain-level
modules MUST NOT import edge-layer modules.

## Import paths

Code that imports objects, functions, classes, entities, constants, or other named Python definitions from another
module MUST import them from the module where they are defined. Importing a definition into a module for local use does
not make that module a supported import path for other callers. Callers MUST NOT import definitions through unrelated
intermediate modules unless a specification or a code comment explicitly documents that import path as a supported
public facade.

When a named definition moves to another module, all imports of that definition MUST be updated to the new definition
module as part of the same change. Obsolete compatibility import paths and re-export-only modules MUST be removed
instead of preserved as hidden alternate public paths.

## Data structures

Backend domain data structures SHOULD inherit from `ffun.core.entities.BaseEntity` unless a third-party interface or standard-library protocol requires another type.

Backend data structures MUST NOT use `dataclass` for domain entities.
