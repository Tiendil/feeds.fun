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
- `fixture` - test data or setup used by one or more tests.
- `architecture test` - a test that verifies a backend-wide convention from an architecture specification.

## General principles

Tests MUST be written as part of the backend Python project.

Development-related test execution MUST happen through the project development container commands.

The preferred command form for running all backend tests is:

```bash
./bin/backend-tests.sh
```

The preferred command form for running targeted backend tests is:

```bash
./bin/backend-utils.sh poetry run pytest <path>
```

Tests SHOULD be deterministic for the same repository state and filesystem state.

Tests SHOULD prefer end-to-end coverage through public boundaries when that is practical for the behavior under test.

Tests SHOULD use mocks, stubs, and monkeypatching as little as possible.

Tests SHOULD prefer real project code, temporary files, local test services, and explicit fixtures over mocked collaborators.

Tests MUST NOT depend on external network access.

Tests MAY use Docker-provided local services when the tested behavior explicitly requires them.

Tests MUST NOT depend on user-specific files outside test-created temporary directories.

Tests MUST NOT modify Docker configuration or runtime parameters.

Tests SHOULD verify observable behavior and locally owned validation instead of implementation declarations such as annotations, imports, or exact helper types.

Static typing requirements SHOULD be enforced by static analysis, code review, or dedicated architecture checks, not by ordinary unit tests that inspect runtime annotations.

Tests MAY inspect annotations only in dedicated architecture tests that validate a broad project-wide convention. Per-entity unit tests MUST NOT inspect annotations only to restate the entity declaration.

Tests MUST NOT use identity assertions except for `None` checks. Use `assert value is None` and `assert value is not None` only when checking for `None`.

Tests MUST NOT use `assert <value> is <other_value>` or `assert <value> is not <other_value>` for non-`None` values. Use equality, membership, or an explicit behavioral assertion instead.

Tests MUST NOT use identity assertions for boolean values. Use `assert condition` instead of `assert condition is True`, and `assert not condition` instead of `assert condition is False`.

When a test uses `assert_logs` to verify branch-specific behavior, it MUST assert both expected log counts and zero counts for mutually exclusive branch log events.

## Mocking

Tests SHOULD prefer real project code, local services, explicit fixtures, test constructors, and small fakes over mocks.

When a test must replace a Python collaborator, setting, method, or attribute, it SHOULD use the `pytest-mock` `MockerFixture`.

Patches SHOULD be scoped to the test that needs them and SHOULD patch the name as it is looked up by the code under test.

Use `mocker.patch("<import.path>", ...)` for imported module-level collaborators and settings.

Use `mocker.patch.object(...)` when replacing an attribute on an object or class already available in the test.

Use direct `unittest.mock.MagicMock` or `unittest.mock.AsyncMock` only for local fake objects or callables that are passed into the code under test.

Tests SHOULD NOT use pytest `monkeypatch` for ordinary Python attribute replacement; use `MockerFixture` for consistent cleanup and call assertions.

Tests MAY use specialized test tools for their own domain boundaries, for example `respx_mock` for HTTP client behavior.

## Test module layout

Each implementation module or submodule SHOULD have corresponding tests under a `tests` submodule owned by the same parent module.

The name of a test file MUST be built from the name of the tested module by adding the `test_` prefix.

The structure of tests SHOULD mirror the implementation structure when that makes ownership clear.

Examples:

- `./ffun/ffun/core/logging.py` -> `./ffun/ffun/core/tests/test_logging.py`
- `./ffun/ffun/domain/urls.py` -> `./ffun/ffun/domain/tests/test_urls.py`
- `./ffun/ffun/integrations/plugins/github.py` -> `./ffun/ffun/integrations/plugins/tests/test_github.py`

Cross-module integration tests MAY live under the module that owns the public boundary being exercised.

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

Every possible execution path of a tested function or method MUST have a corresponding test method or parametrized test case.

Execution paths include:

- successful path.
- default-value path.
- empty-input path.
- invalid-input path.
- handled error path.
- warning-producing path.
- branch-specific path.

