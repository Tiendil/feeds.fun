# Backend entity architecture

## Goal of the document

This document describes the architecture of Feeds Fun backend entities and data structures used to pass domain, configuration, integration, and command information between backend modules.

## Scope

The scope of this specification is limited to architectural requirements for Python data structures under `ffun/ffun` that represent Feeds Fun concepts.

The following topics are out of scope:

- exact class names.
- exact constructor signatures.
- frontend data models.
- database table schemas.
- external response schema details.
- parser and loader algorithms.
- validation rules already specified by module behavior.

## Dictionary

- `entity` - a typed Python object that represents one backend concept and can be passed across module boundaries.
- `value entity` - an entity whose equality is based on its data rather than object identity.
- `boundary entity` - an entity that is passed between modules with different responsibilities.
- `serialized representation` - a plain data representation prepared for an external protocol such as JSON, HTTP response data, logs, or persistent storage.

## General principles

Backend concepts MUST be represented as explicit typed entities before they cross backend module boundaries.

Boundary entities MUST NOT be represented as untyped dictionaries unless the data is already being prepared as a serialized representation.

Backend entities SHOULD use Pydantic v2 for structured data models.

Backend entities SHOULD keep behavior close to their data only when that behavior is pure and local to the entity.

Entities MUST NOT perform:

- filesystem access.
- process execution.
- terminal output.
- configuration file discovery.

Value entities SHOULD be immutable after construction when practical.

Entities that can be used for de-duplication SHOULD be hashable when practical.

## Pydantic baseline

The project accepts Pydantic v2 as the default dependency for entity modeling.

The project SHOULD provide shared base entity infrastructure owned by the core module.

Project entities SHOULD inherit from the shared base entity unless they have a specific reason to use Pydantic directly.

Direct Pydantic usage MAY be used for:

- configuration objects that mirror external input shapes.
- external transfer objects that intentionally mirror boundary-facing data shapes.
- compatibility with existing modules that have not been migrated to the shared base entity.
- third-party interfaces that require a direct Pydantic model shape.

Shared entity defaults SHOULD:

- strip surrounding whitespace from string values.
- validate default values.
- reject unknown fields.
- prefer immutable value objects where practical.
- avoid attribute-based construction unless a boundary explicitly needs it.

Entities SHOULD use Pydantic field metadata and validators for local field constraints, default factories, discriminators, and model invariants.

Entities SHOULD use Pydantic serialization methods at boundaries that need model dumps or JSON.

The shared base entity MUST provide a copy-with-changes operation.

Very small internal helper values MAY use plain Python classes with `__slots__` when Pydantic would add no practical value.

Project data structures MUST NOT use `dataclasses.dataclass`.

## Enumeration conventions

Closed sets of named values MUST be represented as Python enum classes.

String-valued external protocols, modes, provider names, setting kinds, category names, and similar closed type sets SHOULD use `enum.StrEnum`.

Integer-valued closed sets SHOULD use `enum.IntEnum` when the integer value is part of the external contract or persisted state.

Existing `str, enum.Enum` and `int, enum.Enum` classes MAY remain when they already define stable serialized or persisted values.

New or changed enum classes SHOULD use `enum.StrEnum` or `enum.IntEnum` instead of `str, enum.Enum` or `int, enum.Enum`.

Plain strings MUST NOT be used as the primary internal representation for values that have a finite configured, persisted, or specified set of allowed names.

Enum values that cross external boundaries MUST preserve the specified serialized or persisted value exactly.

## Semantic primitive types

Semantically specific primitive values MUST have semantically specific Python types before they cross module boundaries.

For example, a user id, feed id, entry id, tag id, URL, score rule id, or provider key MUST NOT be represented as an unqualified primitive value in entities or public function signatures when the value has a distinct Feeds Fun meaning.

Semantic primitive types SHOULD use `typing.NewType` when runtime behavior is identical to the underlying primitive.

Raw primitive types MAY be used at parsing, rendering, storage, and serialization boundaries where external data is converted into or out of project types.

Raw primitive types MAY be used inside local helper code when the value has already been validated or when adding a semantic type would not improve module-boundary clarity.

Semantic primitive types SHOULD be owned by the module that owns the corresponding backend concept.

Shared Feeds Fun semantic primitive types SHOULD belong to the domain module.

Domain-neutral semantic primitive types that are universal across backend modules MAY belong to the core module.

Module-specific semantic primitive types SHOULD belong to the owning module.

## Entity ownership

Shared entity infrastructure MUST belong to the core module.

Domain-neutral universal primitive types MAY belong to the core module when they are not Feeds Fun business concepts.

Shared domain primitive types and universal domain entities MUST belong to the domain module.

Module-specific entities MUST belong to the module that owns the corresponding responsibility.

External-boundary transfer entities MUST belong to the module that owns the external boundary.

Provider-specific request and response entities MUST belong to the module that owns the provider boundary.

A module MAY expose entities from its public package interface when doing so simplifies imports for callers.

Public re-exports MUST NOT hide ownership. The defining module MUST remain clear from the source tree.

## Core domain entities

The core module MUST contain only shared entity infrastructure and domain-neutral universal primitive types.

Core entity infrastructure and primitives MUST NOT contain domain-specific Feeds Fun concepts such as feeds, entries, rules, tags, users, or provider keys.

The domain layer MUST contain only universal entities for concepts shared by all or most other backend modules.

Domain entities MUST model universal Feeds Fun concepts independently from the concrete interface that created or renders them.

Domain entities MUST NOT depend on API route names, CLI option parsing, database table shapes, or concrete configuration file syntax.

Domain entities MUST NOT contain subsystem-specific entities when those entities are required only by one narrower module.

## Configuration entities

Configuration entities MAY represent parsed environment or settings data at the configuration loading boundary when their responsibility is to validate the input shape.

Configuration entities SHOULD use Pydantic validation to reject malformed parsed data before it reaches lower layers.

Configuration entities MUST preserve enough information to report useful configuration errors.

Configuration entities MUST NOT execute provider calls, feed loading, database queries, or other side effects.

Configuration entities MAY reference domain entities when the referenced concept has already been validated as a domain concept.

## Command entities

Command entities MUST represent parsed user intent before the command is executed.

Command entities MUST model command selection and parsed options independently from rendered output.

Command entities MUST NOT contain rendered output.

Command entities MUST NOT perform command execution.

## Data structure conventions

Ordered input from users, feeds, provider responses, and configuration files SHOULD be represented with ordered collections.

Sets MAY be used internally for de-duplication, but externally visible output order MUST be produced explicitly according to the relevant behavior or API specification.

Mappings keyed by semantic ids SHOULD use the semantic id type when possible.

Optional values MUST be represented with `None` instead of sentinel strings.

Serialized representations MUST be created at protocol boundaries and SHOULD be treated as write-only output data.

Serialized representations SHOULD be produced from Pydantic models through explicit boundary code, not by leaking Pydantic dump shapes into domain behavior.

Entity methods that return dictionaries for logging MUST return structured values with stable keys and MUST NOT contain presentation formatting.

## Validation boundaries

Parsing layers SHOULD validate external data before creating entities that are used by lower layers.

Pydantic model validation MAY validate local invariants that are always true for the entity.

Validation that requires filesystem access, configuration discovery, provider calls, database queries, feed loading, or command execution MUST live outside pure entity definitions.

Invalid external input MUST be reported through the error architecture instead of by returning partially valid entities.
