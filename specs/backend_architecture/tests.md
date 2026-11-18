# Backend test architecture

## Goal of the document

This document describes the architecture of Feeds Fun backend tests, including where tests live and how they relate to backend modules.

## Scope

The scope of this specification is limited to backend test organization and architectural testing expectations for Python code under `ffun/ffun`.
The [automated test conventions](../programming/tests.md), [Python test conventions](../python/tests.md), and [pytest conventions](../python/libs/pytest.md) apply to backend tests.

The following topics are out of scope:

- exact test framework configuration.
- exact fixture names.
- continuous integration configuration.
- package publishing checks.
- performance benchmarks.
- frontend Vitest tests.

## Dictionary

- `unit test` - a test focused on one backend module or one small group of closely related functions or entities.
- `integration test` - a test that checks multiple backend modules through a public boundary such as API handler execution, application setup, parser execution, feed loading, or command execution.

## Test module layout

API integration tests SHOULD live under the API package that owns the tested route or dependency boundary.

Command integration tests SHOULD live under `./ffun/ffun/cli/tests/` when command behavior is present.

## Test organization

Yoyo migration modules under module-local `migrations` packages do not need separate per-function test classes for their migration step functions.

## Domain operation re-exports

Some domain modules intentionally re-export operation functions with assignments like:

```python
get_entry = operations.get_entry
```

These assignments are public domain-level names, but the behavior belongs to the operation module.

When a domain module re-exports an operation function without wrapping it, the domain test class for that function SHOULD
contain only a minimal identity assertion that verifies the public name points to the operation function.

Example:

```python
class TestGetEntry:
    def test_reexports_operation(self) -> None:
        assert domain.get_entry is operations.get_entry
```

This re-export is an example of an explicit identity contract under the [Python test conventions](../python/tests.md#assertions).

Behavior tests for the re-exported function MUST live in the operation module's tests, not in the domain module's tests.