Tests MUST cover corner cases for each tested function or method.

Corner cases include:

- boundary values.
- empty collections and empty strings.
- missing optional values.
- duplicate values.
- unsupported values.
- malformed input.
- paths that do not exist.
- values that require normalization.
- repeated calls that may reveal state leaks.

## Entity tests

Entity tests SHOULD verify local invariants of entities.

Entity tests MUST verify behavior or invariants owned by the entity.

Entity tests SHOULD cover:

- entity-specific Pydantic field validation.
- entity-specific Pydantic model validation.
- non-trivial defaults or default factories.
- normalization behavior owned by the entity.
- entity-specific methods and properties.
- serialization or deserialization behavior owned by the entity.
- rejection of invalid values that the entity is responsible for rejecting.

Entity tests MUST NOT be added only to satisfy file-to-module layout symmetry.

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

Settings tests MUST verify behavior owned by the settings class or application setup boundary.

Settings tests SHOULD cover:

- supported settings structure.
- environment variable parsing.
- path normalization.
- invalid configuration failures.

Settings tests MUST NOT be added only to satisfy file-to-module layout symmetry.

Settings tests MUST NOT verify that literal default values are assigned unchanged when the settings class has no custom
parsing, validation, normalization, computed values, or application setup behavior.

For settings-only modules that contain only passive settings declarations, the absence of a matching
`tests/test_settings.py` file is acceptable and SHOULD be preferred over meaningless tests.

## Error tests

Error tests SHOULD verify behavior customized by concrete error classes.

Error tests SHOULD cover:

- custom error codes.
- custom message formatting.
- custom structured details.
- behavior added by an intermediate error class.

Error tests SHOULD NOT test unchanged inheritance from project or module root error classes.

Error tests SHOULD NOT test behavior inherited unchanged from the shared base error class.

Tests for exception boundaries SHOULD verify that expected low-level failures are converted into Feeds Fun errors, API errors, warning log records, or persisted error states.

Tests for exception boundaries SHOULD verify that `pydantic.ValidationError` from external input is converted into Feeds Fun errors, API errors, warning log records, or persisted error states.

API tests SHOULD verify that fatal errors are mapped to the expected HTTP status category and response body shape.

API tests SHOULD verify that unmapped project exceptions use the default failure category.

Command tests SHOULD NOT verify full CLI execution blocks, including Typer argument parsing, option validation, command
wiring, process exit behavior, and rendered command errors.

Full CLI execution blocks are assumed to be covered by manual testing.

Command module tests SHOULD cover only narrow helper functions that own non-trivial local behavior and can be tested
without invoking the command runner.

Worker and background-processing tests SHOULD verify that expected non-fatal problems are represented as warning log records, retries, or persisted processing states.

Worker and background-processing tests SHOULD verify that warning-producing behavior does not fail the whole operation when the operation can continue or persist a meaningful state.

## Behavior coverage

Architecture specifications are the source of expected backend-wide conventions.

Backend tests SHOULD cover examples and rules in architecture specifications when the corresponding behavior is implemented and runtime-testable.

Configuration and application setup tests SHOULD cover:

- application initialization failures.

API tests SHOULD cover:

- route behavior.
- dependency behavior.
- authentication and authorization boundaries.
- request validation.
- response shape for stable API contracts.
- warnings.
- errors and status categories.

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

Tests that need files SHOULD create those files in temporary directories.

Tests SHOULD keep fixture data as small as possible while preserving the behavior being verified.

Inline fixture data SHOULD be preferred for short configuration files and short expected outputs.

Reusable fixture files MAY be added when inline data would obscure the test.

Fixture paths SHOULD use forward slashes in expected normalized identifiers.

Tests that change the current working directory MUST restore it before the test ends.

## Assertions

Tests SHOULD assert structured values before rendered text when structured values are available.

Rendered output tests SHOULD assert exact output only for stable API, CLI, or persisted-state contracts.

Rendered output tests MAY assert selected lines, fields, or records when exact text is intentionally outside the relevant specification.

API response tests SHOULD parse response bodies before asserting response contents.
