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

## General principles

The [automated test conventions](../programming/tests.md) apply to backend tests.

Tests MUST be written as part of the backend Python project.

Development-related test execution MUST happen through the project development container commands.

The preferred command form for running all backend tests is:

```bash
mise run backend:test
```

The preferred command form for running targeted backend tests is:

```bash
mise run backend:poetry -- run pytest <path>
```

Tests that require specific shared state MUST prepare that state at the start of the relevant test or with an autouse fixture at the test class or test module level.

Tests MUST NOT clean up shared state after themselves unless the developer explicitly requests cleanup behavior.

Tests MAY use any convenient functionality from the parent top-level module when testing behavior owned by that parent module. This includes private module-level helpers when the helper is the direct subject of the corresponding required test class.

Tests SHOULD use mocks, stubs, and monkeypatching as little as possible.

Tests MAY use Docker-provided local services when the tested behavior explicitly requires them.

Tests MUST NOT modify Docker configuration or runtime parameters.

Tests MAY inspect annotations only in dedicated architecture tests that validate a broad project-wide convention. Per-entity unit tests MUST NOT inspect annotations only to restate the entity declaration.

Tests MAY use `assert value is None` and `assert value is not None` when checking for `None`.

Tests MAY use `assert <value> is <other_value>` or `assert <value> is not <other_value>` for non-`None` values only when object identity is the explicit behavior under test, such as checking singleton values, module re-exports or aliases, or registry/cache/container APIs that promise to return the exact registered or stored object instance.

Tests with non-`None` identity assertions SHOULD make the identity contract clear through the test name, setup, or surrounding assertion context.

Tests MUST NOT use identity assertions for boolean values. Use `assert condition` instead of `assert condition is True`, and `assert not condition` instead of `assert condition is False`.

## Mocking

When a test must replace a Python collaborator, setting, method, or attribute, it SHOULD use the `pytest-mock` `MockerFixture`.

Use `mocker.patch("<import.path>", ...)` for imported module-level collaborators and settings.

Use `mocker.patch.object(...)` when replacing an attribute on an object or class already available in the test.

Use direct `unittest.mock.MagicMock` or `unittest.mock.AsyncMock` only for local fake objects or callables that are passed into the code under test.

Tests SHOULD NOT use pytest `monkeypatch` for ordinary Python attribute replacement; use `MockerFixture` for consistent cleanup and call assertions.

Tests MAY use specialized test tools for their own domain boundaries, for example `respx_mock` for HTTP client behavior.

## Test module layout

Each implementation module or submodule SHOULD have corresponding tests under a `tests` submodule owned by the same parent module.

The name of a test file MUST be built from the name of the tested module by adding the `test_` prefix.

Examples:

- `./ffun/ffun/core/logging.py` -> `./ffun/ffun/core/tests/test_logging.py`
- `./ffun/ffun/domain/urls.py` -> `./ffun/ffun/domain/tests/test_urls.py`
- `./ffun/ffun/integrations/plugins/github.py` -> `./ffun/ffun/integrations/plugins/tests/test_github.py`

API integration tests SHOULD live under the API package that owns the tested route or dependency boundary.

Command integration tests SHOULD live under `./ffun/ffun/cli/tests/` when command behavior is present.

Test data constructors reused by multiple test modules in the same package SHOULD live in `tests/make.py`.

`tests/make.py` SHOULD contain small factory functions that create valid entities, value objects, queue items, and other domain data for tests.

`tests/make.py` MUST NOT contain assertions or behavior-verification helpers.

Test helper functions reused by multiple test modules in the same package SHOULD live in `tests/helpers.py`.

`tests/helpers.py` SHOULD contain assertion helpers, cleanup helpers, and test workflow utilities.

`tests/helpers.py` MUST NOT contain ordinary domain data constructors when those constructors fit `tests/make.py`.

## Test organization

Tests SHOULD be organized around the tested function or tested class.

Each production module-level function MUST have a corresponding test class.

Yoyo migration modules under module-local `migrations` packages do not need separate per-function test classes for their migration step functions.

Each class SHOULD have a corresponding test class.

Test classes MUST use `Test<SubjectName>` naming, where `<SubjectName>` is the tested function or class name converted to PascalCase.

Examples:

- function `normalize_url` -> `class TestNormalizeUrl`.
- class `FeedLoader` -> `class TestFeedLoader`.
- class `Resource` -> `class TestResource`.

Tests for a class MUST group method tests inside the class's test class.

Tests for a class method MUST use this method name format:

```text
test_<method_name>__<test_name>
```

`<method_name>` MUST be the tested method name in snake case.

`<test_name>` MUST describe the execution path or behavior being verified in snake case.

Examples:

- `test_normalize__empty_value`.
- `test_process__provider_returns_error`.
- `test_replace_tags__circular_replacement`.

When a test class tests one module-level function, test methods MAY omit the function name and use this format:

```text
test_<test_name>
```

Examples:

- `TestNormalizeUrl.test_success`.
- `TestNormalizeUrl.test_invalid_scheme`.
- `TestNormalizeUrl.test_trailing_slash`.

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

This is a narrow exception to the general rule forbidding non-`None` identity assertions.

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
