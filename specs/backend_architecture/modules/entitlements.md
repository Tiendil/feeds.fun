# Entitlements module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.entitlements` backend module.

## Scope

This specification covers entitlement kinds, source-owned grants, effective entitlement intervals, grant and revocation behavior, effective-state queries, cleanup, audit records, and business events.

Purchased-subscription lifecycles, payment-service-provider protocols, product pricing, frontend behavior, token consumption, and the concrete set of entitlement sources are out of scope.

## Dictionary

- `entitlement kind` - a predefined capability or limit with a stable identifier, merge policy, and lifetime status.
- `source` - a semantic identifier for one system allowed to maintain its own entitlement state.
- `grant transaction identifier` - the internal benefit transaction UUID for the causal operation that created one grant.
- `revoking transaction identifier` - the internal benefit transaction UUID for the causal operation that revoked one grant.
- `source entitlement` - one durable grant recorded by one source and grant transaction identifier for one user and entitlement kind.
- `active source entitlement` - a source entitlement whose activation time has arrived and whose expiration and optional revocation times have not arrived at the evaluation time.
- `effective entitlement interval` - a time interval during which merged source state grants one entitlement kind to one user with one value.
- `merge policy` - the operation used to combine values from active source entitlements of the same kind.
- `entitlement guarantee` - one entitlement kind and integer value promised by a benefit or another granting product concept.

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

One source entitlement MUST be identified by the exact tuple of source, grant transaction identifier, user id, and entitlement kind.

Source identifiers MUST be non-empty, and transaction identifiers MUST be UUIDs issued by the benefits transaction ledger.
A grant MUST contain an integer value and timezone-aware activation and expiration times, with activation earlier than expiration.
A grant being created MUST have neither a revocation time nor a revoking transaction identifier.

A source entitlement is inactive before activation, at or after expiration, and at or after a revocation time.
An already expired grant MAY be recorded, but it is immediately inactive.

After creation, only revocation state may change.
Correcting any other field requires a new grant transaction identifier.

Creating a grant whose identity and immutable values exactly match an existing grant MUST be a no-op.
Reusing the same identity with different immutable values MUST fail.
Retrying an identical grant after it has been revoked MUST remain a no-op and MUST NOT reactivate it.

Revocation MUST capture one current time and the revoking benefit transaction identifier.
The revocation time and revoking transaction identifier MUST either both be present or both be absent.
Revoking an already revoked grant MUST be a no-op and preserve its original revocation time and revoking transaction identifier.
Revoking a missing grant MUST fail.

A subscription-owned revocation MUST load every source entitlement associated with one internal subscription that is active at the evaluation time or can become active afterward.
It MUST process the loaded grants in deterministic user, entitlement-kind, source, and grant-transaction order.
When the subscription has no current or future source entitlements, the operation MUST return an empty result.

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
Grant and revocation operations MUST accept that evaluation time and the caller-owned transaction so a higher-level workflow can coordinate them atomically with its own state.

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
- `grant_source_entitlements` creates or retries one ordered collection of guarantees for a transaction and optional subscription owner.
- `revoke_source_entitlement` revokes or retries revocation of one source-owned grant.
- `revoke_subscription_entitlements` revokes every current or future source entitlement owned by one subscription.
- `get_entitlements` returns current effective intervals for requested users and kinds.
- `cleanup_expired_entitlements` removes expired effective intervals and returns the number removed.

`grant_source_entitlement` MUST accept a caller-owned transaction, one source entitlement containing `source_id`, grant transaction identifier, user id, kind id, value, activation, expiration, and no revocation state, the caller-captured evaluation time, and the audit actor.
It MUST return a source-change result describing whether state changed and the resulting effective state together with a zero-argument callback that emits the corresponding business events after commit.

`revoke_source_entitlement` MUST accept a caller-owned transaction, identify the grant by `source_id`, grant transaction identifier, user id, and kind id, and accept the revoking transaction identifier, caller-captured evaluation time, and audit actor.
It MUST return a source-change result and corresponding zero-argument business-event callback, and fail when the identified grant is missing.

