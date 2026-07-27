# Backend module specification requirements

## Goal of the document

This document describes the common location, naming, structure, abstraction level, and content conventions for specifications of individual Feeds Fun backend modules.

## Scope

This specification applies to module specifications under `specs/backend_architecture/modules/`.

Module specifications cover module responsibilities, public interfaces, observable behavior, and externally relevant effects.

General specification style, backend-wide architecture, implementation package layout, persistence schemas, internal algorithms, framework choices, and requirements that apply uniformly to all backend modules are out of scope.

## Dictionary

- `module specification` - a specification dedicated to the responsibilities and behavior of one top-level `ffun` backend module.
- `module-specific section` - a section that describes concepts or behavior unique to the module being specified.
- `public interface` - the module capabilities and semantic contracts available to other top-level backend modules.

## Abstraction boundary

A module specification MUST describe the module at the boundary visible to callers and other project components.
It MUST define module responsibilities, public capabilities, semantic inputs and results, failure conditions, behavioral invariants, state transitions, and observable effects at the highest level that remains precise and testable.

A module specification MUST NOT prescribe internal representations, orchestration, algorithms, persistence mechanisms, or framework-specific structures.
It MUST NOT name concrete entity, model, data-transfer-object, exception, or helper types, or the files and internal submodules that define them.
Public data contracts MUST instead be described through their semantic fields, invariants, and observable meaning.

Persistence requirements MAY specify observable properties such as durability, uniqueness, atomicity, isolation, and ordering.
They MUST NOT specify table, column, index, constraint, or migration names; SQL or DDL; query shapes; or the number and sequence of persistence operations.

A workflow sequence MUST be specified only when callers can observe the sequence or when its ordering is itself a required behavior.
Internal processing steps MUST otherwise be expressed as required outcomes and invariants.

Concrete public operation, audit-event, and business-event names MAY be specified when the name itself is an intentional stable contract.

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
6. `Public interface` [can be empty].
7. `Audit records` [can be empty].
8. `Business events` [can be empty].

A section marked `[can be empty]` MAY contain no module requirements. In that case, the section MUST contain one plain-text sentence explaining why, such as `Module does not produce business events.`

Module-specific sections SHOULD be nested under `Domain behavior`. A module specification MAY use an additional top-level section when the concern is substantial, stable, and does not fit a standardized section.

## Standard sections

### `Module responsibility`

The `Module responsibility` section MUST identify the module's architectural role and the behavior, state, or integration boundaries it owns.

The section SHOULD identify important behavior that callers must access through the module boundary. It SHOULD NOT enumerate implementation files or private helpers.

### `Domain behavior`

The `Domain behavior` section MUST describe the module-specific concepts, invariants, state transitions, calculations, and workflows needed to implement the module correctly.

Distinct concepts or workflows SHOULD use nested sections. Transaction and concurrency requirements SHOULD stay with the workflow they constrain.

The section MUST specify behavior through observable outcomes and MUST NOT prescribe internal algorithms, intermediate representations, helper operations, or persistence steps.

### `Public interface`

A module specification SHOULD define a public interface when another module needs a stable call contract that is not sufficiently described by the responsibility and behavior sections.

The section MUST describe public behavior through caller-visible capabilities and semantic contracts.
It MAY define stable operation names, inputs, results, transaction participation, and failure behavior when those details are part of the cross-module contract.

The section SHOULD specify accepted values, semantic result fields, failure conditions, transaction behavior, and observable lifecycle semantics when those details form the stable contract.
It MUST NOT require concrete entity, model, data-transfer-object, or exception type names.

The section MUST describe callable interfaces by their observable protocol. It MUST NOT require that a public callable is implemented as a class, function, decorated generator, or callable object unless callers depend on that distinction through type identity, inheritance, instance reuse, introspection, or another explicitly documented contract.

The section MUST NOT specify private helpers, internal submodules, or implementation-only operations.

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
