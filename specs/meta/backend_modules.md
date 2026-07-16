# Backend module specification requirements

## Goal of the document

This document describes the common location, naming, structure, and content conventions for specifications of individual Feeds Fun backend modules.

## Scope

This specification applies to module specifications under `specs/backend_architecture/modules/`.

General specification style, backend-wide architecture, implementation package layout, and requirements that apply uniformly to all backend modules are out of scope.

## Dictionary

- `module specification` - a specification dedicated to the responsibilities and behavior of one top-level `ffun` backend module.
- `module-specific section` - a section that describes concepts or behavior unique to the module being specified.

## Location and identity

Each module specification MUST be stored as `specs/backend_architecture/modules/<module>.md`, where `<module>` matches the intended or existing top-level Python package name under `ffun/ffun/<module>/`.

A module specification MAY exist before its implementation package is created.

There MUST be at most one module specification for each top-level backend module.

The document's `h1` title MUST identify the module and end with `module`, such as `# Audit module` for `ffun.audit`.

A module specification MUST supplement the backend-wide architecture specifications. It MUST NOT repeat general package, database, entity, error, or test requirements unless it adds a module-specific constraint.

## Required structure

In addition to the sections required for every specification by `specs/meta/general.md`, a module specification MUST contain these top-level sections:

- `Module responsibility`.
- `Domain behavior`.

Standardized top-level sections MUST appear in this order:

1. `Goal of the document`.
2. `Scope`.
3. `Dictionary` [can be empty].
4. `Module responsibility`.
5. `Domain behavior`.
6. `Database schema` [can be empty].
7. `Domain interface` [can be empty].
8. `Audit records` [can be empty].
9. `Business events` [can be empty].

A section marked `[can be empty]` MAY contain no module requirements. In that case, the section MUST contain one plain-text sentence explaining why, such as `Module does not require persistent storage.`

Module-specific sections SHOULD be nested under `Domain behavior`. A module specification MAY use an additional top-level section when the concern is substantial, stable, and does not fit a standardized section.

## Standard sections

### `Module responsibility`

The `Module responsibility` section MUST identify the module's architectural role and the behavior, entities, storage, or integration boundaries it owns.

The section SHOULD identify important behavior that callers must access through the module boundary. It SHOULD NOT enumerate implementation files or private helpers.

### `Domain behavior`

The `Domain behavior` section MUST describe the module-specific concepts, invariants, state transitions, calculations, and workflows needed to implement the module correctly.

Distinct concepts or workflows SHOULD use nested sections. Transaction and concurrency requirements SHOULD stay with the workflow they constrain.

### `Database schema`

A module specification that defines persistent module-owned state MUST include a `Database schema` section.

The section MUST identify each owned table and its columns, types, primary keys, foreign keys, uniqueness rules, checks, and required indexes. It MUST distinguish source-of-truth state from derived or historical state when the module owns more than one form.

Each table SHOULD use a nested section named after the table.

Each table schema MUST be expressed as PostgreSQL DDL in a fenced `sql` code block. Markdown tables MUST NOT be used to define database schemas.

The SQL MUST include all specified columns, types, defaults, keys, foreign keys, uniqueness rules, checks, and indexes. Each column MUST have an adjacent SQL comment that describes its domain meaning. Comments MUST also explain intentionally templated identifiers and constraints whose purpose is not clear from their names.

Every `Database schema` section MUST explicitly address secondary indexes. Required secondary indexes MUST be expressed as `CREATE INDEX` or `CREATE UNIQUE INDEX` statements in the corresponding table subsection, next to the table DDL. Each index statement MUST have an adjacent SQL comment that explains the query or invariant it supports.

When a module requires no secondary indexes, the `Database schema` section MUST contain one plain-text sentence that states this and explains why.

Prose MAY accompany the SQL to explain ownership, derived-state behavior, or other requirements that cannot be expressed by DDL alone.

### `Domain interface`

A module specification SHOULD include a `Domain interface` section when another module needs a stable call contract that is not sufficiently described by the responsibility and behavior sections.

The section MUST describe public behavior through `ffun.<module>.domain`. It MAY define stable operation names, arguments, return values, transaction participation, and failure behavior when those details are part of the cross-module contract.

The section MUST NOT specify private helpers or expose the module's `operations` boundary to callers.

### `Audit records`

A module specification that defines concrete durable audit events for its workflows MUST include an `Audit records` section.

The section MUST define when each record is appended, its event name, actor and subject entity roles, required attributes, transaction boundary, and no-op behavior.

The section MUST NOT treat business-event logs as durable audit storage.

### `Business events`

A module specification that generates business events MUST include a `Business events` section.

The section MUST define each event name, the condition that generates it, its business-event user, and required attributes. It SHOULD distinguish effective-state events from source or request events when both exist.

## Dependency metadata

Depmesh MUST relate each module specification to Python files under the top-level backend module with the matching name.

The `governed_by` relation for `ffun/ffun/<module>/**/*.py` MUST include `specs/backend_architecture/modules/<module>.md` when that specification exists.

The reverse `governs` relation for a module specification MUST include existing Python files under `ffun/ffun/<module>/`.

All module specifications MUST be governed by this specification through depmesh. These relationships SHOULD use generic name-based rules rather than one rule per module.
