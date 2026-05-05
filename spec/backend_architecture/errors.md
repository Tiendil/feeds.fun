# Error architecture

## Goal of the document

This document describes how Feeds Fun backend modules represent fatal errors and warnings, and how those values move from lower layers to API, CLI, and worker boundaries.

## Scope

The scope of this specification is limited to error and warning architecture inside the backend Python implementation.

The following topics are out of scope:

- exact wording of user-facing messages.
- complete lists of future error codes.
- terminal formatting.
- HTTP response schema details.
- frontend error handling.
- test coverage requirements.

## Dictionary

- `fatal error` - a problem that prevents the requested backend operation from completing successfully.
- `non-fatal problem` - a problem discovered while processing a backend operation that does not prevent the operation from producing useful output or continuing later.
- `error code` - a stable machine-readable identifier for a fatal error when the error is rendered across an external boundary.
- `module root error` - the `Error` exception class in a module's `errors` submodule; it is the root for fatal errors owned by that module.
- `exception boundary` - a module boundary where low-level exceptions are converted into Feeds Fun exceptions, API errors, feed error states, or log records.

## General principles

Fatal errors MUST be represented with Feeds Fun project-specific exceptions before they cross backend module boundaries.

Non-fatal problems SHOULD be represented as warning log records, persisted error states, or explicit result values instead of exceptions when processing can continue and produce useful output.

Lower-level modules MUST NOT convert errors directly into HTTP responses, terminal output, process termination, or frontend-visible records.

The API, CLI, and worker boundary layers MUST be responsible for converting backend errors and warnings into:

- HTTP responses.
- CLI exit behavior and stderr messages.
- worker logs and persisted processing states.

Boundary-facing errors SHOULD expose stable error codes.

Error codes MUST use lowercase ASCII letters, ASCII digits, and `_`.

User-facing messages SHOULD be clear enough to diagnose the problem without exposing implementation stack details.

## Error ownership

Each backend module MAY define an `errors` submodule for errors owned by that module.

Shared base error types MUST be owned by a common lower-level module that does not depend on API or CLI behavior.

Module-specific error types MUST be defined in the module that can add the most useful context.

Production errors MUST NOT be defined in test modules.

Test-only error classes MAY be defined in test modules when they are required to verify error handling behavior.

## Error hierarchy

The backend MUST define a single project root exception type for all expected fatal project errors.

The project root exception MUST be named `Error`.

The project root exception MUST inherit from `Exception`.

The project root exception MUST NOT inherit from Pydantic model classes.

The project root exception MUST be owned by `ffun.core.errors`.

Each module that defines fatal errors SHOULD define one module root error class.

The module root error class MUST be named `Error`.

All fatal errors owned by that module MUST inherit from the module root error class.

A module root error class MUST inherit from the project root exception or from a parent module's root error class.

A module SHOULD NOT define multiple root error classes.

Modules outside the API and CLI boundary modules MUST NOT know about HTTP status codes or CLI exit codes.

Module root error classes SHOULD be abstract classification classes and SHOULD NOT be raised directly when a more specific concrete error is available.

Intermediate abstract error classes MAY exist under a module root when a module needs a narrower ownership boundary.

The hierarchy SHOULD keep module-specific root errors under the single project root exception.

Concrete error class names MAY differ, but project and module root error classes MUST be named `Error`.

## Exception data

Project-specific exceptions SHOULD carry:

- a human-readable message or enough structured attributes to build one.
- optional structured details.
- an optional original cause.
- an error code when the exception crosses an external API or CLI boundary.

Structured details MUST contain values that can be rendered deterministically.

Structured details SHOULD use strings, numbers, booleans, `None`, lists, and dictionaries when they need to be serialized by the API or CLI.

Exceptions MUST NOT require callers to parse their message text to understand the error category.

## Warnings

Warnings represent non-fatal problems discovered while processing a backend operation.

Warnings MUST be used only when processing can continue, retry later, or persist a meaningful failed state for the affected feed or entry.

Warnings MUST NOT be used for invalid API input, invalid command line arguments, invalid configuration that prevents startup, or storage failures that prevent a valid result.

Warnings SHOULD be represented as structured log records, explicit result states, or persisted error states.

Warnings are not exceptions, Pydantic entities, or Python `warnings` module warnings.

Code that adds warnings SHOULD include enough context for API, CLI, worker, and operator output to be useful.

Examples of warning-producing situations include:

- a transient network problem while loading a feed.
- an entry that cannot be processed by one tag processor but can still be handled later.
- a feed source response that is malformed but can be represented as a source-specific feed error state.

## Pydantic validation errors

Pydantic validation errors MUST NOT be exposed directly across high-level module boundaries for user-provided data.

Modules that create Pydantic entities from external input MUST convert `pydantic.ValidationError` into Feeds Fun errors, API errors, warning log records, or persisted error states at the nearest exception boundary with useful context.

Pydantic validation errors MAY be used directly inside tests for low-level entity validation.

## Exception boundaries

Modules that call external systems MUST convert relevant low-level failures into Feeds Fun errors, API errors, warning log records, or persisted error states at the boundary where context is still available.

External systems include:

- filesystem operations.
- TOML parsing.
- Pydantic model validation for external input.
- regular expression compilation.
- PostgreSQL operations.
- HTTP and feed-source requests.
- LLM provider requests.
- shell command execution.

Unexpected programming errors MAY propagate during development, but code that handles expected user, provider, source, storage, or environment failures MUST convert them into Feeds Fun-specific errors or states.

When converting an exception, the original exception SHOULD be preserved as the cause when it helps debugging.

## Boundary mapping

The API layer MUST map boundary-facing project errors to HTTP responses.

The CLI layer MUST map fatal project errors to non-zero exit behavior.

The worker layer MUST map expected processing failures to logs, retries, or persisted processing states.

The mapping from exception classes to external boundary behavior SHOULD be owned by the boundary module.

The mapping MAY map specific module root error classes to specific response or exit categories.

The mapping MAY map specific concrete error classes to specific response or exit categories when a module root is too broad.

The mapping MUST define a default failure category for project exceptions that are not explicitly mapped.

The API and CLI SHOULD choose the most specific category that matches the failure.

The API and CLI MUST NOT treat warning log records alone as fatal errors.
