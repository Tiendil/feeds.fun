# Entitlements module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.entitlements` backend module.

## Scope

This specification covers entitlement kinds, source-owned grants, effective entitlement intervals, grant and revocation behavior, effective-state queries, cleanup, audit records, and business events.

Purchased-subscription lifecycles, payment-service-provider protocols, product pricing, frontend behavior, token consumption, and the concrete set of entitlement sources are out of scope.

## Dictionary

- `entitlement kind` - a predefined capability or limit with a stable identifier, merge policy, and lifetime status.
- `source` - a semantic identifier for one system allowed to maintain its own entitlement state.
- `transaction id` - a stable source-supplied identifier for one grant to one user and entitlement kind.
- `source entitlement` - one durable grant recorded by one source and transaction id for one user and entitlement kind.
- `active source entitlement` - a source entitlement whose activation time has arrived and whose expiration and optional revocation times have not arrived at the evaluation time.
- `effective entitlement interval` - a time interval during which merged source state grants one entitlement kind to one user with one value.
- `merge policy` - the operation used to combine values from active source entitlements of the same kind.

## Module responsibility

The module MUST own entitlement-kind metadata, source-owned entitlement state, effective-state derivation, grant and revocation workflows, effective-state queries, and expired-effective-state cleanup.

Sources MUST change entitlements through the public module boundary.
They MUST NOT change another source's state.

Callers that check entitlements MUST use the module's effective-state queries.
They MUST NOT independently reproduce merge behavior or derive access from source-owned grants.

## Domain behavior

### Entitlement kinds

Entitlement kinds MUST form a closed set of stable identifiers.
Each kind MUST define one merge policy and whether grants of that kind are lifetime grants.

The supported kinds MUST be:

- `day_tokens`, stable value `1`, merged using `max`, and not lifetime.
- `month_tokens`, stable value `2`, merged using `max`, and not lifetime.
- `lifetime_tokens`, stable value `3`, merged using `sum`, and lifetime.

Stable kind values MUST NOT be changed or reused.

The supported merge policies MUST be:

- `max`, which selects the largest active value.
- `min`, which selects the smallest active value.
- `sum`, which adds all active values.

Merging an empty value collection MUST fail.

Non-lifetime grants MUST use a source-supplied expiration time.
Lifetime grants MUST use the project's stable lifetime interval-end marker.
The marker represents an unbounded interval and MUST NOT be interpreted as a semantic expiration.

### Source-owned grants

One source entitlement MUST be identified by the exact tuple of source, transaction id, user id, and entitlement kind.

Source and transaction identifiers MUST be non-empty.
A grant MUST contain an integer value and timezone-aware activation and expiration times, with activation earlier than expiration.
A grant being created MUST not already be revoked.

A source entitlement is inactive before activation, at or after expiration, and at or after a revocation time.
An already expired grant MAY be recorded, but it is immediately inactive.

After creation, only revocation state may change.
Correcting any other field requires a new transaction id.

Creating a grant whose identity and immutable values exactly match an existing grant MUST be a no-op.
Reusing the same identity with different immutable values MUST fail.
Retrying an identical grant after it has been revoked MUST remain a no-op and MUST NOT reactivate it.

Revocation MUST capture one current time.
Revoking an already revoked grant MUST be a no-op and preserve its original revocation time.
Revoking a missing grant MUST fail.

Future-dated and multiple same-source grants MUST coexist.
The `lifetime_tokens` effective value MUST be the sum of all active lifetime grants.

### Effective entitlement intervals

Effective entitlement intervals MUST be derived from all source-owned grants for one user and kind.
They MUST be half-open: activation is inclusive and expiration is exclusive.

At any time, at most one effective interval may cover one user and kind.
Absence of a covering interval means the entitlement is not granted.

Each interval MUST have the value produced by applying the kind's merge policy to every source entitlement active throughout that interval.
Periods with no active source entitlement MUST be omitted.
Adjacent intervals with equal values MUST be represented as one interval.

Derivation MUST preserve every current and future interval whose end is later than the evaluation time.
Expired effective intervals MAY remain until cleanup, but they MUST NOT affect query results.

The effective state at an evaluation time MUST be represented as granted with an integer value when an interval covers that time, and not granted with no value otherwise.

