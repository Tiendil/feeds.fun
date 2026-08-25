# Backend module specification requirements

## Goal of the document

This document describes requirements for the structure, abstraction level, and content of specifications for individual Feeds Fun backend modules.

## Scope

This specification applies to specifications of high-level domain modules represented by `ffun.<name>`, where each module owns one cohesive project subdomain.
The `ffun.<name>` notation identifies the architectural boundary covered here; nested packages and other implementation-level code organization are out of scope.

It governs how those specifications distinguish durable domain requirements from implementation choices.
General specification style, backend-wide architecture, and policies owned by other specifications are out of scope.

## Dictionary

- `module specification` - a specification dedicated to one such high-level domain module's responsibility and observable behavior.
- `entity kind` - a durable category of domain entity owned by a module, independent of its representation as a class, record, table, or other implementation construct.
- `special module rule` - a module-specific architectural rule that differs from, or adds to, the rules that ordinarily apply to every backend module.
- `observable correctness guarantee` - an atomicity, concurrency, idempotency, ordering, or temporal property whose violation would change a domain outcome visible outside the module.

## Core principle

A module specification is a domain contract, not a map of the current code.
It MUST establish what the module owns, which entity kinds belong to that ownership, how those entities relate and evolve, and which module-specific behaviors must remain true.
It MUST remain accurate when internal APIs, persistence, data structures, and orchestration change without changing the domain behavior.

Requirements MUST be stated at the highest semantic level that still distinguishes correct behavior from an incorrect domain outcome.
They MUST describe invariants and effects rather than the mechanisms used to achieve them.

Every module-specific requirement MUST serve a current behavior, ownership boundary, relationship, or observable correctness guarantee.
Authors MUST perform a subtraction pass and remove a concept when removing it would not make a current valid outcome, invalid outcome, or ownership boundary ambiguous.

## Location and identity

Each module specification MUST be stored under `specs/backend_architecture/modules/` and MUST have a title that identifies the module.
There MUST be at most one specification for each top-level backend module.

The specification MAY exist before the module is implemented.
Its content MUST describe the intended domain contract rather than treating the absence or shape of the current implementation as a domain limitation.

## Required structure

After the opening sections required by `specs/meta/general.md`, every module specification MUST contain the following top-level sections, in this order:

1. `Module responsibility`
2. `Special module rules`
3. `Domain model`
4. `Domain behavior`
5. `Audit records`
6. `Business events`

An additional top-level section SHOULD be used only when a substantial current concern does not fit the standard sections.

Every required section MUST remain present when it has no module-specific requirements.
Such a section MUST contain a direct statement of absence, such as `This module has no special module rules.`, `This module owns no domain entity kinds.`, or `This module produces no audit records.`
It MUST NOT be filled by repeating backend-wide defaults.

Caller-visible capabilities MUST be described under `Domain behavior` and MUST NOT be placed in a separate operation catalogue.

## Standard sections

### `Scope`

The `Scope` section MUST identify the module's stable domain boundary and the general responsibility to which the specification applies.
It SHOULD distinguish an adjacent responsibility when readers could reasonably assign it to the wrong module.
It MUST NOT enumerate the module's current operations, implementation components, or an exhaustive collection of unrelated out-of-scope concerns.

### `Module responsibility`

The `Module responsibility` section MUST state which domain concepts, decisions, state, and invariants the module owns.
It MUST make ownership boundaries with collaborating modules clear enough that a policy has one authoritative owner.

This section MAY state that callers must respect a module-owned decision or use the module's domain boundary.
It MUST NOT turn that boundary into a catalogue of callable operations or repeat the ordinary boundary rules that apply to every backend module.

### `Special module rules`

The `Special module rules` section MUST contain only intentional differences from, or additions to, ordinary backend-module rules.
For example, a technical audit or locking module may state that it is intentionally used by other modules.
A purchased-state or entitlement module may state that its state changes are intended to participate in an atomic workflow owned by `ffun.benefits`.

A special rule MUST state the module-specific architectural requirement and the semantic boundary within which it applies, not the functions, transaction contexts, callbacks, or orchestration that implement it.
When one module owns a collaborative policy, that module MUST define the policy.
Participating modules MUST state only their participation in and respect for the owning module's decision.

When no special rule exists, the section MUST say so explicitly.

### `Domain model`

The `Domain model` section MUST identify the entity kinds necessary to describe the module's domain contract; implementation-only or technically motivated representations MUST be omitted.
For each identified entity kind, it MUST state the kind's semantic meaning, distinguishing invariants, or membership criteria needed to distinguish it from related kinds.
It MUST describe module-specific relationships and lifecycle invariants, including ownership, cardinality, identity stability, mutability, and historical status when those properties are part of current domain correctness.

Entity kinds and their relationships MUST be described semantically.
For example, a purchase may belong to exactly one user, its ownership may be immutable, and a historical transaction may be append-only.
The specification MUST NOT translate those facts into fields, foreign keys, row shapes, model inheritance, or persistence constraints.

