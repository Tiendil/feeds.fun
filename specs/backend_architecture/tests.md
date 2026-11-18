# Backend test architecture

## Goal of the document

This document describes the architecture of Feeds Fun backend tests, including where tests live, how they relate to backend modules, and how they cover entities and errors.

## Scope

The scope of this specification is limited to backend test organization and architectural testing expectations for Python code under `ffun/ffun`.

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

## Test execution

The [automated test conventions](../programming/tests.md), [Python test conventions](../programming/python.tests.md), and [pytest conventions](../programming/libs/pytest.md) apply to backend tests.

Development-related test execution MUST happen through the project development container commands.

The preferred command form for running all backend tests is:

```bash
mise run backend:test
```

The preferred command form for running targeted backend tests is:

```bash
mise run backend:poetry -- run pytest <path>
```

## Test module layout

API integration tests SHOULD live under the API package that owns the tested route or dependency boundary.

Command integration tests SHOULD live under `./ffun/ffun/cli/tests/` when command behavior is present.

## Test organization

Tests SHOULD be organized around the tested function or tested class.

Each production module-level function MUST have a corresponding test class.

Yoyo migration modules under module-local `migrations` packages do not need separate per-function test classes for their migration step functions.

Each class SHOULD have a corresponding test class.

Test-only helper functions do not need corresponding test classes.

Standalone test functions SHOULD be used only for module-level invariants or file-level checks that do not naturally belong to one tested function or class.

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

This re-export is an example of an explicit identity contract under the [Python test conventions](../programming/python.tests.md#assertions).

Behavior tests for the re-exported function MUST live in the operation module's tests, not in the domain module's tests.

## Entity tests

Entity tests MUST NOT verify that constructor arguments are assigned to fields unchanged.

Entity tests MUST NOT verify simple Pydantic model construction when the entity has no custom validators, constrained
fields, non-trivial defaults, normalization, serialization, computed properties, or entity-specific methods.

Entity tests MUST NOT verify plain `NewType`, enum member existence, or passive data-container fields unless the module
owns non-trivial conversion, validation, serialization, persistence compatibility, API compatibility, or external-input
compatibility behavior for them.

For entity-only modules that contain only passive entities, the absence of a matching `tests/test_<module>.py` file is
acceptable and SHOULD be preferred over meaningless tests.

Entity tests SHOULD NOT test behavior inherited unchanged from the shared base entity.

Entity tests SHOULD NOT test trivial Pydantic behavior unless the entity customizes that behavior.

Entity tests MUST NOT require filesystem access unless the entity itself explicitly owns path normalization that depends on filesystem semantics.

Entity tests MUST NOT verify API or CLI rendering.

Entity tests MAY assert `pydantic.ValidationError` for invalid low-level model construction.

## Settings tests

Settings tests MUST NOT verify that literal default values are assigned unchanged when the settings class has no custom
parsing, validation, normalization, computed values, or application setup behavior.

For settings-only modules that contain only passive settings declarations, the absence of a matching
`tests/test_settings.py` file is acceptable and SHOULD be preferred over meaningless tests.

## Error tests

Error tests SHOULD NOT test unchanged inheritance from project or module root error classes.

Error tests SHOULD NOT test behavior inherited unchanged from the shared base error class.

Tests for exception boundaries SHOULD verify that expected low-level failures are converted into Feeds Fun errors, API errors, warning log records, or persisted error states.

Tests for exception boundaries SHOULD verify that `pydantic.ValidationError` from external input is converted into Feeds Fun errors, API errors, warning log records, or persisted error states.

API tests SHOULD verify that unmapped project exceptions use the default failure category.

Command tests SHOULD NOT verify full CLI execution blocks, including Typer argument parsing, option validation, command
wiring, process exit behavior, and rendered command errors.

Full CLI execution blocks are assumed to be covered by manual testing.

Command module tests SHOULD cover only narrow helper functions that own non-trivial local behavior and can be tested
without invoking the command runner.

## Behavior coverage

Architecture specifications are the source of expected backend-wide conventions.

Backend tests SHOULD cover examples and rules in architecture specifications when the corresponding behavior is implemented and runtime-testable.

Parser and integration tests SHOULD cover:

- supported feed, entry, site, and OPML input forms.
- source-specific integration behavior.
- malformed input.
- provider failures.
- normalization of external data.

Worker and operation tests SHOULD cover:

- persistence-backed state changes.
- idempotency where repeated calls are expected.
- retryable failures.
- persisted error states.
- coordination across module public boundaries.

Command helper tests SHOULD cover:

- parsing or validation helpers extracted from commands.
- output-shaping helpers when they return structured data.
- command-adjacent workflows that are callable without invoking the CLI runner.
- warnings or errors produced by those narrow helpers.

## Fixtures and temporary data

Fixture paths SHOULD use forward slashes in expected normalized identifiers.