### Source-change workflow

Each non-no-op grant or revocation MUST atomically change source-owned state, update the complete affected effective timeline, and append the required audit record.
Changes for the same user and entitlement kind MUST be serialized.

The workflow MUST use one captured evaluation time for validation, revocation, effective-state derivation, audit data, and the returned state.

Failure at any point MUST leave source-owned state, effective intervals, and audit history unchanged.

Business events MUST be emitted only after the state and audit transaction succeeds.
No-op and failed workflows MUST NOT emit them.

### Effective-state queries

Every query MUST capture one evaluation time and treat an interval as active exactly when its activation is not later than that time and its expiration is later than that time.
Queries MUST NOT mutate entitlement state merely because time has passed.

A batch query MUST return an entry for every requested user and selected entitlement kind.
Each entry MUST contain the complete active interval or no value.

An empty entitlement-kind selection MUST select every supported kind.
Duplicate user or kind identifiers MUST behave as one request for the duplicated value.
Unknown kind identifiers MUST fail.

### Cleanup

Cleanup MUST capture one cleanup time and remove only effective intervals that have expired by that time.
It MUST NOT remove source-owned grants.
It MUST return the number of effective intervals removed.

## Public interface

The public interface MUST provide these operations:

- `get_entitlement_kind` returns the stable metadata for one entitlement kind and fails for an unknown kind.
- `grant_source_entitlement` creates or retries one source-owned grant.
- `revoke_source_entitlement` revokes or retries revocation of one source-owned grant.
- `get_entitlements` returns current effective intervals for requested users and kinds.
- `cleanup_expired_entitlements` removes expired effective intervals and returns the number removed.

`grant_source_entitlement` MUST accept one source entitlement containing source, transaction id, user id, kind id, value, activation, expiration, and no revocation time.
It MUST also accept the audit actor's kind and canonical identifier.
It MUST return the effective granted state and value at the workflow's evaluation time.

`revoke_source_entitlement` MUST identify the grant by source, transaction id, user id, and kind id and accept the audit actor.
It MUST capture the revocation time internally and return the effective state after the workflow.

`get_entitlements` MUST accept collections of user ids and entitlement kind ids.
Its result MUST map each selected user and kind to the active interval's user id, kind id, value, activation, and expiration, or to no value when the entitlement is not granted.

## Audit records

### `source_entitlement_changed`

Every non-no-op source change MUST append one `source_entitlement_changed` audit record in the same transaction as the state change.

The actor MUST identify the initiating user, administrator, payment service provider, or system component.
The subject MUST be the affected user.

The record attributes MUST include:

- `source`, identifying the owner of the changed grant.
- `transaction_id`, identifying the changed source transaction.
- `kind_id`, identifying the entitlement kind.
- `previous_source_state`, containing the previous source, transaction id, user id, kind id, value, activation, expiration, and revocation values, or `null` for a new grant.
- `new_source_state`, containing the resulting source, transaction id, user id, kind id, value, activation, expiration, and revocation values.
- `previous_effective_intervals`, containing every previous current or future effective interval ordered by activation.
- `new_effective_intervals`, containing every resulting current or future effective interval ordered by activation.

Each effective-interval snapshot MUST contain its user id, kind id, value, activation, and expiration.

The audit record MUST be appended even when source state changes without changing the effective entitlement.
A no-op request MUST NOT append a record.

## Business events

The module MUST emit both events below after every successful non-no-op source change.
No-op and rolled-back changes MUST NOT emit either event.

### `source_entitlement_changed`

The event MUST describe the resulting source-owned grant.
It MUST use the affected user as the business-event user and include `source`, `transaction_id`, `kind_id`, `granted`, `value`, `starts_at`, `expires_at`, and `revoked_at`.

### `entitlement_changed`

The event MUST describe the resulting effective state.
It MUST use the affected user as the business-event user and include:

- `kind_id`.
- `granted`.
- `value`, or `null` when not granted.
- `new_effective_intervals`, containing the resulting interval values, activation times, and expiration times.

The event MUST be emitted even when a source change leaves the effective timeline unchanged.
Time passage, queries, and cleanup MUST NOT emit either event.
