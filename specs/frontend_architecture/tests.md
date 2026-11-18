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
- `component test` - a test that mounts or renders a Vue component to verify its behavior.

## General principles

The [automated test conventions](../programming/tests.md), [TypeScript test conventions](../programming/typescript.tests.md), and [Vitest conventions](../programming/libs/vitest.md) apply to frontend tests.

Tests MUST be written as part of the frontend TypeScript project.

Development-related test execution MUST happen through the project development container commands.

The preferred command form for running all frontend tests is:

```bash
mise run frontend:test
```

The preferred command form for running targeted frontend tests is:

```bash
mise run frontend:run -- npm run test:unit -- --run <path>
```

## Test module layout

Test files MUST NOT be placed directly under `./site/src`.
Cross-cutting frontend architecture tests MUST live under `./site/src/tests`.

Each implementation module or submodule SHOULD have corresponding tests under a `tests` submodule owned by the same parent module when that matches the existing layout.

Examples:

- `./site/src/logic/utils.ts` -> `./site/src/logic/tests/utils.test.ts`
- `./site/src/logic/iframeSanitizer.ts` -> `./site/src/logic/tests/iframeSanitizer.test.ts`
- `./site/src/stores/entries.ts` -> `./site/src/stores/tests/entries.test.ts` when store tests are added.
- global component registration architecture -> `./site/src/tests/componentRegistration.test.ts`.

Component tests SHOULD live near the component or under a nearby `tests` submodule owned by the same parent directory when component tests are added.

View-level integration tests SHOULD live under the `views` module or the feature module that owns the tested page behavior when view tests are added.

## Test organization

Tests SHOULD be organized around the tested function, component, store, or public module behavior.

Examples:

- `it("returns fallback value for empty input", ...)`.
- `it("removes unsafe iframe attributes", ...)`.
- `it("emits selected tag changes", ...)`.

Standalone top-level tests SHOULD be used only for module-level invariants or file-level checks that do not naturally belong to one tested function, component, or store.

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

Logic tests MAY use spies when they verify integration with a third-party library and direct observable output is not enough.

## Component and view tests

Component tests MUST NOT be added unless the developer explicitly requests component-level testing.
Component behavior SHOULD be extracted into frontend logic and covered by logic tests when practical.
Requiring explicit approval keeps the component-test surface intentional; extracting render-independent behavior produces smaller, faster tests that are less coupled to Vue mounting details.
Architecture tests that inspect component source or registration without mounting or rendering components are not component tests under this restriction.
When component tests are explicitly requested, the following component-test rules apply.

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

Inline fixture data SHOULD be preferred for short HTML snippets, API payloads, and expected outputs.

Tests that modify global browser state, timers, stores, or mocks MUST restore them before the test ends.

## Assertions

DOM tests SHOULD query stable user-observable DOM structure before asserting raw HTML strings.

Rendered output tests MAY assert selected lines, attributes, or records when exact text is intentionally outside the relevant specification.

Security-sensitive sanitization tests SHOULD assert both allowed output and removed unsafe input.
