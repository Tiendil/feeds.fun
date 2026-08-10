# Subscriptions module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.subscriptions` backend module.

## Scope

This specification applies to the complete caller-visible contract and observable behavior of locally persisted, externally managed purchased-subscription state owned by `ffun.subscriptions`.

Payment collection, provider APIs and notification protocols, checkout and customer-portal workflows, invoices and payment attempts, product pricing, entitlement derivation, resource accounting, and frontend presentation are out of scope.

## Dictionary

- `subscription provider` - an external system that owns the commercial subscription.
- `provider account` - one provider-side account and environment whose identifiers form an independent namespace.
- `subscription identity` - the exact provider, provider account, and provider subscription identifier tuple for one subscription.
- `provider customer identifier` - the provider-side customer associated with a subscription.
- `subscription status` - the normalized provider-neutral lifecycle state stored for a subscription.
- `provider status` - the exact open-ended status value supplied by the subscription provider.
- `subscription item` - one provider-identified product and price selection included in a subscription.
- `subscription snapshot` - the complete current caller-supplied state of one subscription at one provider update time.
- `business state` - every subscription snapshot field except the provider update time.

## Module responsibility

The module MUST own provider-neutral subscription identities, current subscription snapshots, normalized statuses, exact provider statuses, subscription items, lifecycle timestamps, durable state replacement, current-state queries, audit records, and business events.

The subscription provider remains authoritative for commercial subscription state.
The module MUST represent the latest accepted provider state locally and MUST NOT independently infer provider-side state transitions.

Callers MUST read and change locally persisted subscription state through the public module boundary.
They MUST NOT reproduce subscription identity, validation, freshness, or replacement behavior.

The module MUST NOT own payment-provider communication, product catalogs or pricing, payment or invoice state, entitlement grants, resource limits, or access decisions.

## Domain behavior

### Subscription identity and ownership

Provider, provider-account, provider-subscription, and provider-customer identifiers MUST be non-empty strings.
Provider and provider-account identifiers MUST preserve the caller-supplied external namespace exactly.

One subscription MUST be identified by the exact tuple of provider, provider account, and provider subscription identifier.
Each subscription MUST be associated with exactly one Feeds Fun user and one provider customer identifier.

The subscription identity, user association, and provider customer identifier MUST remain immutable after creation.
Reusing an existing subscription identity with a different immutable value MUST fail.

A user MAY have multiple subscriptions, including multiple subscriptions from the same provider account or provider customer.
Different subscription identities MUST be stored and queried independently.

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

Every subscription MUST contain both one normalized status and the exact non-empty provider status from which the caller obtained the normalized state.
Provider statuses MUST remain open-ended external strings and MUST NOT be validated against a provider-specific closed set by this module.

The module MUST NOT assign entitlement, access, or resource-limit meaning to any subscription status.
Callers that make access decisions MUST use the owning domain boundaries for those decisions rather than infer access from subscription state.

Status transitions MUST be accepted from any supported status to any supported status when supplied by a newer valid snapshot.
The module MUST NOT reject a newer snapshot merely because its transition would be unusual for a particular provider.

Time passage alone MUST NOT change a stored subscription status.
Queries MUST NOT mutate subscription state when a trial, billing period, or scheduled end time passes.

### Subscription items

Every subscription snapshot MUST contain at least one subscription item.

Each item MUST contain a non-empty provider item identifier, product identifier, and price identifier, together with a positive integer quantity.
Provider item identifiers MUST be unique within one subscription.

Items MUST be treated as an identity-keyed collection rather than a positionally meaningful sequence.
A newer snapshot's item collection MUST completely replace the previous collection.
An item absent from the newer collection MUST no longer belong to the current subscription state.

Product and price identifiers MUST remain external references.
The module MUST NOT derive prices, display names, entitlements, or other product behavior from them.

### Lifecycle timestamps

Every subscription snapshot MUST contain timezone-aware subscription-start and provider-update timestamps.

Current billing-period start and end timestamps MUST either both be present or both be absent.
When present, both MUST be timezone-aware and the period start MUST be earlier than the period end.

Trial end, scheduled end, and actual end timestamps MAY be absent.
When present, each MUST be timezone-aware.

