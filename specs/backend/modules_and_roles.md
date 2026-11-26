# Backend modules and roles

## Goal of the document

This document describes the Feeds Fun backend layout by module and role.

## Scope

This specification applies to Python source files under `ffun/ffun`.

## File and package layout

The backend layout follows `specs/programming/modules_and_roles.md`.
Each declared module is implemented as a Python package.

A declared top-level module named `ffun.<name>` MUST use `./ffun/ffun/<name>/` as its source directory.
A declared nested module MUST use the subdirectory of its parent module that matches the final component of its package name.

## Dedicated specifications

A module or role with requirements beyond its list entry SHOULD have a dedicated specification for those requirements.

A top-level module MAY have a dedicated specification at `specs/backend/modules/<module>.md`, where `<module>` is its package name without the `ffun.` prefix.
A role MAY have a dedicated specification at `specs/backend/roles/<role>.md`, where `<role>` is its lowercase name.

The goal of a dedicated specification MUST name the module or role it governs.
If a role has a source filename or path pattern, the goal SHOULD mention it.
The scope MUST state which code the specification governs.
Its requirements apply alongside the layout rules in this specification.

## Modules

A top-level module MUST own the definitions and behavior that directly implement its responsibilities.

- `ffun.api` owns the backend's HTTP entry points.
- The `ffun.api.spa` nested module owns the HTTP endpoints used by the frontend.
- `ffun.application` owns application construction and application-wide settings.
- `ffun.audit` owns the audit records produced by backend workflows.
- `ffun.auth` owns authentication and authorization logic.
- `ffun.benefits` owns benefit package templates and the benefit transactions that coordinate changes to purchased state and its corresponding entitlements.
- `ffun.cli` owns the command-line interface for managing the backend.
- `ffun.core` owns the domain-neutral technical infrastructure shared by backend modules. See `specs/backend/modules/core.md`.
- `ffun.data_protection` owns data protection and privacy-related behavior.
- `ffun.dispatcher` owns dispatching entries to tag processor queues and tracking per-processor entry processing status.
- `ffun.domain` owns the shared code that represents and supports foundational Feeds Fun domain concepts. See `specs/backend/modules/domain.md`.
- `ffun.entitlements` owns source-specific user entitlement state and merged effective entitlements.
- `ffun.extractors` owns rule-based extraction of feed metadata and entries from public sources.
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

## Roles

Paths in role placement rules are relative to the source directory of the file's most specific declared module.

An **orphaned file** is a Python file in a declared module whose path matches no placement rule for a role other than Public or Private.

- **Domain** — `domain.py` implements the business logic owned by its module. See `specs/backend/roles/domain.md`.
- **Entities** — `entities.py` defines types, semantic identifiers, enums, and entities that represent its module's concepts. See `specs/backend/roles/entities.md`.
- **Errors** — `errors.py` defines its module's exception types and error values. See `specs/backend/roles/errors.md`.
- **Migrations** — Python files matching `migrations/*.py` implement changes to the database schema and stored data. See `Schema Migrations` in `specs/backend/db.md`.
- **Operations** — `operations.py` implements the technical details of its module's communication with storage and other external systems. See `specs/backend/roles/operations.md`.
- **Settings** — `settings.py` defines how its module produces validated, typed settings from configuration inputs and defaults. See `specs/backend/roles/settings.md`.
- **Tests** — Python files under directories named `tests` at any depth contain their module's colocated tests and test support code. See `specs/backend/roles/tests.md`.
  The `make` Python submodule MAY appear only inside tests packages, as `<module>.tests.make`.
- **Utilities** — `utils.py` provides technical helpers that support its module's implementation.
- **Public** — Orphaned files in modules that permit this role contain public interfaces specific to their module.
- **Private** — Orphaned files in modules that permit this role contain implementation code specific to their module.

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

**Rationale:** A single public path gives callers a consistent way to import a definition.

**Example:** The Feeds module defines `Feed` in its public `entities.py` file.
A caller with access to that interface uses `from ffun.feeds.entities import Feed`.

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
