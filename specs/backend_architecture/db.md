# Backend database architecture

## Goal of the document

This document describes how Feeds Fun backend code works with PostgreSQL, including persistence boundaries, transaction handling, query conventions, migration ownership, and database-focused testing practices.

## Scope

This specification covers backend database access from Python code under `ffun/ffun`, database schema migrations owned by backend modules, and tests that verify persistence-backed behavior.

This specification does not cover deployment-specific PostgreSQL administration, production backup strategy, frontend data access, Docker configuration, or database schema details for individual product features.

## Dictionary

- `database operation` - a function that directly reads from or writes to PostgreSQL.
- `transactional operation` - a database operation or domain function whose multiple SQL statements MUST succeed or fail as one atomic unit.
- `operation module` - a module-local `operations` submodule that owns persistence-backed commands and queries for the parent backend module.
- `migration` - a yoyo migration file stored in a module-local `migrations` package.
- `execute callable` - an object with the same contract as `ffun.core.postgresql.ExecuteType`, used to run SQL inside either a single-statement helper or an explicit transaction.

## Storage Technology

PostgreSQL is the backend source of durable application state.

Backend runtime database access MUST use the shared PostgreSQL infrastructure in `ffun.core.postgresql`.

Backend runtime code MUST NOT create independent PostgreSQL connection pools or long-lived direct connections. Application startup owns pool creation and application shutdown owns pool destruction.

Migrations MAY use yoyo's synchronous PostgreSQL backend because migration execution is a CLI-time maintenance operation, not request or worker runtime data access.

Database code SHOULD assume that rows are returned as dictionaries keyed by column name.

Database code SHOULD keep PostgreSQL-specific behavior explicit when it is part of the chosen design, such as `ON CONFLICT`, `RETURNING`, `ANY(...)`, array operators, JSONB values, or row locking.

## Connection Lifecycle

The application lifespan MUST initialize the PostgreSQL pool before API handlers, workers, or other database-backed behavior run.

The application lifespan MUST verify basic database connectivity during startup and fail startup when PostgreSQL is unavailable.

The application lifespan MUST close the PostgreSQL pool during shutdown.

Long-running application processes SHOULD keep the pool healthy with periodic pool checks.

Code outside application startup and shutdown MUST treat the database pool as already initialized.

## Database Access Boundary

Database operations SHOULD live in the owning backend module's `operations` submodule.

Operation modules SHOULD contain direct SQL execution, row-to-entity conversion, idempotent persistence commands, and low-level persistence queries owned by the module.

Domain modules SHOULD compose operation-module functions into business workflows.

Domain modules MUST own transaction boundaries for new or significantly changed business workflows.

When a workflow changes multiple database records that must stay consistent, the domain module MUST handle the transaction boundary and pass the transaction execute callable into operation-module helpers.

Existing operation-module transaction blocks MAY remain in old code until the surrounding workflow is substantially changed. New code SHOULD NOT add transaction ownership to operation modules unless the operation module function is intentionally a low-level atomic primitive and no domain workflow boundary exists.

Top-level backend modules MUST NOT import another top-level module's `operations` submodule. Cross-module behavior SHOULD go through the other module's `domain`, `entities`, or `errors` boundary.

Operation modules SHOULD return domain entities, typed ids, primitives, or dictionaries with clear ownership. They SHOULD NOT leak raw persistence details into API handlers when a domain entity or module-level type can express the result.

Operation modules SHOULD provide small row mapper functions when database rows are converted into entities in more than one place.

Technical maintenance functions that directly mutate storage for cleanup, merge, repair, or tests SHOULD make that purpose clear in their name or containing boundary and SHOULD remain outside normal user-facing workflows unless explicitly intended.

## Execution Helpers

Single-statement database operations SHOULD use the shared `execute` helper.

The `execute` helper SHOULD be used for statements that are correct as their own autocommitted unit, such as one `SELECT`, one `INSERT ... ON CONFLICT`, one `UPDATE ... RETURNING`, or one `DELETE`.

Explicit transactions MUST use the shared transaction context manager or the transaction decorator provided by `ffun.core.postgresql`.

