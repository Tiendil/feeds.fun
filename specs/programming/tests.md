# Automated test conventions

## Goal of the document

This document describes conventions for organizing automated software tests and verifying program behavior.

## Scope

This specification applies to automated software tests across programming languages and test frameworks.

## Dictionary

- `fixture` - test data or setup used by one or more tests.

## General principles

Tests SHOULD be deterministic for the same repository state and filesystem state.

Deterministic tests let developers reproduce failures.

Tests SHOULD prefer a real current-time value as the baseline for time-related cases when the exact calendar date is not part of the behavior under test.
Hard-coded calendar datetimes SHOULD be used only when the specific date, month, year, weekday, or timezone boundary is itself relevant to the tested behavior.

A shared baseline lets relative-time assertions use the same reference as their inputs.
Specific calendar dates let tests exercise the boundaries that matter to the behavior.

Tests MUST NOT depend on external network access.

Tests MAY use local services provided by the development environment when the tested behavior explicitly requires them.

Tests MUST NOT modify the development environment's configuration or runtime parameters unless the developer explicitly permits it.

Tests MUST NOT depend on user-specific files outside test-created temporary directories.

Tests SHOULD prefer coverage through public module boundaries when that is practical for the behavior under test.

Tests SHOULD prefer end-to-end coverage through public boundaries when that is practical for the behavior under test.

Tests SHOULD exercise behavior of other top-level modules through their public boundaries.

Tests MAY use internal functionality from the module that owns the behavior under test.
Tests MAY exercise a private helper directly when that helper owns the behavior being verified.

Tests SHOULD verify observable behavior and locally owned validation instead of implementation declarations or private implementation details.

**Example:** A test for URL normalization checks the returned URL and whether invalid input is rejected.

**Counterexample:** Checking which private helper was called, which module was imported, or what type annotation was written would test implementation details.

Public boundaries and behavioral assertions keep tests useful when implementation details change.

Tests that inspect program structure to enforce a project-wide convention MUST be dedicated architecture tests.
Examples of program structure include imports, field declarations, and type annotations where the language supports them.

Static typing requirements SHOULD be enforced by static analysis, code review, or dedicated architecture checks.
Ordinary unit tests SHOULD NOT inspect runtime representations solely to restate type declarations.

**Example:** The type checker can verify that a parser returns its declared result type, while a unit test checks that valid input parses correctly.

**Counterexample:** Reading a Python return annotation or asserting a TypeScript object’s keys solely to mirror its interface would duplicate the declaration.

Tests SHOULD use mocks, stubs, and spies as little as possible.

Tests SHOULD prefer real project code, temporary files, local test services, explicit fixtures, test constructors, and small fakes over mocked collaborators.

Real collaborators reduce the risk that a test passes against behavior that differs from production.

Patches SHOULD be scoped to the test that needs them and SHOULD patch the name as it is looked up by the code under test.

## Test module layout

When a project is organized into modules, tests SHOULD live with the module that owns the behavior under test, using the project's conventions for test directories or packages.

Projects organized into modules MUST use dedicated test directories where their test tooling supports them.

Tests for implementation files in one directory SHOULD live in a test subdirectory of that directory.

The structure of tests SHOULD mirror the implementation structure when that makes ownership clear.

Cross-module integration tests MAY live under the module that owns the public boundary being exercised.

Mirroring the implementation helps developers find the tests for a module.

A test file for a single implementation module MUST derive its name from that module's name using the project's test file naming convention.

## Test organization

Tests SHOULD be grouped by the function, class, or other program element whose behavior they verify.
Standalone tests SHOULD be used only for module-level invariants or file-level checks that do not naturally belong in one of those groups.

Test names MUST describe the execution path or behavior being verified.

Tests SHOULD prefer separate tests for orthogonal execution paths or validation cases instead of one combined test that verifies all cases at once.

**Example:** `test_a` and `test_b` are better than `test_a_or_b` when `a` and `b` describe independent behavior.

Focused tests help readers identify which behavior failed.

## Test coverage

Every execution path required by the behavior’s contract MUST have a corresponding test or parametrized test case.

Execution paths include:

- successful path.
- default-value path.
- empty-input path.
- invalid-input path.
- handled error path.
- warning-producing path.
- branch-specific path.
- security-sensitive path.

Tests MUST cover corner cases for each tested behavior.

Corner cases include:

- boundary values.
- empty collections and empty strings.
- missing optional values.
- duplicate values.
- unsupported values.
- malformed input.
- paths that do not exist.
- values that require normalization.
  - paths or URLs that require normalization.
- repeated calls that may reveal state leaks.

### Migrations

Migration-sensitive changes SHOULD be verified through tests that exercise the resulting operation behavior after migrations are applied.

### Entities

Entity tests SHOULD verify local invariants of entities.

Entity tests MUST verify only behavior or invariants owned by the entity.

Entity tests SHOULD cover:

- validation of individual values and invariants of the entity as a whole.
- non-trivial defaults or default factories.
- normalization behavior owned by the entity.
- entity-specific methods and properties.
- serialization or deserialization behavior owned by the entity.
- rejection of invalid values that the entity is responsible for rejecting.

Entity tests MAY assert that low-level model construction raises the modeling library’s validation exception for invalid input.

Entity tests MUST NOT require filesystem access unless the entity itself explicitly owns path normalization that depends on filesystem semantics.

Entity tests MUST NOT be added only to satisfy file-to-module layout symmetry.

### Configuration and application setup

Settings tests MUST verify behavior owned by configuration handling or application setup.

Settings tests SHOULD cover:

