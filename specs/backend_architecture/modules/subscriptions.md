# Subscriptions module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.subscriptions` backend module.

## Scope

This specification applies to provider-independent current-state projections of purchased subscriptions owned by `ffun.subscriptions`.

Payment collection, provider APIs and notification protocols, provider object identities, checkout and customer-portal workflows, invoices and payment attempts, product catalogs and pricing, benefit-package configuration, benefit-transaction history, entitlement derivation, resource accounting, and frontend presentation are out of scope.

## Dictionary

- `subscription identifier` - the internally generated UUID that identifies one subscription projection.
- `state transaction identifier` - the internal benefit transaction UUID whose application most recently changed the persisted subscription projection.
- `subscription status` - the normalized provider-neutral lifecycle state stored for a subscription.
- `alive subscription` - a subscription whose latest stored status and end time indicate that it has not ended at the evaluation time.
- `provider status` - the open-ended status value supplied by the external subscription authority.
- `subscription snapshot` - the complete provider-independent caller-supplied state of one subscription at one provider update time.
- `benefit identifier` - the stable local identifier of the configured benefit package associated with a subscription.
- `subscription period` - the required start and end timestamps of the current benefit-bearing subscription period.
- `expected renewal` - the optional externally reported time at which the subscription is expected to renew; it is an observation, not a renewal scheduled or managed by this module.
- `business state` - every subscription snapshot field except the provider update time.
- `audit state` - every subscription snapshot field except the Feeds Fun user identifier represented separately by the audit record.
- `business event attributes` - the subscription identifier, state transaction identifier, and every subscription snapshot field except the Feeds Fun user identifier represented separately by the business event.
- `save outcome` - the high-level business result of saving one subscription snapshot.

## Module responsibility

The module MUST own internal subscription identifiers, current subscription snapshots, their causal state-transaction references, benefit identifiers, normalized statuses, provider statuses, lifecycle timestamps, durable state replacement, current-state queries, audit records, and business events.

The external subscription provider remains authoritative for commercial subscription state.
The module MUST represent the latest accepted state locally and MUST NOT independently infer provider-side state transitions.

Callers MUST read and change locally persisted subscription state through the public module boundary.
They MUST NOT reproduce validation, freshness, ownership, or replacement behavior.

The module MUST NOT own payment-provider communication or provider object identities, subscription items, product catalogs or pricing, provider-product-to-benefit resolution, benefit-package configuration, benefit-transaction history, payment or invoice state, application of entitlement grants, resource limits, or access decisions.
Provider provenance and the mapping from provider subscription references to internal subscription identifiers belong to immutable benefit transactions.
The module MUST NOT persist benefit titles, descriptions, or entitlement guarantees.
Callers MUST resolve benefit details and apply guarantees through the benefits domain boundary.

## Domain behavior

### Subscription identity, causality, and ownership

Every subscription MUST have one internally generated UUID.
The identifier MUST remain stable for the lifetime of the subscription projection and MUST NOT encode a provider identity.

Every persisted subscription MUST reference the internal benefit transaction that created or most recently changed its stored snapshot.
The reference is a logical cross-module identifier and MUST NOT be implemented as a database foreign key to a table owned by another module.

Each subscription MUST be associated with exactly one Feeds Fun user.
The user association MUST remain immutable after creation.
Reusing an existing subscription identifier with a different user MUST fail.

The benefit identifier is mutable because the external authority MAY move one subscription to another product.
A user MAY have multiple subscriptions, and different internal subscription identifiers MUST be stored and queried independently.

### Subscription statuses

Normalized subscription statuses MUST form a closed set of stable identifiers.
The supported statuses MUST be:

- `pending`, stable value `1`, meaning the subscription is not yet commercially active but may still become active.
- `trialing`, stable value `2`, meaning the subscription is in a provider-recognized trial period.
- `active`, stable value `3`, meaning the provider reports the subscription in good standing.
- `past_due`, stable value `4`, meaning the provider reports an overdue but potentially recoverable subscription.
- `paused`, stable value `5`, meaning the provider reports the subscription temporarily suspended.
- `ended`, stable value `6`, meaning the provider reports the subscription ended and no longer current.

Assigned status identifiers MUST NOT be changed or reused.

