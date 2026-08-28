# Locks module

## Goal of the document

This document describes the responsibility and observable coordination behavior of the `ffun.locks` backend module.

## Scope

This specification applies to transaction-scoped logical mutual exclusion provided by `ffun.locks` for backend work.
Business decisions about when coordination is required and forms of coordination other than logical mutual exclusion are outside the module's responsibility.

## Dictionary

- `logical mutex` - exclusive coordination identified by a caller-defined purpose and ordered identifying values rather than by an existing business entity.
- `lock kind` - a stable, module-namespaced purpose that distinguishes one family of logical mutexes.
- `protected work` - work whose effects require exclusive ownership of one logical mutex.
- `holder transaction` - the database transaction that contains the protected work and whose outcome determines the logical-mutex lifetime.

## Module responsibility

The module owns validity and equivalence of logical-mutex identities, exclusive ownership of each logical mutex, and the lifecycle invariants that bind that ownership to protected work.
Calling modules own each lock kind's business meaning, the selection and ordering of identifying values, the decision to coordinate, and every business effect produced by protected work.
The module provides technical coordination and MUST NOT become the authority for protected business policy.

## Special module rules

`ffun.locks` is intentionally available to other top-level backend modules as an approved participant in their database transactions.
Its participation MUST remain limited to logical mutual exclusion and, when requested by a caller, the technical lifecycle of the holder transaction.
Participation MUST NOT transfer ownership of the business workflow or its state changes to `ffun.locks`.

## Domain model

A logical mutex is a transient coordination entity for protected work that must not overlap.
Its immutable identity combines one caller-owned lock kind with an ordered sequence of identifying scalar values; a lock kind alone MAY form a complete identity.
The identity MUST be deterministic, unambiguous across value boundaries, and stable across application versions that may run concurrently.
Callers MUST prevent accidental reuse of a lock kind and preserve its identity semantics after production use.

Each logical-mutex holding belongs to exactly one holder transaction that contains all protected database effects.
A logical mutex MUST have at most one current holder transaction.
The holding MUST end only when the holder transaction commits or rolls back; the module owns no historical state for a completed holding.

## Domain behavior

### Identity validity

The module MUST reject a proposed identity when its kind or identifying values cannot produce a stable and unambiguous logical-mutex identity.
Rejection MUST occur before the proposed identity has any coordination effect.

Identity behavior MUST remain compatible across concurrently deployed application versions.
A version change MUST NOT allow protected work that previously shared one identity to overlap.

### Mutual exclusion

Protected work MUST begin only after its holder transaction holds the logical mutex.
When one holder transaction holds an identity, competing transactions MUST wait until it commits or rolls back before one becomes the next holder.
Different logical-mutex identities MUST remain independently acquirable.

The logical mutex MUST NOT become available before the holder transaction commits or rolls back.
Either transaction outcome MUST leave no live holding.

### Transaction participation

The module MUST support both participation in an existing caller-owned holder transaction and establishment of a holder transaction for protected work.
When the holder transaction is caller-owned, its outcome remains under the caller's workflow authority and the logical mutex remains bound to that outcome.

When coordination establishes the holder transaction, all protected effects and the mutex lifecycle MUST share its outcome.
Successful protected work MUST commit before the logical mutex becomes available, while failed protected work MUST roll back before the mutex becomes available.

### Failure behavior

The same holder transaction MUST NOT acquire the same logical-mutex identity more than once; such an attempt MUST fail the transaction.

If the module cannot establish or preserve exclusive ownership, it MUST report a coordination failure rather than continue or silently assume ownership, and the protected work MUST NOT succeed.
An error produced by the protected work MUST remain the primary reported failure even when ending the holding also fails.

## Audit records

This module produces no audit records because logical-mutex holdings are transient technical coordination rather than durable business facts.

## Business events

This module produces no business events because calling modules own the events produced by protected state changes.
