# Feeds Fun specification overview

## Goal of the document

This document lists Feeds Fun specification documents and specification directories, and briefly describes their purpose.

## Scope

The scope of this specification is limited to the specification index.

Detailed requirements for individual specifications are out of scope except for brief descriptions needed to keep the index useful.

## Specification directories

- `specs/` contains all project specifications used by depmesh governance rules.
- `specs/backend_architecture/` contains specifications related to backend architecture, Python conventions, database access, entities, tests, and errors.
- `specs/backend_architecture/modules/` contains specifications for individual backend modules.
- `specs/behavior/` contains specifications for externally visible application behavior.
- `specs/behavior/cli/` contains specifications for individual backend CLI command families.
- `specs/frontend_architecture/` contains specifications related to frontend architecture and tests.
- `specs/documentation/` contains specifications related to repository documentation artifacts.
- `specs/meta/` contains specifications related to requirements for specification documents.
- `specs/tools/` contains specifications related to development and agent tools.

## Specification documents

- `specs/intro.md` is this file and indexes all specification documents.
- `specs/dictionary.md` defines Feeds Fun and dependency metadata terms shared by multiple specifications.
- `specs/meta/general.md` defines general rules for project specification documents.
- `specs/meta/backend_modules.md` defines the common structure and dependency metadata requirements for backend module specifications.
- `specs/backend_architecture/modules_layout.md` describes backend package layout and ownership boundaries.
- `specs/backend_architecture/python.md` describes language-level implementation conventions for backend Python code.
- `specs/backend_architecture/db.md` describes backend database access, transactions, migrations, and database-focused testing practices.
- `specs/backend_architecture/entities.md` describes backend entity and data structure architecture.
- `specs/backend_architecture/errors.md` describes backend error and warning architecture.
- `specs/backend_architecture/tests.md` describes backend pytest test placement.
- `specs/backend_architecture/modules/audit.md` describes append-only audit persistence and its transactional domain interface.
- `specs/backend_architecture/modules/benefits.md` describes configured user-facing benefit packages, the all-source transaction and provider-provenance ledger, and atomic application to purchased states and entitlements.
- `specs/backend_architecture/modules/entitlements.md` describes entitlement source ownership, merging, persistence, audit history, and business events.
- `specs/backend_architecture/modules/locks.md` describes collision-free, transaction-scoped logical mutexes backed by PostgreSQL.
- `specs/backend_architecture/modules/one_time_purchases.md` describes internal one-time-purchase projections and lifecycle snapshots linked to causal benefit transactions.
- `specs/backend_architecture/modules/resources.md` describes interval-scoped per-user resource accounting, reservations, and finalized usage.
- `specs/backend_architecture/modules/subscriptions.md` describes internal purchased-subscription projections and lifecycle snapshots linked to causal benefit transactions.
- `specs/behavior/cli.md` describes behavior shared by the backend CLI command families.
- `specs/behavior/cli/entitlements.md` describes the CLI command family for managing and inspecting entitlements.
- `specs/behavior/cli/subscriptions.md` describes the CLI command family for managing and inspecting purchased-subscription snapshots.
- `specs/frontend_architecture/modules_layout.md` describes frontend source layout and ownership boundaries.
- `specs/frontend_architecture/components.md` describes frontend component contracts, global registration, naming, and composition conventions.
- `specs/frontend_architecture/tests.md` describes frontend Vitest test placement.
- `specs/documentation/readme.md` describes repository README expectations.
- `specs/documentation/changelog.md` describes changelog artifact expectations.
