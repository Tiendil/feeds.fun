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

## DTO architecture

Feeds Fun adopts a [DTO-centric architecture](../programming/dto.md) for its backend Python code.
Its shared DTO base follows [Pydantic as the foundation of a DTO-centric architecture](../python/libs/pydantic.dto_foundation.md).

## Semantic primitive types

Shared semantic primitive types SHOULD belong to the domain module.

A semantic identifier shared by independent domain modules MAY belong to the domain module when placing it in a narrower owning module would reverse the intended dependency direction or create a circular dependency.

## Entity ownership

Shared entity infrastructure MUST belong to the core module.

Shared domain primitive types and universal domain entities MUST belong to the domain module.

A module MAY expose entities from its public package interface when doing so simplifies imports for callers.

Public re-exports MUST NOT hide ownership. The defining module MUST remain clear from the source tree.

## Core domain entities

The core module MUST contain only shared entity infrastructure.

Core entity infrastructure MUST NOT contain domain-specific Feeds Fun concepts such as feeds, entries, rules, tags, users, or provider keys.

The domain layer MUST contain only universal entities for concepts shared by all or most other backend modules and dependency-neutral semantic identifiers shared across independent domain modules.

Domain entities MUST NOT contain subsystem-specific entities when those entities are required only by one narrower module.

## Configuration entities

Configuration entities SHOULD use Pydantic validation to reject malformed parsed data before it reaches lower layers.

Configuration settings objects MAY read configuration files from explicitly configured or declared paths when they act as the configuration-loading boundary.
They MUST restrict filesystem access to reading those files and MUST NOT perform open-ended file discovery or filesystem writes.

## Validation boundaries

Parsing layers SHOULD validate external data before creating entities that are used by lower layers.

Invalid external input MUST be reported through the error architecture instead of by returning partially valid entities.
