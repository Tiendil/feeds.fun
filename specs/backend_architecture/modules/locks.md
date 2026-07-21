# Locks module

## Goal of the document

This document describes how the `ffun.locks` backend module provides collision-free, transaction-scoped logical mutexes through PostgreSQL.

## Scope

This specification covers lock identity, lock acquisition and release, transaction ownership, the ephemeral lock table, failure behavior, and the public asynchronous context managers exposed by `ffun.locks.domain`.

Distributed coordination outside PostgreSQL, reader-writer locks, semaphores, long-lived leases, leader election, work queues, and administrative PostgreSQL maintenance are out of scope.

## Dictionary

- `logical mutex` - exclusive coordination identified by an application-defined kind and ordered arguments rather than by an existing business row.
- `lock kind` - a stable, module-namespaced string that identifies the purpose and argument semantics of a logical mutex.
- `lock arguments` - ordered scalar values that identify one mutex within a lock kind.
- `canonical lock key` - the deterministic, delimiter-separated ASCII serialization of the lock arguments.
- `acquisition row` - the ephemeral `lk_locks` row whose unique primary key coordinates transactions requesting the same logical mutex.
- `holder transaction` - the explicit database transaction that inserted an acquisition row and has not yet committed or rolled back.

## Module responsibility

`ffun.locks` MUST be a shared-service module that owns collision-free logical mutex identity, key validation and encoding, acquisition-row persistence, and the public lock context managers.

The module MUST provide technical transaction coordination only. Calling modules own the business meaning of each lock kind, the selection and ordering of lock arguments, the choice between caller-owned and lock-owned transaction boundaries, and all protected state changes.

The module MUST use exact unique database values rather than hashes or PostgreSQL advisory locks. Different logical mutexes MUST NOT block one another because of a hash collision.

The module MUST NOT create independent connection pools, reserve a second connection for a held lock, or coordinate through process-local state.

## Domain behavior

### Lock identity

A logical mutex MUST be identified by the exact pair `(lock_kind, canonical_lock_key)`.

Lock kinds MUST be non-empty lowercase `snake_case` strings. A calling module MUST namespace its kinds with enough context to prevent accidental reuse, for example `entitlements_user_kind`. A lock kind's meaning, argument count, argument order, and canonical conversions MUST remain stable after production code uses it.

Lock kinds intentionally use string identity. They form an open extension namespace owned by calling modules rather than a closed categorical set, so they are an explicit exception to the integer categorical-value preference in `specs/backend_architecture/db.md`.

`ffun.locks.entities` MUST define `LockKind` as the semantic string type used for lock kinds across module boundaries. Calling modules MUST construct lock kinds explicitly as `LockKind` values rather than passing unqualified strings.

Lock arguments MUST be ordered. Argument order and canonical string value are part of lock identity; the original Python type is not. The following argument types MUST be supported:

- `str`, including `enum.StrEnum` values and semantic string types created with `typing.NewType`, encoded unchanged.
- `int`, including semantic integer types created with `typing.NewType`, encoded in canonical base-10 form with a leading `-` for negative values and no redundant leading zeroes.
- `enum.IntEnum`, encoded as its integer value.
- `uuid.UUID`, encoded in its canonical lowercase hyphenated form.
- `bool`, encoded as lowercase `true` or `false`.

Floating-point values, byte sequences, containers, arbitrary objects, and other unsupported values MUST be rejected before database access. Implementations MUST use the conversions defined above rather than applying generic `str(...)` conversion to arbitrary objects.

Each converted argument MUST be non-empty and contain only ASCII letters, ASCII digits, `.`, `_`, `:`, `@`, `/`, or `-`. The pipe character `|` MUST separate adjacent converted arguments and MUST NOT be allowed inside an argument. The canonical lock key MUST be the converted arguments joined with `|`, without escaping, leading separators, or trailing separators. For example:

```text
74d7d6d5-24bc-4d90-bc84-45b5f0146b21|1|source|true
```

A lock MAY have no arguments; its canonical key is then the empty string. Empty converted arguments MUST be rejected so a one-argument lock cannot collide with the no-argument lock.

The delimiter and restricted alphabet make argument boundaries unambiguous without escaping or explicit type tags. Values from different Python types that have the same canonical string intentionally identify the same mutex. For example, integer `1` and string `"1"` both encode as `1`.

Canonical serialization MUST be deterministic for the same supported values. It MUST NOT use Python object hashes, randomized representations, lossy normalization, or direct concatenation without separators. Encoding changes MUST preserve coordination between concurrently deployed application versions.

The UTF-8 representation of a lock kind MUST NOT exceed 128 bytes. The UTF-8 representation of a canonical lock key MUST NOT exceed 1024 bytes. Oversized or otherwise invalid identity values MUST raise `ffun.locks.errors.InvalidLockKey` before database access. These conservative limits keep the composite primary key safely indexable and prevent unbounded caller-controlled lock records.