Functions that are designed to run inside a caller-owned transaction SHOULD accept an execute callable as their first argument.

Functions that accept an execute callable MUST use that callable for all SQL that belongs to the caller's transaction.

Transactional functions MUST NOT call the top-level `execute` helper for statements that are expected to participate in the active transaction, because that opens a separate autocommitted execution path.

The transaction decorator SHOULD be used when a public async function owns the whole transaction and has no setup code that must run outside the transaction.

The transaction context manager SHOULD be used when transaction ownership is local to part of a function or when error handling around the transaction boundary must be explicit.

Nested transaction ownership SHOULD be avoided. Prefer passing the existing execute callable through helper functions instead of opening another transaction inside an active transactional workflow.

## Query Style

Static SQL SHOULD be written as readable multiline SQL strings close to the operation that uses them.

SQL parameters MUST be passed separately from SQL text, using psycopg named placeholders such as `%(user_id)s`.

Code MUST NOT interpolate user-controlled values into SQL text.

String interpolation in SQL text is acceptable only for trusted schema identifiers or static fragments selected by code, and the reason SHOULD be obvious from local context.

Iterable parameters used with PostgreSQL array comparisons SHOULD be materialized before execution when the value may be a generator. The common form for membership checks is `column = ANY(%(ids)s)`.

Dynamic SQL SHOULD use PyPika when conditions, inserts, or joins are assembled from code.

Complex queries whose shape is built from optional filters or generated clauses SHOULD use PyPika.

Bulk inserts SHOULD use PyPika when rows are assembled in Python.

Raw SQL SHOULD be preferred over a query builder for stable, hand-tuned, PostgreSQL-specific, or complex queries where explicit SQL is clearer.

Bulk inserts SHOULD use PostgreSQL-native conflict handling together with PyPika when idempotency or upsert behavior is needed.

JSONB values SHOULD be passed through psycopg's JSON adapter when Python structures need to be stored as JSONB.

Operations that update timestamps for persisted records SHOULD set the timestamp in SQL when the database time is the intended source of truth.

Operations that need one consistent application-level timestamp across multiple rows SHOULD compute that timestamp once in Python and pass it to every relevant statement.

## Idempotency And Constraints

Schema constraints SHOULD enforce durable invariants such as primary keys, uniqueness, and ownership keys.

Database operations SHOULD use `ON CONFLICT` when repeated calls are expected to be harmless.

Operation code SHOULD handle expected PostgreSQL constraint errors at the lowest boundary that can convert them into meaningful project behavior.

Expected constraint failures SHOULD be translated into domain errors, warning log records, retries, idempotent fallback reads, or boolean results according to the workflow.

Unexpected constraint failures SHOULD be allowed to fail the operation rather than being hidden.

When an operation uses `RETURNING` to determine whether a change happened, the empty result path MUST be handled explicitly.

Counter, quota, and reservation updates SHOULD be expressed as conditional SQL updates when the invariant can be checked atomically in the database.

## Concurrency

Worker-style selection of shared work SHOULD use database-level coordination when multiple workers may run concurrently.

`FOR UPDATE SKIP LOCKED` SHOULD be used for queue-like selection when workers must claim rows without blocking each other.

Operations that may touch the same set of rows concurrently SHOULD use deterministic ordering where practical to reduce deadlock risk.

Cleanup operations SHOULD tolerate concurrent inserts or links by using transactions, foreign key checks, conflict handling, or retryable no-op behavior.

When a concurrency failure is expected and harmless for a periodic maintenance task, code MAY convert it into a logged no-op result.

When a concurrency failure means the caller's requested state cannot be guaranteed, code SHOULD raise a module-owned error.

## Schema Ownership

Each backend module SHOULD own the tables that correspond to its domain responsibility.

Table names SHOULD use a short module-related prefix when that keeps ownership clear in SQL and migrations.

Schema changes MUST be implemented as yoyo migrations in the owning module's `migrations` package.

Migration files SHOULD stay close to the module that owns the changed tables.

