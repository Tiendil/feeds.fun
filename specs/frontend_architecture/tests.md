# Frontend test architecture

## Goal of the document

This document describes the architecture of Feeds Fun frontend tests, including where tests live, how they relate to frontend modules, and how they cover user-facing logic.

## Scope

The scope of this specification is limited to frontend test organization and architectural testing expectations for source code under `site/src`.
The [automated test conventions](../programming/tests.md), [TypeScript test conventions](../programming/typescript.tests.md), and [Vitest conventions](../programming/libs/vitest.md) apply to frontend tests.

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

## Test module layout

Cross-cutting frontend architecture tests MUST live under `./site/src/tests`.

View-level integration tests SHOULD live under the `views` module or the feature module that owns the tested page behavior when view tests are added.

## Logic tests

Logic tests SHOULD verify pure TypeScript behavior through exported functions and values.

Logic tests SHOULD cover:

- input normalization.
- validation and assertions owned by the module.
- parsing and sanitization behavior.
- security-sensitive transformations.
- date, timer, and formatting helpers.

Logic tests SHOULD NOT verify Vue rendering unless the tested logic explicitly owns DOM transformation.

Logic tests MAY use spies when they verify integration with a third-party library and direct observable output is not enough.

## Component and view tests

Component tests MUST NOT be added unless the developer explicitly requests component-level testing.
Component behavior SHOULD be extracted into frontend logic and covered by logic tests when practical.
Requiring explicit approval keeps the component-test surface intentional; extracting render-independent behavior produces smaller, faster tests that are less coupled to Vue mounting details.
Architecture tests that inspect component source or registration without mounting or rendering components are not component tests under this restriction.

View-level tests SHOULD verify page-level composition only when the behavior cannot be covered by smaller component, store, or logic tests.

View-level tests SHOULD NOT duplicate behavior already covered by lower-level component or logic tests.

## Router tests

Router tests SHOULD verify route selection, route metadata, and navigation guards through public router behavior.