### Acquisition and release

Lock acquisition MUST insert one acquisition row with a plain `INSERT` through the holder transaction's execute callable. The insert MUST NOT use `ON CONFLICT`, an upsert, or a preliminary existence query.

The immediate primary-key uniqueness check is the synchronization primitive. When another transaction has inserted the exact same primary key but has not completed, PostgreSQL waits for that transaction and then rechecks the conflict:

- if the holder transaction commits after deleting its acquisition row, the waiting insert succeeds.
- if the holder transaction rolls back, the waiting insert succeeds.
- if a transaction commits a live acquisition row, the waiting insert fails with a uniqueness violation.

The context manager MUST enter the protected body only after its insert succeeds.

On normal context exit, the context manager MUST delete its acquisition row through the same execute callable. The delete MUST verify that exactly one row was deleted.

On exceptional exit from a caller-owned lock context, the context manager SHOULD delete its acquisition row when the transaction remains usable. If the protected operation has already put the transaction into a failed state, rollback is the cleanup mechanism. Cleanup failure MUST NOT suppress the original protected-operation exception.

On exceptional exit from a transaction-owning lock context, the context manager MUST roll back its holder transaction. It does not need to delete the acquisition row separately because rollback removes the insertion atomically with the protected work.

Insert and delete MUST belong to the same holder transaction. Their successful commit leaves no live acquisition row. Rollback at any point also leaves no live acquisition row.

Deleting the acquisition row does not release the mutex immediately: competing uniqueness checks continue to wait until the holder transaction commits or rolls back. Callers using `Lock` SHOULD complete the surrounding transaction promptly after leaving the lock context; `locked_transaction` completes its transaction as part of context exit.

### Transaction contract

Every logical mutex MUST run inside one explicit database transaction that contains both its acquisition row and all protected database work.

`Lock` MUST participate in a caller-owned transaction. The execute callable passed to `Lock` MUST be the execute callable of that transaction.

`Lock` MUST NOT open, commit, or roll back a transaction. It MUST NOT call the top-level autocommitted execute helper for acquisition or cleanup.

Passing an autocommitted execute callable to `Lock` violates this contract because acquisition could commit a live row before cleanup. Such a row would survive process failure and prevent future acquisition.

`locked_transaction` MUST own its transaction through the shared transaction infrastructure in `ffun.core.postgresql`. It MUST NOT open an additional connection after starting that transaction, and it MUST use the owned transaction's execute callable for acquisition, cleanup, and protected work.

Calling code MUST NOT use `locked_transaction` inside an existing database transaction. It MUST use `Lock` when the logical mutex needs to participate in a transaction whose boundary is already owned by the caller.

The protected database reads and writes MUST use the same transaction execute callable. Using a separate transaction for protected state would allow the lock lifecycle and protected state change to succeed or fail independently.

The mutex is held until the holder transaction completes. Consequently, leaving a `Lock` context does not make the key available while its caller-owned transaction remains open. Leaving a `locked_transaction` context completes its owned transaction, so its lexical context and mutex lifetime coincide.

The lock is not reentrant. Code MUST NOT nest acquisition of the same canonical lock identity within one transaction. Such an insertion conflicts with the transaction's own acquisition row and invalidates the transaction.

When one transaction needs multiple logical mutexes, it MUST acquire them in deterministic order by their canonical `(lock_kind, lock_key)` pairs and release the contexts in reverse order. Calling modules SHOULD acquire logical mutexes before locking or mutating other database rows to reduce deadlock risk.

PostgreSQL statement cancellation, lock timeouts, deadlock detection, connection failures, and other unexpected infrastructure failures MUST propagate and cause the holder transaction to roll back.

### Required verification

Module tests MUST use the real test PostgreSQL service for concurrency behavior. They MUST verify that:

- a second transaction requesting the same identity waits until the holder transaction completes and then acquires the mutex.
- leaving the lock context does not unblock a waiter before the holder transaction completes.
- successful exit from `locked_transaction` commits protected work, removes the acquisition row, and then allows a waiter to enter.
- exceptional exit from `locked_transaction` rolls back both protected work and the acquisition row before allowing a waiter to enter.
- different lock identities can be acquired concurrently.
- normal commit, protected-body failure, and transaction rollback leave no live acquisition rows.
- a deliberately committed acquisition row causes `LockInvariantViolation` rather than silent takeover.
- canonical encoding distinguishes argument boundaries and argument order, allows boolean values, and intentionally gives integer and string values the same identity when their canonical strings match.
- invalid, unsupported, and oversized identity values are rejected before any acquisition row is inserted.

### Invariant violations

A committed acquisition row violates the module's lifecycle invariant. Normal acquisition MUST NOT silently delete, replace, or take ownership of such a row.

The module MUST convert a uniqueness violation caused by an existing committed row or by same-transaction reentrant acquisition into `ffun.locks.errors.LockInvariantViolation`. The affected transaction remains failed and MUST roll back.

