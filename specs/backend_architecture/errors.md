# Error architecture

## Goal of the document

This document describes how the Feeds Fun backend represents fatal errors and warnings and passes those values to API, CLI, and worker boundaries.

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
- `exception boundary` - a Python module boundary where expected low-level exceptions are converted into Feeds Fun exceptions, API errors, feed error states, or log records.
- `stored-state integrity failure` - an unexpected failure to validate or reconstruct persisted application state according to its owning domain model.

The [Errors role specification](roles/errors.md) defines module root errors and the exception hierarchy.

## General principles

Expected fatal errors MUST be represented with Feeds Fun project-specific exceptions before they cross backend module boundaries.

Unexpected programming, infrastructure, storage, provider, or environment failures MAY propagate as their original exceptions until the developer explicitly defines handling for them.

Non-fatal problems SHOULD be represented as warning log records, persisted error states, or explicit result values instead of exceptions when processing can continue and produce useful output.

Boundary-facing errors SHOULD expose stable error codes.

Error codes MUST use lowercase ASCII letters, ASCII digits, and `_`.

User-facing messages SHOULD be clear enough to diagnose the problem without exposing implementation stack details.

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

Code that adds warnings SHOULD include enough context for API, CLI, worker, and operator output to be useful.

Examples of warning-producing situations include:

- a transient network problem while loading a feed.
- an entry that cannot be processed by one tag processor but can still be handled later.
- a feed source response that is malformed but can be represented as a source-specific feed error state.

## Exception boundaries

Code MUST catch an exception only when the catching boundary has defined recovery, translation, or context-enrichment behavior for that condition.
Merely recognizing an exception type is not sufficient reason to catch it.

An exception is expected only when its occurrence is part of the called operation's documented contract and the caller has a defined response.
Exceptions caused by violated internal invariants, invalid persisted state, programming defects, or unexpected infrastructure failures are not expected merely because they use a project-specific exception class.

Code that calls external systems MUST convert expected low-level failures into Feeds Fun errors, API errors, warning log records, or persisted error states at the boundary where useful domain context is still available.

A low-level failure is expected when one of the following is true:

- the module business logic explicitly anticipates the condition.
- the third-party service contract defines the condition as a normal outcome.
- the condition is a known recurring operational case that the developer has decided to handle.
- the caller can make a useful domain decision from a module-specific error or state.

External systems include:

- filesystem operations.
- TOML parsing.
- regular expression compilation.
- PostgreSQL operations.
- HTTP and feed-source requests.
- LLM provider requests.
- shell command execution.

Code SHOULD NOT catch broad low-level exception classes only to satisfy a conversion rule at a Python module boundary.

Unexpected low-level failures MAY propagate unchanged until the developer explicitly requests handling for that class of failure.

Filesystem, parser, and validation failures encountered while loading application configuration MAY propagate as their original exceptions when configuration loading fails and the original diagnostic is intended for the operator.
This allowance MUST NOT be used for user-provided, provider-provided, or other runtime domain-operation input.

An external boundary MAY catch an exception to report it and translate it into the boundary's standard failure behavior.
This translation does not change whether the exception is expected or unexpected.

Translation of an unexpected exception MUST leave the operation failed and MUST NOT recover with a successful, empty, or fallback result.

Code that handles expected user, provider, source, storage, or environment failures MUST convert them into Feeds Fun-specific errors or states.

Invalid external input MUST be reported through the error architecture instead of by returning partially valid entities.

For PostgreSQL operations, code SHOULD catch and convert specific database exceptions only when the exception represents an expected business or consistency condition.

For example, a `ForeignKeyViolation` MAY be converted to an operation-specific stale-reference, concurrency, or integrity error when the operation is designed to race with deletion or accepts externally supplied entity ids.

Code SHOULD NOT wrap unexpected PostgreSQL infrastructure failures such as connection errors, pool failures, timeouts, SQL syntax errors, or unexpected constraint violations unless the developer explicitly approves that handling.

A failure to validate or reconstruct persisted application state according to its owning domain model MUST be treated as an unexpected stored-state integrity failure.

For HTTP, feed-source, LLM provider, and other third-party service calls, code MUST convert expected service outcomes into module-specific errors or persisted states when those outcomes are part of normal operation.

Examples include unavailable feed sources, malformed feed responses, known protocol errors, provider-declared rate limits, authentication failures, and documented validation failures.

Unknown third-party failures SHOULD NOT be broadly normalized unless the Python module boundary intentionally treats all failures of that operation as a recoverable domain outcome.

When converting an exception, the original exception SHOULD be preserved as the cause when it helps debugging.

## Boundary mapping

Lower-level Python modules MUST NOT convert errors directly into HTTP responses, terminal output, process termination, or frontend-visible records.

The module responsible for the boundary SHOULD own the mapping from exception classes to external behavior.

The mapping MAY map specific module root error classes to specific response or exit categories.

The mapping MAY map specific concrete error classes to specific response or exit categories when a module root is too broad.

The mapping MUST define a default failure category for project exceptions that are not explicitly mapped.

The API and CLI SHOULD choose the most specific category that matches the failure.

The API and CLI MUST NOT treat warning log records alone as fatal errors.

### API boundary

The API boundary MUST map boundary-facing project errors to HTTP responses.
The API boundary MUST decide how to represent warnings in HTTP responses.
Only the API boundary MAY assign HTTP status codes for Feeds Fun responses.

A project-specific exception class alone MUST NOT make an error boundary-facing.
Global API infrastructure MAY render an unexpected stored-state integrity failure as a generic server-error response, but endpoint handlers MUST NOT assign it a stable application error code or present it as a condition the caller can correct.

### CLI boundary

The CLI boundary MUST map fatal project errors to non-zero exit behavior.
The CLI boundary MUST handle stderr reporting for errors and warnings.
Only the CLI boundary MAY assign exit codes to Feeds Fun commands.

### Worker boundary

The worker boundary MUST map expected processing failures to logs, retries, or persisted processing states.
The worker boundary MUST decide how to report errors and warnings through logs or persisted processing states.