Cross-module schema changes SHOULD live in the module that owns the main business reason for the change. If there is no single owner, the `meta` module MAY own the migration.

Migrations SHOULD define explicit dependencies with `__depends__` when ordering matters across files or modules.

Migrations MUST define apply behavior. Migrations SHOULD define rollback behavior when rollback is reasonably possible.

A rollback that cannot restore data safely MAY be a no-op, but the migration SHOULD make that limitation clear by being simple and intentional.

Migrations SHOULD keep schema DDL, indexes, and data backfills in the same migration only when they are part of one atomic compatibility step.

Large data migrations SHOULD be written so their locking, ordering, and rollback properties are clear from the SQL and local comments.

Indexes SHOULD be created or changed in the migration that introduces the query shape or invariant that needs them.

Migration SQL SHOULD use the same safety rules as runtime SQL: bind data values as parameters and keep interpolated SQL fragments limited to trusted static identifiers or fragments.

## Migration Commands

Development migration commands MUST be run through the backend development container helpers.

The preferred command for applying migrations in development is:

```bash
./bin/backend-utils.sh poetry run ffun migrate
```

The preferred command for creating a new backend migration is:

```bash
./bin/backend-utils.sh poetry run yoyo new --message "what you want to do" ./ffun/<component>/migrations/
```

The migration path in the command above intentionally uses the path layout visible inside the backend container.

Production upgrades SHOULD apply migrations before starting the upgraded application version.

When upgrading across multiple versions with migration requirements, operators SHOULD follow the documented version-by-version migration order instead of skipping directly to the latest version.

## Tests

Tests for database-backed behavior SHOULD use the real test PostgreSQL service provided by the development environment.

Tests MUST be run through backend development container commands.

The preferred command for all backend tests is:

```bash
./bin/backend-tests.sh
```

The preferred command for targeted backend tests is:

```bash
./bin/backend-utils.sh poetry run pytest <path>
```

Backend test setup SHOULD apply all migrations before database-backed tests run and roll them back after the test session.

Operation tests SHOULD cover persistence-backed state changes, returned entities, idempotency, empty inputs, duplicate inputs, expected constraint failures, and important `RETURNING` empty-result paths.

Transactional workflow tests SHOULD verify both successful multi-step behavior and failure paths that must leave the database unchanged.

Migration-sensitive changes SHOULD be verified by tests that exercise the resulting operation behavior after migrations are applied.

Tests SHOULD assert structured database-visible state when behavior depends on persistence.

Tests SHOULD use small explicit fixtures and helper functions owned by the relevant module.

Tests SHOULD NOT mock PostgreSQL for ordinary operation and domain tests when the behavior being tested is persistence behavior.

## When To Apply Each Pattern

Use a plain operation-module function with `execute` when the operation is one independent SQL statement or when each statement is intentionally safe as its own autocommitted unit.

Use an execute-callable helper when the operation is a reusable step that may need to participate in a larger transaction.

Use the transaction decorator when one public async function is exactly one atomic database workflow.

Use the transaction context manager when only part of a function is atomic, when transaction setup depends on earlier work, or when explicit exception handling around the transaction boundary improves clarity.

Use raw SQL when the query is stable, readable, PostgreSQL-specific, or performance-sensitive.

Use PyPika or another structured builder already present in the backend when query shape is assembled from optional filters, repeated inserts, or generated joins.

Use `ON CONFLICT DO NOTHING` when duplicate work is acceptable and the caller can continue without knowing whether the row was new.

Use `ON CONFLICT DO UPDATE` when an existing row must be refreshed and the update is safe under repeated calls.

Use a fallback `SELECT` after conflict handling when the caller needs the existing row id or entity.

Use conditional `UPDATE ... RETURNING` when the database must atomically decide whether a state transition is allowed.

Use row locks with `SKIP LOCKED` when concurrent workers claim shared work.

Add or change an index when a new query shape becomes part of normal runtime behavior, especially for worker polling, feed entry listing, ownership lookups, and cleanup scans.

Add a migration whenever persisted schema, indexes, constraints, or stored data compatibility changes.
