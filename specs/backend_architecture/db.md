# Backend database architecture

## Goal of the document

This document describes the Feeds Fun backend architecture for PostgreSQL-backed persistence.

## Scope

This specification applies to database-backed Python code under `ffun/ffun` and to the backend's ownership, migration, and testing of stored data.

## Dictionary

- `database operation` - a function that directly reads from or writes to PostgreSQL.
- `transactional operation` - a database operation or domain function whose multiple SQL statements MUST succeed or fail as one atomic unit.
- `operation module` - a module that owns persistence-backed commands and queries for its slice. [Operations layer](layers_and_slices.md#operations)
- `migration` - a Yoyo file that changes the database schema or stored data. [Migrations layer](layers_and_slices.md#migrations)
- `execute callable` - an object with the same contract as `ffun.core.postgresql.ExecuteType`, used to run SQL inside either a single-statement helper or an explicit transaction.
- `approved transaction participant` - a cross-cutting technical module whose public domain interface MAY participate in another top-level module's transaction without workflow-specific approval.

## Storage Technology

PostgreSQL is the backend source of durable application state.
General SQL and schema conventions are documented in [PostgreSQL conventions](../programming/postgresql.md).

Backend runtime database access MUST use the shared PostgreSQL infrastructure in `ffun.core.postgresql`.

Backend runtime code MUST NOT create independent PostgreSQL connection pools or long-lived direct connections. Application startup owns pool creation and application shutdown owns pool destruction.

Migrations MAY use yoyo's synchronous PostgreSQL backend because migration execution is a CLI-time maintenance operation, not request or worker runtime data access.

Database code SHOULD assume that rows are returned as dictionaries keyed by column name.

## Connection Lifecycle

The application lifespan MUST initialize the PostgreSQL pool before API handlers, workers, or other database-backed behavior run.

The application lifespan MUST verify basic database connectivity during startup and fail startup when PostgreSQL is unavailable.

The application lifespan MUST close the PostgreSQL pool during shutdown.

Long-running application processes SHOULD keep the pool healthy with periodic pool checks.

Code outside application startup and shutdown MUST treat the database pool as already initialized.

## Database Access Boundary

Technical maintenance functions that directly mutate storage for cleanup, merge, repair, or tests SHOULD make that purpose clear in their name or containing boundary and SHOULD remain outside normal user-facing workflows unless explicitly intended.

### Table Access Across Modules

Production database schemas and runtime database access in one top-level module MUST NOT reference tables owned by another top-level module.
Cross-module persistence behavior MUST go through the owning modules' public domain boundaries instead of bypassing those boundaries with SQL.

Tests MAY reference tables owned by other top-level modules when direct database access is useful for test setup, assertions, or cleanup.
This exception MUST NOT introduce cross-module references in production schemas, migrations, or runtime database operations.

### Transaction Ownership

Domain modules MUST own transaction boundaries for new or significantly changed business workflows.
When such a workflow must atomically change multiple database records owned by the same top-level backend module, the domain module MUST pass the transaction execute callable into operation-module helpers.

By default, a transaction owned by one top-level backend module MUST NOT execute database operations owned by another top-level backend module or pass its execute callable through another top-level module's domain boundary.
The following cross-cutting technical modules are approved transaction participants for every workflow:

- `ffun.locks`, only for transaction-scoped lock acquisition, release, and holder-transaction lifecycle.
- `ffun.audit`, only for appending and loading audit records through its public domain interface.

A transaction-owning module MAY pass its execute callable through an approved transaction participant's public domain interface, or use an execute callable yielded by that interface, without workflow-specific approval.
When `ffun.locks.locked_transaction` opens the holder transaction, the calling top-level module remains the transaction owner for business-architecture purposes; `ffun.locks` owns only the technical transaction lifecycle.
Participation MUST remain limited to the approved responsibility above, MUST NOT transfer ownership of the calling workflow or its database operations, and MUST NOT permit importing the participant's operation module.
No workflow-specific exception or approval documentation is required for an approved transaction participant.

Transaction sharing with any other top-level backend module remains prohibited by default.
Only a human developer MAY grant an exception to this rule, and the approval MUST be explicit.
Every approved exception MUST be documented before implementation begins, either in the specification for the transaction-owning module or in a comment or docstring attached to the particular function that owns the cross-module transaction.
These locations are required to keep the approval version-controlled and discoverable at either the module's architectural contract or the exact transaction boundary; a separate record would not reliably accompany reviews of the specification or transaction-owning function.
The documentation MUST identify the particular workflow, name the other participating top-level modules, and explicitly require them to share one database transaction.
If no approved exception is documented for a workflow, developers and agents MUST treat the default prohibition as unconditional for that workflow.
An exception MUST NOT be inferred from a general atomicity requirement, a generic cross-module domain API, the ability of a function to accept an execute callable, or any other undocumented circumstance.
Such an exception permits only the specified transaction sharing; cross-module calls MUST still use the participating module's public domain boundary and MUST NOT import its operation module.

New code SHOULD NOT add transaction ownership to operation modules unless the operation module function is intentionally a low-level atomic primitive and no domain workflow boundary exists.

### Operation Results and Row Mapping

Operation modules SHOULD return domain entities, typed ids, primitives, or dictionaries with clear ownership. They SHOULD NOT leak raw persistence details into API handlers when a domain entity or module-level type can express the result.

When an operation uses `RETURNING` to determine whether a change happened, the empty result path MUST be handled explicitly.

Operation modules SHOULD provide small row mapper functions when database rows are converted into entities in more than one place.

Python code SHOULD expose stored integer identifiers for closed sets of categorical values as enums with the stable integer identifiers as their member values.
Enum member names SHOULD provide readable code and interface vocabulary, while enum integer values SHOULD be used for persistence and internal identifiers.

When persisted row data cannot be converted into a valid owning-domain entity, the operation boundary SHOULD raise a module-owned stored-state integrity exception and preserve the validation exception as its cause.
A stored-row validation failure MUST NOT be interpreted as a missing record, filtered from query results, or replaced with a partially populated entity or fallback value.
Normal write paths MUST prevent invalid persisted state; encountering it during a read indicates corrupted data, an incompatible migration, or a write that bypassed domain validation.

## Execution Helpers

Single-statement database operations SHOULD use the shared `execute` helper.

The `execute` helper SHOULD be used for statements that are correct as their own autocommitted unit, such as one `SELECT`, one `INSERT ... ON CONFLICT`, one `UPDATE ... RETURNING`, or one `DELETE`.

Explicit transactions MUST use the shared transaction context manager or the transaction decorator provided by `ffun.core.postgresql`.

Functions that are designed to run inside a caller-owned transaction SHOULD accept an execute callable as their first argument.

Functions that accept an execute callable MUST use that callable for all SQL that belongs to the caller's transaction.

Transactional functions MUST NOT call the top-level `execute` helper for statements that are expected to participate in the active transaction, because that opens a separate autocommitted execution path.

Transaction boundaries MUST cover the complete defined persistence behavior of the workflows and operations they compose.
Code MUST NOT omit or narrow a transaction boundary based on an operation's current number or order of SQL statements.

The transaction decorator SHOULD be used when a public async function owns the whole transaction and has no setup code that must run outside the transaction.

The transaction context manager SHOULD be used when transaction ownership is local to part of a function or when error handling around the transaction boundary must be explicit.

Nested transaction ownership SHOULD be avoided. Prefer passing the existing execute callable through helper functions instead of opening another transaction inside an active transactional workflow.

## Query Style

Static SQL SHOULD be written as strings close to the operation that uses them.

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

Operations that need one consistent application-level timestamp across multiple rows SHOULD compute that timestamp once in Python and pass it to every relevant statement.

## Constraint Validation And Errors

Business invariants, including allowed values and state-transition rules, MUST be validated by domain or service logic before an operation persists the state, even when a row-local schema constraint also protects the corresponding stored shape.
Database schemas MUST NOT use constraints, triggers, or other schema-level validation to enforce invariants that depend on data owned by another top-level backend module.

Operation code SHOULD handle expected PostgreSQL constraint errors at the lowest boundary that can convert them into meaningful project behavior.

Expected constraint failures SHOULD be translated into domain errors, warning log records, retries, idempotent fallback reads, or boolean results according to the workflow.

Unexpected constraint failures SHOULD be allowed to fail the operation rather than being hidden.

## Concurrency

When a concurrency failure is expected and harmless for a periodic maintenance task, code MAY convert it into a logged no-op result.

When a concurrency failure means the caller's requested state cannot be guaranteed, code SHOULD raise a module-owned error.

## Schema Ownership

Each backend module SHOULD own the tables that correspond to its domain responsibility.

A table owned by one top-level backend module MUST NOT define foreign keys, cascading actions, triggers, or other schema-level references to tables owned by another top-level backend module. Cross-module identifiers MUST be stored as semantic values without database-level references; validation and coordinated state changes MUST go through module domain boundaries.

### Table Prefixes

Table names SHOULD start with a short owner prefix when that keeps module ownership clear.
Examples include `f_` for feeds, `l_` for library, `o_` for ontology, `u_` for users, and `q_` for queues.

Table prefixes MUST NOT intersect between modules.

When a new module's natural one-letter prefix is already used, the new module MUST use a longer but still short prefix that starts with the module name's first character.
For example, `l_` is already used by `library`, so `librarian` uses `ln_` for tables such as `ln_processor_pointers`.

## Schema Migrations

Schema changes and any conversions of stored data required by a code change MUST be implemented as Yoyo migrations in the owning slice’s Migrations layer.

Before adding a migration on a development branch, developers and agents MUST check whether that branch already introduces an unreleased migration for the same feature or schema change.
When it does, they SHOULD amend that branch migration instead of adding another incremental migration.
Consolidating unreleased changes avoids unnecessary migration-chain noise and keeps one feature's apply and rollback behavior coherent; a separate migration MAY be used when it has a justified independent maintenance or review boundary.
A new migration MUST be added when the earlier migration may already have been applied outside the development branch, or when the new change has an independent compatibility or ordering boundary.

Cross-module schema changes SHOULD live in the module that owns the main business reason for the change. If there is no single owner, the `meta` module MAY own the migration.

Migrations SHOULD define explicit dependencies with `__depends__` when ordering matters across files or modules.

Migrations MUST define apply behavior. Migrations SHOULD define rollback behavior when rollback is reasonably possible.

A rollback that cannot restore data safely MAY be a no-op, but the migration SHOULD make that limitation clear by being simple and intentional.

When yoyo fails in the development environment because the PostgreSQL database is in an inconsistent migration state, agents SHOULD stop the project's Docker containers instead of weakening migrations with defensive guards. The development PostgreSQL database is kept in RAM, so stopping containers resets it.

Migrations SHOULD keep schema DDL, indexes, and data backfills in the same migration only when they are part of one atomic compatibility step.

Migration apply and rollback functions SHOULD execute each SQL statement separately. Related statements MAY remain in the same migration step and transaction when they form one atomic compatibility change. Separate execution improves failure attribution and avoids relying on multi-statement driver behavior.

For large data migrations, the SQL and its comments SHOULD make locking, ordering, and rollback behavior clear.

An index migration SHOULD ship with the code or schema change that requires it.

A schema specification and the migration that introduces its schema SHOULD use the same data type spellings.

Migration SQL SHOULD use the same safety rules as runtime SQL.

## Migration Commands

Development migration commands MUST be run through the backend development container helpers.

The preferred command for applying migrations in development is:

```bash
mise run backend:ffun -- migrate
```

The preferred command for creating a new backend migration is:

```bash
mise run backend:yoyo -- new --message "what you want to do" ./ffun/<component>/migrations/
```

The migration path in the command above intentionally uses the path layout visible inside the backend container.

Production upgrades SHOULD apply migrations before starting the upgraded application version.

When upgrading across multiple versions with migration requirements, operators SHOULD follow the documented version-by-version migration order instead of skipping directly to the latest version.

## Tests

Tests for database-backed behavior SHOULD use the real test PostgreSQL service provided by the development environment.

Tests MUST be run through backend development container commands.

The preferred command for all backend tests is:

```bash
mise run backend:test
```

The preferred command for targeted backend tests is:

```bash
mise run backend:poetry -- run pytest <path>
```

Backend test setup SHOULD apply all migrations before database-backed tests run and roll them back after the test session.

Operation tests SHOULD cover persistence-backed state changes, returned entities, idempotency, empty inputs, duplicate inputs, expected constraint failures, and important `RETURNING` empty-result paths.

Transactional workflow tests SHOULD verify both successful multi-step behavior and failure paths that must leave the database unchanged.

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