The scheduled end MUST describe a future or planned end without changing the current normalized status.
The actual end MUST describe when the provider reports that the subscription ended.
The two values MUST remain distinct because an active subscription MAY have a scheduled end while continuing through its current period.

### Snapshot validation and replacement

A subscription snapshot MUST be validated completely before persisted state changes.
Invalid identity, status, item, or timestamp data MUST fail without changing stored state.

At most one current snapshot MUST exist for one subscription identity.
Creating a missing identity MUST durably store the complete snapshot.

A snapshot whose provider update time is earlier than the stored provider update time MUST be a stale no-op and return the stored state.
A snapshot with the same provider update time and identical business state MUST be an idempotent no-op.
A snapshot with the same provider update time and different business state MUST fail as an ambiguous conflict.

A snapshot whose provider update time is later than the stored provider update time MUST replace the complete mutable business state and advance the stored provider update time.
When only the provider update time differs, the module MAY advance that time without treating the replacement as a business-state change.

Replacement of a subscription's status, provider status, items, lifecycle timestamps, and provider update time MUST be atomic.
Concurrent replacements for the same subscription identity MUST serialize their freshness decisions so older state cannot overwrite newer state.

Failure at any point in a business-state replacement MUST leave the previous snapshot and audit history unchanged.
Business events MUST be emitted only after the new state and required audit record become durable.

### Current-state queries

An identity query MUST return the complete current subscription snapshot for the exact requested identity, or no value when the subscription is unknown.

A batch user query MUST return one entry for every distinct requested user.
Each entry MUST contain every current snapshot associated with that user, including snapshots whose normalized status is `ended`.

Repeated user identifiers MUST behave as one request for the duplicated value.
An empty user collection MUST return an empty result.

Subscriptions for one user MUST be ordered by subscription start descending, then by provider, provider account, and provider subscription identifier ascending.
Subscription items MUST be ordered by provider item identifier ascending.

Queries MUST be read-only and MUST NOT produce audit records or business events.

## Public interface

The public interface MUST provide these operations:

- `save_subscription` creates, retries, or replaces one complete subscription snapshot.
- `get_subscription` returns the current snapshot for one exact subscription identity.
- `get_subscriptions` returns current snapshots for requested users.

`save_subscription` MUST accept the complete semantic snapshot fields described by this specification and the audit actor's kind and canonical identifier.
It MUST return the resulting stored snapshot and whether its business state changed.

`get_subscription` MUST accept the provider, provider account, and provider subscription identifiers that form the subscription identity.

`get_subscriptions` MUST accept a collection of user identifiers and return the complete per-user result described by the current-state query contract.

The public interface MUST own transaction boundaries for subscription changes.
Query operations MUST execute independently of caller-owned transactions.

## Audit records

### `subscription_changed`

Every creation or business-state replacement MUST append one `subscription_changed` audit record in the same transaction as the state change.

The actor MUST identify the initiating user, administrator, payment service provider, or internal system component.
The subject MUST be the affected user.

The record attributes MUST include:

- `provider`, identifying the subscription provider.
- `provider_account_id`, identifying the provider account namespace.
- `provider_subscription_id`, identifying the subscription within that namespace.
- `provider_customer_id`, identifying the associated provider customer.
- `provider_updated_at`, identifying the provider update time of the accepted snapshot.
- `previous_state`, containing the complete previous business state or `null` for a new subscription.
- `new_state`, containing the complete resulting business state.

Each state snapshot MUST include the normalized status, provider status, subscription items, subscription start, billing-period start and end, trial end, scheduled end, and actual end values.

A stale snapshot, idempotent retry, freshness-only update, or failed request MUST NOT append an audit record.

## Business events

### `subscription_changed`

Every successful creation or business-state replacement MUST emit one `subscription_changed` business event after the state and audit transaction succeeds.

The event MUST use the affected user as the business-event user and include `provider`, `provider_account_id`, `provider_subscription_id`, `provider_customer_id`, `provider_updated_at`, the previous normalized status or `null`, the resulting normalized status, the exact provider status, subscription items, and lifecycle timestamps.

A stale snapshot, idempotent retry, freshness-only update, failed request, or query MUST NOT emit the event.
