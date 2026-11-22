# Tests role

## Goal of the document

This document describes requirements for Python code with the Tests role (`tests/`) in the Feeds Fun backend.

## Scope

This specification applies to Python files with the Tests role under `ffun/ffun`.

## Factories and helpers

Object constructors and pure fake data factories SHOULD live in `tests.make`.
Helpers that perform actions or coordinate multiple calls SHOULD live in `tests.helpers`.
These placement preferences apply even when only one test file uses the factory or helper.

## Direct public function re-exports

A test of a direct public function re-export SHOULD only verify that the public name refers to the original function.
Tests dedicated to the function’s behavior MUST live with the Python module that defines it.

Example:

```python
class TestGetEntry:
    def test_reexports_operation(self) -> None:
        assert domain.get_entry is operations.get_entry
```

## Database-backed tests

These rules apply to tests of PostgreSQL-backed behavior.

Tests for database-backed behavior SHOULD use the real test PostgreSQL service provided by the development environment.

Operation tests SHOULD cover persistence-backed state changes, returned entities, idempotency, empty inputs, duplicate inputs, expected constraint failures, and important `RETURNING` empty-result paths.

Transactional workflow tests SHOULD verify both successful multi-step behavior and failure paths that must leave the database unchanged.

Tests SHOULD assert structured database-visible state when behavior depends on persistence.

Tests SHOULD use small explicit fixtures and helper functions owned by the relevant module.

Tests SHOULD NOT mock PostgreSQL for ordinary operation and domain tests when the behavior being tested is persistence behavior.
