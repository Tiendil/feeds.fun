# Frontend test architecture

## Goal of the document

This document describes the architecture of Feeds Fun frontend tests, including where tests live, how they relate to frontend modules, and how they cover user-facing logic.

## Scope

The scope of this specification is limited to frontend test organization and architectural testing expectations for source code under `site/src`.

The following topics are out of scope:

- exact Vitest configuration.
- exact fixture names.
- continuous integration configuration.
- backend pytest tests.
- browser end-to-end tests.
- visual regression tests.
- performance benchmarks.

## Dictionary

- `unit test` - a test focused on one frontend module or one small group of closely related functions, components, or stores.
- `integration test` - a test that checks multiple frontend modules through a public boundary such as component rendering, store behavior, router behavior, or API client behavior.
- `fixture` - test data or setup used by one or more tests.
- `DOM test` - a test that uses the Vitest `jsdom` environment to verify browser-facing behavior.

## General principles

Tests MUST be written as part of the frontend TypeScript project.

Development-related test execution MUST happen through the project development container commands.

The preferred command form for running all frontend tests is:

```bash
./bin/frontend-tests.sh
```

The preferred command form for running targeted frontend tests is:

```bash
./bin/frontend-utils.sh npm run test:unit -- --run <path>
```

Tests SHOULD be deterministic for the same repository state.

Tests SHOULD prefer coverage through public module boundaries when that is practical for the behavior under test.

Tests SHOULD use mocks, stubs, and spies as little as possible.

Tests SHOULD prefer real project code, explicit fixtures, and the configured `jsdom` environment over mocked collaborators.

Tests MUST NOT depend on external network access.

Tests MUST NOT depend on user-specific files outside test-created temporary directories.

Tests MUST NOT modify Docker configuration or runtime parameters.

Tests SHOULD verify observable behavior and locally owned validation instead of implementation declarations such as exact helper types or private implementation details.

Static typing requirements SHOULD be enforced by TypeScript, static analysis, code review, or dedicated architecture checks, not by ordinary unit tests that inspect runtime shapes only to restate type declarations.

## Test module layout

Frontend tests MUST use the Vitest `*.test.ts` naming convention.

Each implementation module or submodule SHOULD have corresponding tests under a `tests` submodule owned by the same parent module when that matches the existing layout.

The name of a test file MUST be built from the name of the tested module by adding the `.test.ts` suffix.

The structure of tests SHOULD mirror the implementation structure when that makes ownership clear.

Examples:

- `./site/src/logic/utils.ts` -> `./site/src/logic/tests/utils.test.ts`
- `./site/src/logic/iframeSanitizer.ts` -> `./site/src/logic/tests/iframeSanitizer.test.ts`
- `./site/src/stores/entries.ts` -> `./site/src/stores/tests/entries.test.ts` when store tests are added.

Cross-module integration tests MAY live under the module that owns the public boundary being exercised.

Component tests SHOULD live near the component or under a nearby `tests` submodule owned by the same parent directory when component tests are added.

View-level integration tests SHOULD live under the `views` module or the feature module that owns the tested page behavior when view tests are added.

## Test organization

Tests SHOULD be organized around the tested function, component, store, or public module behavior.

Tests for one exported function SHOULD be grouped in one `describe("<functionName>")` block.

Tests for one component SHOULD be grouped in one `describe("<ComponentName>")` block.

Tests for one store SHOULD be grouped in one `describe("<storeName>")` block.

Test names MUST describe the execution path or behavior being verified.

Examples:

- `it("returns fallback value for empty input", ...)`.
- `it("removes unsafe iframe attributes", ...)`.
- `it("emits selected tag changes", ...)`.

Standalone top-level tests SHOULD be used only for module-level invariants or file-level checks that do not naturally belong to one tested function, component, or store.

Every meaningful execution path of a tested function, component, store action, or module behavior MUST have a corresponding test or parametrized test case.

Execution paths include:

- successful path.
- default-value path.
- empty-input path.
- invalid-input path.
- handled error path.
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
- paths or URLs that require normalization.
- repeated calls that may reveal state leaks.

## Logic tests

Logic tests SHOULD verify pure TypeScript behavior through exported functions and values.

Logic tests SHOULD cover:

- input normalization.
- validation and assertions owned by the module.
- parsing and sanitization behavior.
- security-sensitive transformations.
- date, timer, and formatting helpers.
- API-client request and response shaping when the API boundary is mocked.

Logic tests SHOULD NOT verify Vue rendering unless the tested logic explicitly owns DOM transformation.

Logic tests that inspect HTML or browser APIs MUST use the configured `jsdom` environment.

Logic tests MAY use spies when they verify integration with a third-party library and direct observable output is not enough.

## Component and view tests

Component tests SHOULD verify user-observable behavior.

Component tests SHOULD cover:

- rendered text and attributes that are part of the component contract.
- emitted events.
- prop-driven branches.
- accessible states when the component owns them.
- security-sensitive rendering decisions.

Component tests SHOULD NOT assert private component internals, exact child implementation structure, or CSS classes unless those values are part of a stable contract.

View-level tests SHOULD verify page-level composition only when the behavior cannot be covered by smaller component, store, or logic tests.

View-level tests SHOULD NOT duplicate behavior already covered by lower-level component or logic tests.

## Store, router, and API tests

Store tests SHOULD verify state transitions through public store actions and getters.

Store tests SHOULD reset store state between tests.

Router tests SHOULD verify route selection, route metadata, and navigation guards through public router behavior.

API-client tests SHOULD verify request construction, response parsing, and error handling at the API client boundary.

API-client tests MUST NOT call external network services.

API-client tests SHOULD mock the transport boundary rather than mocking the frontend code that builds requests or interprets responses.

## Behavior coverage

Frontend architecture specifications are the source of expected frontend-wide conventions.

Tests SHOULD cover examples and rules in frontend architecture specifications when the corresponding behavior is implemented and runtime-testable.

Shared logic tests SHOULD cover:

- HTML sanitization.
- URL and iframe normalization.
- tag filter state behavior.
- settings and constants interpretation.
- user-visible formatting helpers.

Component and view tests SHOULD cover:

- conditional rendering.
- event emission.
- user input handling.
- store interaction at component boundaries.
- error and empty states visible to users.

Store and integration tests SHOULD cover:

- persistence-backed state changes exposed to the frontend.
- API success responses.
- API error responses.
- idempotency where repeated calls are expected.
- coordination across public frontend module boundaries.

## Fixtures and temporary data

Tests that need files SHOULD create those files in temporary directories.

Tests SHOULD keep fixture data as small as possible while preserving the behavior being verified.

Inline fixture data SHOULD be preferred for short HTML snippets, API payloads, and expected outputs.

Reusable fixture files MAY be added when inline data would obscure the test.

Fixture paths SHOULD use forward slashes in expected normalized identifiers.

Tests that modify global browser state, timers, stores, or mocks MUST restore them before the test ends.

## Assertions

Tests SHOULD assert structured values before rendered text when structured values are available.

DOM tests SHOULD query stable user-observable DOM structure before asserting raw HTML strings.

Rendered output tests SHOULD assert exact output only for stable frontend contracts.

Rendered output tests MAY assert selected lines, attributes, or records when exact text is intentionally outside the relevant specification.

Security-sensitive sanitization tests SHOULD assert both allowed output and removed unsafe input.
