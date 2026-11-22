# Operations role

## Goal of the document

This document describes requirements for Python code with the Operations role (`operations.py`) in the Feeds Fun backend.

## Scope

This specification applies to Python files with the Operations role in the Feeds Fun backend.

## Operation functions

Operation functions SHOULD provide individual actions that code with the Domain role in the same module can compose into workflows.

## Function names

Operation function names MUST describe caller-visible semantics rather than SQL statements or other implementation mechanisms.

- `load_<object>` MUST be used to retrieve or materialize data from storage or an external system.
  The object name SHOULD use singular or plural form according to the result cardinality.
  Selection qualifiers SHOULD follow the object as `_by_<key>` or `_for_<scope>`, while state qualifiers SHOULD precede it, as in `load_active_intervals`.
- `save_<object>` MUST be used to make a complete logical value durable when the operation may:
  - create the value.
  - replace the value.
  - reuse existing data.
  - perform an idempotent no-op.
- `update_<object-or-aspect>` MUST be used to mutate existing logical state.
  When only part of an object is changed, the name SHOULD identify that aspect, as in `update_feed_info`.

An operation that uses an upsert internally SHOULD still use `save_` or `update_` according to its caller-visible contract and SHOULD NOT expose the storage mechanism in its name.

## PostgreSQL transaction ownership

New code SHOULD NOT add transaction ownership to operation modules unless the operation module function is intentionally a low-level atomic primitive and no domain workflow boundary exists.

## PostgreSQL operation results and row mapping

The following rules apply to Python files with the Operations role that implement PostgreSQL-backed commands and queries.

Operation modules SHOULD return domain entities, typed ids, primitives, or dictionaries with clear ownership.
They SHOULD NOT leak raw persistence details into API handlers when a domain entity or a type defined at Python module scope can express the result.

Operation modules SHOULD provide small row mapper functions when database rows are converted into entities in more than one place.

See the [backend database architecture](../db.md) for PostgreSQL-specific rules.