A domain state or category MAY be named when the distinction is necessary to define current behavior.
Its programming-language symbol, numeric representation, or serialized value MUST NOT be specified.
An exhaustive domain set MUST be listed only when it is intentionally closed and the completeness of the set changes valid behavior.

### `Domain behavior`

The `Domain behavior` section MUST define the module-specific rules, state transitions, calculations, query semantics, and observable effects needed to preserve its domain contract.
It SHOULD organize closely related invariants together and omit behavior already governed by another module or by backend-wide specifications.

Capabilities MUST be expressed without prescribing an interface.
For example, a specification may require that records for one owner can be retrieved in a domain-significant order, but it MUST NOT name the operation, prescribe its arguments, or define its return shape.

Atomicity, concurrency, idempotency, ordering, and temporal guarantees MUST be included only when they define observable correctness.
Such a guarantee MUST state which domain effects succeed or fail together, which competing outcomes are allowed, or how authority and time affect acceptance.
It MUST NOT prescribe transaction ownership protocols, lock acquisition, retry loops, event callbacks, or persistence-operation order.

For example, `An older authoritative state cannot replace a newer state` is an observable temporal and concurrency invariant.
Requiring a particular lock, comparison query, exception type, and retry sequence to enforce it is not.
Likewise, `Repeating the same logical operation has no additional effect` is a domain idempotency guarantee; the key, index, or lookup sequence used to provide it is not.

### `Audit records`

The `Audit records` section MUST describe the module-specific rules for when a domain change produces durable audit evidence.
It MUST state the semantic purpose of that evidence and any module-specific atomicity, lifecycle, or no-op invariants.

### `Business events`

The `Business events` section MUST describe the module-specific rules for when a domain change produces a business event.
It MUST state the semantic purpose of the event and any module-specific ordering, temporal, or no-op invariants.

## Cross-module ownership

Each policy MUST be defined by the module that owns the corresponding domain decision.
A consuming module MUST state only the effect of respecting that decision when the relationship is necessary to understand its own behavior.
It MUST NOT duplicate the owner's policy, enumerate the owner's cases, or prescribe how the owner implements it.

Backend-wide rules such as ordinary module boundaries, error conventions, database practices, and test conventions MUST NOT be repeated in module specifications unless a module has a concrete exception.
Out-of-scope statements SHOULD be limited to adjacent responsibilities that are genuinely easy to confuse with the module's ownership.

## Excluded implementation detail

A module specification MUST NOT catalogue public operations or name functions, classes, enums, exceptions, callbacks, arguments, or private implementation components.
It MUST NOT specify signatures, parameter lists, return shapes, transaction-context protocols, or whether behavior is exposed through any particular programming-language construct.

Entity field inventories, data-transfer shapes, identifier representations, serialization formats, stable numeric enum values, database-oriented identifiers, string formats, size limits, and validation expressions MUST be omitted.
The specification MUST describe the domain distinction or validity rule they serve instead.

Tables, columns, indexes, constraints, migrations, row shapes, persistence-operation sequences, algorithms, and data structures MUST NOT appear in a module specification.
The specification also MUST NOT prescribe transaction, locking, retry, or event-delivery orchestration even when the current implementation uses those mechanisms.

Audit records and business events MUST be specified only as semantic effects when they are part of observable behavior.
By default, a module specification MUST state only which domain change requires or does not require durable evidence or notification, the semantic purpose of that effect, and relevant atomicity or no-op invariants.
It MUST NOT define exact event names, schemas, attribute inventories, serialization rules, callback protocols, or delivery procedures.

Test cases, fixtures, and implementation verification strategies MUST NOT be specified.
Current implementation limitations MUST NOT be promoted into permanent domain constraints, and speculative variants, compatibility provisions, or extension points without a current consumer MUST be omitted.

An otherwise excluded implementation detail MAY appear only when the developer explicitly requests that exact detail as part of the contract.
The specification MUST place an explanation next to the detail stating why it is required and which current observable behavior or architectural property would be lost without it.
Existing implementation shape, convenience, symmetry, debugging value, and hypothetical future use are not sufficient justifications.

## Examples and counterexamples

### Conforming examples

- `Each purchase belongs to exactly one user, and that ownership never changes` is an appropriate relationship and lifecycle invariant.
- `A failed state change leaves both the prior domain state and its audit history unchanged` is an appropriate atomicity invariant when partial success would be observable.
- `This module's state changes may participate in the benefit workflow's atomic domain change` is an appropriate special rule for a participating module.

### Non-conforming examples

- `The purchase row stores a user UUID in a non-null foreign-key column` is an implementation prescription and MUST NOT appear.
- `The write helper receives a transaction object and inserts the audit row before returning a callback` prescribes an interface and orchestration and MUST NOT appear.
- Repeating the benefit module's decision policy and transaction procedure in every participating module is not appropriate.

## Dependency metadata

Depmesh MUST relate every module specification to the implementation artifacts governed by it and MUST relate every module specification to this specification.
These relationships SHOULD use generic module-based rules rather than one rule per module.
