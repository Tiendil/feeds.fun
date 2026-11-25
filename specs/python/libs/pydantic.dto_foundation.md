# Pydantic as the foundation of a DTO-centric architecture

## Goal of the document

This document describes how projects use a shared Pydantic base class for their DTOs.

## Scope

This specification applies wherever a project adopts Pydantic v2 as the foundation of a DTO-centric architecture.

## Shared base class

Projects that adopt this foundation follow the [DTO-centric architecture](../../programming/dto.md).

Projects MUST provide a shared Pydantic base class for their DTOs.
Project-owned DTOs MUST inherit from the shared base class unless they use Pydantic directly as permitted below.

DTOs MAY use Pydantic directly in cases such as these.

- configuration objects that mirror external input shapes.
- external transfer objects that intentionally mirror boundary-facing data shapes.
- compatibility with existing modules that have not been migrated to the shared base class.
- third-party interfaces that require a direct Pydantic model shape.

Very small internal helper values MAY use plain Python classes when Pydantic would add no practical value.

Project data structures MUST NOT use `dataclasses.dataclass`.

The shared base class MUST provide a copy-with-changes operation.

## Shared base class defaults

Projects SHOULD configure the shared base class with these defaults.

- strip surrounding whitespace from string values.
- validate default values.
- reject unknown fields.
- prefer immutable value objects where practical.
- avoid attribute-based construction unless a boundary explicitly needs it.
