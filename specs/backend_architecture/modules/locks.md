# Locks module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.locks` backend module.

## Scope

This specification covers logical-mutex identity, validation, acquisition, release, transaction participation, concurrency, and failure behavior.

Reader-writer locks, semaphores, long-lived leases, leader election, work queues, cross-system distributed coordination, and administrative repair are out of scope.

## Dictionary

- `logical mutex` - exclusive coordination identified by an application-defined kind and ordered arguments rather than by an existing business row.
- `lock kind` - a stable, module-namespaced string that identifies the purpose and argument semantics of a logical mutex.
- `lock arguments` - ordered scalar values that identify one mutex within a lock kind.
- `canonical lock key` - the deterministic serialization of lock arguments used to compare logical-mutex identity.
- `holder transaction` - the transaction that owns a logical mutex until it commits or rolls back.

## Module responsibility

The module MUST own logical-mutex identity, key validation and canonicalization, collision-free mutual exclusion, and caller-owned and module-owned transaction contexts.

Calling modules MUST own the business meaning of each lock kind, argument selection and ordering, transaction-boundary choice, and all protected state changes.

The module MUST provide technical transaction coordination only.

`ffun.locks` is an approved transaction participant under the backend database architecture.
Calling modules MAY use either lock context for the module's technical responsibility without workflow-specific transaction-sharing approval.
Using either lock context MUST NOT transfer ownership of the protected business workflow or its database operations to `ffun.locks`.
For `locked_transaction`, opening and completing the holder transaction is technical lifecycle ownership; yielding its execute callable to the calling module's protected operations is intended usage.

## Domain behavior

### Lock identity

A logical mutex MUST be identified by the exact pair of lock kind and canonical lock key.

A lock kind MUST be a non-empty lowercase `snake_case` string.
Calling modules MUST namespace kinds sufficiently to prevent accidental reuse.
A kind's meaning, argument count, argument order, and canonical conversions MUST remain stable after production use.

Lock kinds form an open namespace owned by callers.

Lock arguments MUST be ordered.
Their canonical values and positions are part of the identity, while their original language-level types are not.

The interface MUST accept these argument categories:

- strings, preserved unchanged.
- integers, encoded in canonical base-10 form.
- integer categorical values, encoded by their integer value.
- UUID values, encoded in canonical lowercase hyphenated form.
- booleans, encoded as lowercase `true` or `false`.

Floating-point values, byte sequences, containers, arbitrary objects, and other unsupported values MUST be rejected.

Each encoded argument MUST be non-empty and contain only ASCII letters, ASCII digits, `.`, `_`, `:`, `@`, `/`, or `-`.
Adjacent arguments MUST be separated by `|`, which MUST NOT occur inside an argument.
No escaping, leading separator, or trailing separator is permitted.

A mutex MAY have no arguments, in which case its canonical key is empty.
Empty argument values MUST be rejected so a one-argument mutex cannot share the no-argument identity.

Values from different supported categories that have the same canonical text intentionally identify the same mutex.
For example, integer `1` and string `"1"` have the same identity.

Canonicalization MUST be deterministic and collision-free with respect to argument boundaries.
It MUST NOT use object hashes, randomized representations, lossy normalization, or concatenation without separators.
Canonicalization changes MUST preserve coordination between concurrently deployed application versions.

A lock kind MUST NOT exceed 128 bytes, and a canonical lock key MUST NOT exceed 1024 bytes.
Invalid, unsupported, or oversized identities MUST fail before coordination state is accessed.

### Mutual exclusion

The protected body MUST begin only after the logical mutex has been acquired.

When another transaction holds the same identity, acquisition MUST wait until that transaction commits or rolls back and then acquire the mutex.
Different identities MUST be independently acquirable.

The mutex MUST remain held until the holder transaction completes.
Leaving a caller-owned lock context MUST therefore not make the identity available while its surrounding transaction remains open.

Successful transaction completion MUST leave no live coordination state.
Rollback at any point MUST also leave no live coordination state.

### Transaction contract

Every logical mutex MUST belong to one explicit transaction that also contains all protected work.

The caller-owned context MUST participate in the transaction supplied by its caller.
It MUST NOT open, commit, or roll back that transaction.

The module-owned context MUST create one transaction and use it for acquisition, protected work, and release.
It MUST commit after successful protected work and roll back after exceptional protected work.

Protected transactional reads and writes MUST use the holder transaction.
Using another transaction would allow mutex lifecycle and protected state changes to succeed or fail independently.

Calling code MUST NOT use the module-owned context inside an existing transaction.
It MUST use the caller-owned context when the mutex must participate in a transaction whose boundary already exists.

### Context completion and failures

On normal exit, a context MUST complete its release behavior without suppressing caller behavior.

On exceptional exit from a caller-owned context, release SHOULD be attempted while the transaction remains usable.
If release fails while a protected-body exception is already propagating, the cleanup failure MUST NOT replace the original exception.

On exceptional exit from a module-owned context, the holder transaction MUST roll back and the protected-body exception MUST propagate.

Unexpected transaction failures, timeouts, cancellation, deadlock detection, and connection failures MUST propagate and cause the holder transaction to roll back.

The mutex MUST NOT be reentrant.
Acquiring the same identity twice within one transaction MUST fail and require rollback.

When one transaction needs multiple logical mutexes, callers MUST acquire them in deterministic identity order and release their contexts in reverse order.
Callers SHOULD acquire logical mutexes before locking or mutating other state to reduce deadlock risk.

### Lifecycle invariant failures

Committed coordination state violates the mutex lifecycle.
Normal acquisition MUST NOT silently delete, replace, or take ownership of such state.

Acquisition MUST report a module-level invariant failure when it encounters committed coordination state or same-transaction reentrant acquisition.
Release MUST report the same category of failure when the expected held identity is absent.
The affected transaction MUST roll back.

## Public interface

The public interface MUST provide:

- `Lock`, an asynchronous caller-owned transaction context.
- `locked_transaction`, an asynchronous module-owned transaction context.

`Lock` MUST accept the caller's transaction execution context, one lock kind, and zero or more positional lock arguments.
It MUST validate the identity, wait for acquisition, and enter the protected body only after acquisition.
It MUST not suppress exceptions from the protected body.

`locked_transaction` MUST accept one lock kind and zero or more positional lock arguments.
It MUST validate the identity before opening a transaction.
After acquisition, it MUST yield the owned transaction execution context for all protected database work.

Successful exit from `locked_transaction` MUST commit protected work and make the mutex available.
Exceptional exit MUST roll back protected work and make the mutex available before propagating the exception.

Both contexts MUST use the same identity, acquisition, release, and lifecycle-invariant behavior.

## Audit records

Module does not produce audit records because mutex acquisition is transient technical coordination rather than a durable business fact.

## Business events

Module does not produce business events because calling modules own events generated by protected state changes.
