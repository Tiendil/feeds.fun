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

Tests MUST NOT depend on user-specific files outside test-created temporary directories.

Tests SHOULD prefer coverage through public module boundaries when that is practical for the behavior under test.

Tests SHOULD verify observable behavior and locally owned validation instead of implementation declarations or private implementation details.

**Example:** A test for URL normalization checks the returned URL and whether invalid input is rejected.

**Counterexample:** Checking which private helper was called, which module was imported, or what type annotation was written would test implementation details.

Public boundaries and behavioral assertions keep tests useful when implementation details change.

Static typing requirements SHOULD be enforced by static analysis, code review, or dedicated architecture checks.
Ordinary unit tests SHOULD NOT inspect runtime representations solely to restate type declarations.

**Example:** The type checker can verify that a parser returns its declared result type, while a unit test checks that valid input parses correctly.

**Counterexample:** Reading a Python return annotation or asserting a TypeScript object’s keys solely to mirror its interface would duplicate the declaration.

Tests SHOULD use mocks, stubs, and spies as little as possible.

Tests SHOULD prefer real project code, temporary files, local test services, and explicit fixtures over mocked collaborators.

Real collaborators reduce the risk that a test passes against behavior that differs from production.

## Test organization

The structure of tests SHOULD mirror the implementation structure when that makes ownership clear.

Cross-module integration tests MAY live under the module that owns the public boundary being exercised.

Mirroring the implementation helps developers find the tests for a module.

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

## Fixtures and temporary data

Tests that need files SHOULD create those files in temporary directories.

Tests SHOULD keep fixture data as small as possible while preserving the behavior being verified.

Inline fixture data SHOULD be preferred for short configuration files and short expected outputs.

Reusable fixture files MAY be added when inline data would obscure the test.

Tests that change the current working directory MUST restore it before the test ends.

Temporary files keep file-based setup isolated.
Small fixtures make the relevant data easy to see.

## Assertions

Tests SHOULD assert structured values before rendered text when structured values are available.

Tests MUST NOT use identity assertions for ordinary value checks.

Rendered output tests SHOULD assert exact output only when the exact output is part of a stable contract.

Rendered output tests MAY assert selected lines, fields, or records when exact text is intentionally outside the relevant specification.

Structured assertions focus on the values the contract guarantees.
Exact comparisons are useful when callers depend on the rendering itself.

### Persistence

Persistence operation tests MUST verify the expected persisted effects when the behavior under test inserts or deletes rows, including the number of affected records when cardinality is part of the contract.

Tests for rejected writes, idempotent no-ops, or other paths whose contract includes unchanged persisted state MUST verify that invariant.

Assertions about persisted effects MUST isolate the operations responsible for those effects.
They MUST supplement, not replace, structured assertions about persisted content when record contents are part of the behavior under test.

Tests whose subject is a public count operation MAY verify affected-record cardinality through that operation.