`grant_source_entitlements` MUST accept a caller-owned transaction, one source identifier, one grant transaction identifier, one user, an optional subscription identifier, an ordered collection of guarantees, one activation and expiration interval, the caller-captured evaluation time, and the audit actor.
It MUST apply guarantees in deterministic entitlement-kind order and return the ordered source-change results and corresponding callbacks.

`revoke_subscription_entitlements` MUST accept a caller-owned transaction, one subscription identifier, one revoking transaction identifier, one revocation time, the caller-captured evaluation time, and the audit actor.
It MUST return the ordered source-change results and corresponding callbacks for every current or future source entitlement owned by the subscription, or empty collections when none exist.

These change operations MUST use the supplied transaction for source state, effective state, locking, and audit records and MUST NOT emit business events before commit.
When a change operation is a no-op, its returned business-event callback MUST also be a no-op.
After commit, the caller MUST invoke every returned business-event callback; after rollback, it MUST discard the callbacks without invoking them.
Post-commit callback invocation is best-effort: callback failure MUST NOT invalidate or roll back the committed source, effective, or audit state, and this module does not guarantee durable callback replay.

`ffun.entitlements.grant_source_entitlement`, `ffun.entitlements.revoke_source_entitlement`, `ffun.entitlements.grant_source_entitlements`, and `ffun.entitlements.revoke_subscription_entitlements` are explicitly approved to participate in the database transaction owned by `ffun.benefits.apply_subscription_transaction`.
They MAY accept and use that workflow's execute callable for source-entitlement persistence, effective-state persistence, locking, and audit records.
This exception does not allow benefits to import entitlement operations or access entitlement tables directly, and it does not approve transaction sharing for unrelated workflows.

`get_entitlements` MUST accept collections of user ids and entitlement kind ids.
Its result MUST map each selected user and kind to the active interval's user id, kind id, value, activation, and expiration, or to no value when the entitlement is not granted.

## Audit records

### `source_entitlement_changed`

Every non-no-op source change MUST append one `source_entitlement_changed` audit record in the same transaction as the state change.

The actor MUST identify the initiating user, administrator, payment service provider, or system component.
The subject MUST be the affected user.

The record attributes MUST include:

- `source_id`, identifying the owner of the changed grant.
- `grant_transaction_id`, identifying the transaction that created the grant.
- `revoked_by_transaction_id`, identifying the transaction that revoked the grant or `null` while it remains unrevoked.
- `kind_id`, identifying the entitlement kind.
- `previous_source_state`, containing the previous `source_id`, grant transaction identifier, user id, kind id, value, activation, expiration, revocation time, and revoking transaction identifier, or `null` for a new grant.
- `new_source_state`, containing the resulting `source_id`, grant transaction identifier, user id, kind id, value, activation, expiration, revocation time, and revoking transaction identifier.
- `previous_effective_intervals`, containing every previous current or future effective interval ordered by activation.
- `new_effective_intervals`, containing every resulting current or future effective interval ordered by activation.

Each effective-interval snapshot MUST contain its user id, kind id, value, activation, and expiration.

The audit record MUST be appended even when source state changes without changing the effective entitlement.
A no-op request MUST NOT append a record.

## Business events

The module MUST produce both events below for best-effort emission after every successful non-no-op source change.
No-op and rolled-back changes MUST NOT emit either event.
Failure while delivering an event after commit MUST NOT change durable entitlement state, and retrying an otherwise idempotent source operation MUST NOT replay that event.

### `source_entitlement_changed`

The event MUST describe the resulting source-owned grant.
It MUST use the affected user as the business-event user and include `source_id`, `grant_transaction_id`, `revoked_by_transaction_id`, `kind_id`, `granted`, `value`, `starts_at`, `expires_at`, and `revoked_at`.

### `entitlement_changed`

The event MUST describe the resulting effective state.
It MUST use the affected user as the business-event user and include:

- `kind_id`.
- `granted`.
- `value`, or `null` when not granted.
- `new_effective_intervals`, containing the resulting interval values, activation times, and expiration times.

The event MUST be emitted even when a source change leaves the effective timeline unchanged.
Time passage, queries, and cleanup MUST NOT emit either event.
