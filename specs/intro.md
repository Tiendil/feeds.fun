# Feeds Fun specification overview

## Goal of the document

This document lists Feeds Fun specification documents and specification directories, and briefly describes their purpose.

## Scope

The scope of this specification is limited to the specification index.

Detailed requirements for individual specifications are out of scope except for brief descriptions needed to keep the index useful.

## Specification directories

- `specs/` contains all project specifications used by depmesh governance rules.
- `specs/backend_architecture/` contains specifications related to backend architecture, database access, entities, tests, and errors.
- `specs/frontend_architecture/` contains specifications related to frontend architecture and tests.
- `specs/documentation/` contains specifications related to repository documentation artifacts.
- `specs/meta/` contains specifications related to requirements for specification documents.
- `specs/tools/` contains specifications related to development and agent tools.

## Specification documents

- `specs/intro.md` is this file and indexes all specification documents.
- `specs/dictionary.md` defines Feeds Fun and dependency metadata terms shared by multiple specifications.
- `specs/meta/general.md` defines general rules for project specification documents.
- `specs/backend_architecture/modules_layout.md` describes backend package layout and ownership boundaries.
- `specs/backend_architecture/db.md` describes backend database access, transactions, migrations, and database-focused testing practices.
- `specs/backend_architecture/entities.md` describes backend entity and data structure architecture.
- `specs/backend_architecture/errors.md` describes backend error and warning architecture.
- `specs/backend_architecture/tests.md` describes backend pytest test placement.
- `specs/frontend_architecture/modules_layout.md` describes frontend source layout and ownership boundaries.
- `specs/frontend_architecture/tests.md` describes frontend Vitest test placement.
- `specs/documentation/readme.md` describes repository README expectations.
- `specs/documentation/changelog.md` describes changelog artifact expectations.
- `specs/tools/prolog.md` describes agent-side use of SWI-Prolog for explicit reasoning.