Subscriptions with normalized status `pending`, `trialing`, `active`, `past_due`, or `paused` MUST be eligible to be counted as alive.
An eligible subscription MUST be counted as alive at an evaluation time only when its end timestamp is absent or later than the evaluation time.
A subscription whose normalized status is `ended`, or whose end timestamp is present and not later than the evaluation time, MUST NOT be counted as alive.

Every subscription MUST contain both one normalized status and the non-empty provider status from which the caller obtained the normalized state.
Provider statuses MUST remain open-ended external strings and MUST NOT be validated against a provider-specific closed set by this module.

The module MUST NOT assign entitlement, access, or resource-limit meaning to any subscription status.
Callers that make access decisions MUST use the owning domain boundaries for those decisions rather than infer access from subscription state.

Status transitions MUST be accepted from any supported status to any supported status when supplied by a newer valid snapshot.
The module MUST NOT reject a newer snapshot merely because its transition would be unusual for a particular provider.

Time passage alone MUST NOT change a stored subscription status.
Queries MUST NOT mutate subscription state when a renewal or end time passes.
Time passage MAY cause an alive-subscription query to stop returning a subscription when its stored end timestamp is reached.

### Lifecycle timestamps

Every subscription snapshot MUST contain timezone-aware subscription-start, current-period start, current-period end, and provider-update timestamps.
The current-period start MUST be earlier than the current-period end.

The expected-renewal and end timestamps MAY be absent.
When present, each MUST be timezone-aware.

The expected-renewal timestamp MUST record an expectation received from the external subscription authority.
The module MUST NOT interpret it as a locally managed renewal schedule, and it MUST be absent when no renewal is expected.
The end timestamp MUST describe either the scheduled end of a subscription that has not ended yet or the actual end reported for an ended subscription.
Callers MUST interpret the end timestamp together with the normalized status.

### Benefit references

A subscription snapshot MUST contain the local benefit identifier resolved from trusted provider product metadata.

The subscription module MUST store and return that reference without independently inferring a benefit.
It MUST NOT persist provider product or other provider object identifiers; the causal benefit transaction owns that provenance.
It MUST NOT copy benefit display details or entitlement guarantees into subscription persistence, query a payment provider for benefit details, or directly change entitlement state.

### Snapshot validation and replacement

A subscription snapshot MUST be validated completely before persisted state changes.
Invalid ownership, status, or timestamp data MUST fail without changing stored state.

At most one current snapshot MUST exist for one internal subscription identifier.
Creating a missing identifier MUST durably store the complete snapshot and supplied state transaction identifier and produce the `created` save outcome.

A snapshot whose provider update time is earlier than the stored provider update time MUST be a stale no-op and produce the `skipped` save outcome.
A snapshot with the same provider update time and identical business state MUST be an idempotent no-op and produce the `skipped` save outcome.
A snapshot with the same provider update time and different business state MUST fail as an ambiguous conflict.

A snapshot whose provider update time is later than the stored provider update time and whose business state differs MUST replace the complete mutable business state, advance the stored provider update time, record the supplied state transaction identifier, and produce the `updated` save outcome.
When only the provider update time differs, the module MAY advance that time and the state transaction identifier but MUST produce the `skipped` save outcome because the business state did not change.
A stale or idempotent no-op MUST preserve the stored state transaction identifier.

Replacement of a subscription's state transaction identifier, benefit identifier, status, provider status, subscription period, lifecycle timestamps, and provider update time MUST be atomic.
Concurrent replacements for the same internal subscription identifier MUST serialize their freshness decisions so older state cannot overwrite newer state.

Failure at any point in a business-state replacement MUST leave the previous snapshot and audit history unchanged.
Business events MUST be emitted only after the new state and required audit record become durable.

### Current-state queries

An identity query MUST return the complete current subscription for the exact requested internal subscription identifier, or no value when it is unknown.

A user query without a status filter MUST return every current subscription associated with the requested user, including subscriptions whose normalized status is `ended`.
When a status filter is supplied, the query MUST return only subscriptions whose normalized status is included in the filter.
An empty status filter MUST produce an empty subscription list.

An alive-subscription query MUST follow the same result shape but include only subscriptions counted as alive at the query's evaluation time.