- supported settings structure.
- environment variable parsing.
- path normalization.
- invalid configuration failures.

Settings tests MUST NOT be added only to satisfy file-to-module layout symmetry.

Configuration and application setup tests SHOULD cover:

- application initialization failures.

### Error behavior

Error tests SHOULD verify the observable behavior defined for a specific error or error category.

Error tests SHOULD cover:

- custom error codes.
- custom message formatting.
- custom structured details.

Tests for exception boundaries SHOULD verify that expected low-level failures, including failures when validating external input, are converted into the errors, warnings, or persisted error states defined by the boundary’s contract.

### HTTP API implementations

API tests SHOULD cover:

- route behavior.
- dependency behavior.
- authentication and authorization boundaries.
- request validation.
- response shape for stable API contracts.
- warnings.
- errors and status categories.

API tests SHOULD verify that fatal errors are mapped to the expected HTTP status category and response body shape.

If an API defines a default error response, tests SHOULD trigger an error with no dedicated response and verify that the API returns the default.

### API clients

API-client tests SHOULD verify request construction, response parsing, and error handling at the API client boundary.

API-client tests MUST NOT call external network services.

When API-client tests need a mock for request or response handling, they SHOULD mock the transport boundary and exercise the client's request construction and response parsing.

### User interface tests

Component and view tests SHOULD cover the following behavior when the UI contract defines it.

- rendered text and attributes that are part of the component contract.
- emitted events.
- prop-driven branches.
- accessible states when the component owns them.
- security-sensitive rendering decisions.
- conditional rendering.
- user input handling.
- store interaction at component boundaries.
- error and empty states visible to users.

Component tests SHOULD NOT assert private component internals, exact child implementation structure, or CSS classes unless those values are part of a stable contract.

### CLI tests

Automated CLI tests SHOULD cover only helpers that own non-trivial behavior and can be tested without invoking the command runner.

Command helper tests SHOULD cover:

- parsing or validation helpers extracted from commands.
- output-shaping helpers when they return structured data.
- command-adjacent workflows that are callable without invoking the CLI runner.
- warnings or errors produced by those narrow helpers.

Full CLI execution is assumed to be covered by manual testing, including argument parsing, option validation, command wiring, exit behavior, and error output.

### Background processing

Worker and background-processing tests SHOULD verify that expected non-fatal problems are represented as warning log records, retries, or persisted processing states.

Worker and background-processing tests SHOULD verify that warning-producing behavior does not fail the whole operation when the operation can continue or persist a meaningful state.

## Shared resources

Tests that use a resource shared across tests MUST tolerate existing state unrelated to the behavior under test.
Tests MUST NOT reset a shared resource unless the reset is required to verify the behavior under test.

Tests MUST NOT clean up shared state after themselves unless the developer explicitly requests cleanup behavior.

A test for reading one record can create that record through the application and leave the other records in the shared database in place.

## Fixtures and temporary data

Tests that need files SHOULD create those files in temporary directories.

Tests SHOULD keep fixture data as small as possible while preserving the behavior being verified.

Inline fixture data SHOULD be preferred for short inputs and expected outputs.

Reusable fixture files MAY be added when inline data would obscure the test.

Expected normalized identifiers in test fixtures SHOULD use the separators specified by the normalization contract.

When the normalization contract does not specify a separator, expected path identifiers in test fixtures SHOULD use forward slashes.

A fixture for a format that specifies forward slashes can use `folder/file` as the expected identifier.

Tests MUST undo temporary runtime overrides that can affect other tests before the test ends.
Examples include changing the working directory, patching a function such as `window.fetch`, and installing fake timers.

Temporary files keep file-based setup isolated.
Small fixtures make the relevant data easy to see.

Tests MUST prepare any additional data they need at the start of the relevant test or through automatic setup that applies to that test.

### Application-owned state

Tests that can exercise a mutable in-memory component in isolation SHOULD use a fresh, test-owned instance for each test.

Tests MUST prepare and mutate application-owned state through the production code that owns the corresponding state transition and invariants.

Tests MUST NOT bypass production logic by writing directly to databases, files, queues, caches, or other application-owned state unless the developer explicitly approves the exception.

An approved exception MUST be documented next to the bypass and MUST explain why the required state cannot be produced through production code.

Tests MAY inspect application-owned state directly to assert observable effects; this permission does not allow direct mutation.

## Assertions

Tests SHOULD assert structured values before rendered text when structured values are available.

API response tests SHOULD parse response bodies before asserting response contents.

Tests MUST NOT use identity assertions for ordinary value checks.

Rendered output tests SHOULD assert exact output only when the exact output is part of a stable contract.

Rendered output tests MAY assert selected lines, fields, or records when exact text is intentionally outside the relevant specification.

Structured assertions focus on the values the contract guarantees.
Exact comparisons are useful when callers depend on the rendering itself.

Security-sensitive sanitization tests SHOULD assert both allowed output and removed unsafe input.

When a test uses logs to verify branch-specific behavior, it MUST assert both expected log counts and zero counts for mutually exclusive branch log events.

### Persistence

Persistence operation tests MUST verify the expected persisted effects when the behavior under test inserts or deletes rows, including the number of affected records when cardinality is part of the contract.

Tests for rejected writes, idempotent no-ops, or other paths whose contract includes unchanged persisted state MUST verify that invariant.

Assertions about persisted effects MUST isolate the operations responsible for those effects.
They MUST supplement, not replace, structured assertions about persisted content when record contents are part of the behavior under test.

Tests whose subject is a public count operation MAY verify affected-record cardinality through that operation.