If normal cleanup does not delete exactly one acquisition row, the module MUST raise `LockInvariantViolation` so the holder transaction rolls back.

`ffun.locks.errors` MUST define the module root `Error`, `InvalidLockKey`, and `LockInvariantViolation` according to `specs/backend_architecture/errors.md`.

## Database schema

### `lk_locks`

The module MUST own exactly one table, `lk_locks`.

```sql
-- Ephemeral exact-key rows used to coordinate holder transactions.
CREATE TABLE lk_locks (
    lock_kind TEXT COLLATE "C" NOT NULL, -- Stable open namespace; C collation preserves exact textual identity.
    lock_key TEXT COLLATE "C" NOT NULL, -- Canonical ASCII key; C collation preserves exact textual identity.
    PRIMARY KEY (lock_kind, lock_key) -- Immediate exact-key uniqueness coordinates competing transactions.
);
```

The primary key MUST be immediate and non-deferrable. Its exact uniqueness behavior is the mutex implementation and MUST NOT be replaced with hash uniqueness.

The `"C"` collation MUST be used so textual primary-key identity follows deterministic exact values rather than locale-sensitive equivalence.

The table intentionally omits `created_at` and `updated_at`. Acquisition rows have no durable lifecycle: they MUST be inserted and deleted in one transaction or removed by rollback, and no live row may commit. Timestamps would therefore describe neither durable creation nor mutation and would add width and write churn to a hot technical table.

No secondary indexes are required because runtime acquisition and release address the complete primary key and normal committed state contains no rows. The table MUST NOT define foreign keys, business-value constraints, ownership columns, lease deadlines, or payload columns.

Normal committed state MUST contain zero live rows. Insert-and-delete transactions still create dead tuples and write-ahead-log traffic, so ordinary PostgreSQL vacuum behavior and operational monitoring remain relevant even though the logical table does not grow without bound.

The module MUST NOT expose normal runtime cleanup that deletes committed rows. A committed row indicates transaction-contract misuse or an implementation defect and requires explicit diagnosis before repair.

## Domain interface

### `Lock`

`ffun.locks.domain` MUST expose an asynchronous context manager named `Lock`.

`Lock` MUST accept:

- the caller's transaction-scoped `ffun.core.postgresql.ExecuteType` as its first argument.
- a `LockKind` as its second argument.
- zero or more positional lock arguments after the kind.

The interface SHOULD be used in this form:

```python
from ffun.core.postgresql import transaction
from ffun.locks.domain import Lock
from ffun.locks.entities import LockKind

async with transaction() as execute:
    async with Lock(execute, LockKind("entitlements_user_kind"), user_id, kind_id):
        # Read and change the state protected by this logical mutex.
        ...
```

On context entry, `Lock` MUST validate and encode the identity, insert the acquisition row, wait when another holder transaction owns the same identity, and enter the protected body only after acquisition.

On context exit, `Lock` MUST perform the release behavior defined above and MUST NOT suppress exceptions from the protected body.

`Lock` SHOULD be used when the caller already owns a transaction or when one transaction must acquire multiple logical mutexes.

### `locked_transaction`

`ffun.locks.domain` MUST expose an asynchronous context manager named `locked_transaction`.

`locked_transaction` MUST accept:

- a `LockKind` as its first argument.
- zero or more positional lock arguments after the kind.

The interface SHOULD be used in this form:

```python
from ffun.locks.domain import locked_transaction
from ffun.locks.entities import LockKind

async with locked_transaction(LockKind("entitlements_user_kind"), user_id, kind_id) as execute:
    # All protected database work uses the yielded transaction execute callable.
    ...
```

On context entry, `locked_transaction` MUST validate and encode the lock identity, open one transaction through `ffun.core.postgresql`, insert the acquisition row through that transaction, wait when another holder owns the same identity, and yield the transaction's `ExecuteType` callable after acquisition.

If transaction creation or acquisition fails, `locked_transaction` MUST roll back and close the transaction before propagating the failure.

On successful body completion, `locked_transaction` MUST delete exactly one acquisition row and commit the transaction before returning. The mutex is released by that commit.

On exceptional body completion, `locked_transaction` MUST roll back the transaction and MUST NOT suppress the protected-body exception. The mutex is released by that rollback.

`locked_transaction` SHOULD be preferred when the protected workflow can give it ownership of the complete transaction because its lexical context then accurately represents the mutex lifetime.

`locked_transaction` and `Lock` MUST use the same lock identity, acquisition, cleanup, and invariant-violation behavior.

Calling modules MUST import `Lock` and `locked_transaction` from `ffun.locks.domain`. They MUST NOT depend on the acquisition-row schema directly.

## Audit records

Module does not produce audit records because logical mutex acquisition is transient technical coordination rather than a durable business fact.

## Business events

Module does not produce business events. Calling modules own any business events generated by state changes performed while a logical mutex is held.