Subscriptions for one user MUST be ordered by subscription start descending, then by internal subscription identifier ascending.
Queries MUST be read-only and MUST NOT produce audit records or business events.

## Public interface

The public interface MUST provide these operations:

- `new_subscription_id` generates one internal subscription identifier.
- `save_subscription` creates, retries, or replaces one complete subscription snapshot inside a caller-owned transaction and returns the resulting current and previous subscriptions together with the save outcome.
- `get_subscription` returns the current subscription for one exact internal subscription identifier.
- `get_subscriptions_for_user` returns current subscriptions for one requested user.
- `get_alive_subscriptions_for_user` returns alive current subscriptions for one requested user.

`save_subscription` MUST accept a caller-owned transaction, the internal subscription identifier, the causal state transaction identifier, the complete semantic snapshot described by this specification, and the audit actor's kind and canonical identifier.
It MUST return the resulting current subscription, the previous subscription for a business-state replacement, the `created`, `updated`, or `skipped` save outcome described by the snapshot replacement contract, and a zero-argument callback that emits the corresponding business event after commit.
For a `skipped` outcome, the returned callback MUST be a no-op.
It MUST use the supplied transaction for the subscription state, lock, and audit record and MUST NOT emit a business event before commit.

`get_subscription` MUST accept the internal subscription identifier.

`get_subscriptions_for_user` MUST accept one user identifier and an optional collection of normalized statuses, defaulting to no status filter.
It MUST return the subscription list described by the current-state query contract.

`get_alive_subscriptions_for_user` MUST accept one user identifier and return the alive-only subscription list described by the current-state query contract.

Each query operation MUST own the transaction boundary around all persistence work it performs and MUST execute independently of caller-owned transactions.

`save_subscription` MUST be called by the approved `ffun.benefits` subscription-application workflow so the causal benefit transaction, subscription snapshot, and any entitlement effects share one transaction.
After a successful commit, that caller MUST invoke the returned business-event callback; after rollback, it MUST discard the callback without invoking it.
Post-commit callback invocation is best-effort: callback failure MUST NOT invalidate or roll back the committed subscription and audit state, and this module does not guarantee durable callback replay.

`ffun.subscriptions.save_subscription` is explicitly approved to participate in the database transaction owned by `ffun.benefits.apply_subscription_transaction`.
It MAY accept and use that workflow's execute callable for subscription persistence, locking, and audit records.
This exception does not allow benefits to import subscription operations or access subscription tables directly, and it does not approve transaction sharing for unrelated workflows.

## Audit records

### `subscription_changed`

Every creation or business-state replacement MUST append one `subscription_changed` audit record in the same transaction as the state change.

The actor MUST identify the initiating user, administrator, payment service provider, or internal system component.
The subject MUST be the affected user.

The record attributes MUST include:

- `subscription_id`, identifying the internal subscription.
- `state_transaction_id`, identifying the causal benefit transaction applied to the current state.
- `previous_state`, containing the complete previous audit state or `null` for a new subscription.
- `new_state`, containing the complete resulting audit state.

Each audit state MUST be serialized from the complete subscription snapshot by excluding only the Feeds Fun user identifier.
Consequently, each audit state MUST include the benefit identifier, normalized status, provider status, subscription start, current-period start, current-period end, expected renewal, end, and provider update values, as well as any future subscription snapshot fields not explicitly excluded above.

A stale snapshot, idempotent retry, freshness-only update, or failed request MUST NOT append an audit record.

## Business events

### `subscription_changed`

Every successful creation or business-state replacement MUST produce one `subscription_changed` business event for best-effort emission after the state and audit transaction succeeds.

The event MUST use the affected user as the business-event user and include the previous normalized status or `null` separately from the current subscription attributes.
The business event attributes MUST include the internal subscription identifier and state transaction identifier and be serialized from the complete current snapshot by excluding only the Feeds Fun user identifier.
Consequently, they MUST include the benefit identifier, provider update time, resulting normalized status, provider status, subscription start, current-period start, current-period end, expected renewal, and end values, as well as any future subscription snapshot fields not explicitly excluded above.

A stale snapshot, idempotent retry, freshness-only update, failed request, or query MUST NOT emit the event.
Failure while delivering the event after commit MUST NOT change this durable state and does not make an otherwise idempotent retry emit the event again.
