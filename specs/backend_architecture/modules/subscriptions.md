# Subscriptions module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.subscriptions` backend module.

## Scope

This specification applies to the complete caller-visible contract and observable behavior of locally persisted, externally managed purchased-subscription state owned by `ffun.subscriptions`.

Payment collection, provider APIs and notification protocols, checkout and customer-portal workflows, invoices and payment attempts, product pricing, entitlement derivation, resource accounting, and frontend presentation are out of scope.

## Dictionary

- `subscription provider` - an external system that owns the commercial subscription.
- `provider identifier` - the stable identifier used to select one subscription-provider integration.
- `provider merchant` - the provider-side seller or merchant that receives payments and defines the subscription identifier namespace.
- `subscription identity` - the exact provider identifier, provider merchant, and provider subscription identifier tuple for one subscription.
- `provider customer identifier` - the provider-side customer associated with a subscription.
- `subscription status` - the normalized provider-neutral lifecycle state stored for a subscription.
- `alive subscription` - a subscription whose latest stored status and end time indicate that it has not ended at the evaluation time.
- `provider status` - the open-ended status value supplied by the subscription provider.
- `subscription snapshot` - the complete current caller-supplied state of one subscription at one provider update time.
- `business state` - every subscription snapshot field except the provider update time.
- `audit state` - every subscription snapshot field except identity and ownership fields represented separately by the audit record.
- `business event attributes` - every subscription snapshot field except the Feeds Fun user identifier represented separately by the business event.
- `save outcome` - the high-level business result of saving one subscription snapshot.

## Module responsibility

The module MUST own provider-neutral subscription identities, current subscription snapshots, normalized statuses, provider statuses, lifecycle timestamps, durable state replacement, current-state queries, audit records, and business events.

The subscription provider remains authoritative for commercial subscription state.
The module MUST represent the latest accepted provider state locally and MUST NOT independently infer provider-side state transitions.

Callers MUST read and change locally persisted subscription state through the public module boundary.
They MUST NOT reproduce subscription identity, validation, freshness, or replacement behavior.

The module MUST NOT own payment-provider communication, subscription items, product catalogs or pricing, product-to-subscription mapping, display metadata, payment or invoice state, entitlement grants, resource limits, or access decisions.
Callers MUST resolve product, price, entitlement, and presentation behavior through their owning code or configuration rather than persist it as subscription state.

## Domain behavior

### Subscription identity and ownership

Provider, provider-merchant, provider-subscription, and provider-customer identifiers MUST be non-empty strings.
Provider-supplied identifiers and statuses MUST be normalized by trimming surrounding whitespace.
The module MUST NOT apply any other normalization.

One subscription MUST be identified by the exact tuple of provider identifier, provider merchant, and provider subscription identifier.
Each subscription MUST be associated with exactly one Feeds Fun user and one provider customer identifier.

The subscription identity, user association, and provider customer identifier MUST remain immutable after creation.
Reusing an existing subscription identity with a different immutable value MUST fail.

A user MAY have multiple subscriptions, including multiple subscriptions from the same provider merchant or provider customer.
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

Every subscription snapshot MUST contain timezone-aware subscription-start and provider-update timestamps.

The next renewal and end timestamps MAY be absent.
When present, each MUST be timezone-aware.

The next renewal timestamp MUST describe when the subscription is expected to renew and MUST be absent when no renewal is expected.
The end timestamp MUST describe either the scheduled end of a subscription that has not ended yet or the actual end reported for an ended subscription.
Callers MUST interpret the end timestamp together with the normalized status.

### Snapshot validation and replacement

A subscription snapshot MUST be validated completely before persisted state changes.
Invalid identity, ownership, status, or timestamp data MUST fail without changing stored state.

At most one current snapshot MUST exist for one subscription identity.
Creating a missing identity MUST durably store the complete snapshot and produce the `created` save outcome.

A snapshot whose provider update time is earlier than the stored provider update time MUST be a stale no-op and produce the `skipped` save outcome.
A snapshot with the same provider update time and identical business state MUST be an idempotent no-op and produce the `skipped` save outcome.
A snapshot with the same provider update time and different business state MUST fail as an ambiguous conflict.

A snapshot whose provider update time is later than the stored provider update time and whose business state differs MUST replace the complete mutable business state, advance the stored provider update time, and produce the `updated` save outcome.
When only the provider update time differs, the module MAY advance that time but MUST produce the `skipped` save outcome because the business state did not change.

Replacement of a subscription's status, provider status, lifecycle timestamps, and provider update time MUST be atomic.
Concurrent replacements for the same subscription identity MUST serialize their freshness decisions so older state cannot overwrite newer state.

Failure at any point in a business-state replacement MUST leave the previous snapshot and audit history unchanged.
Business events MUST be emitted only after the new state and required audit record become durable.

### Current-state queries

An identity query MUST return the complete current subscription snapshot for the exact requested identity, or no value when the subscription is unknown.

A user query without a status filter MUST return every current snapshot associated with the requested user, including snapshots whose normalized status is `ended`.
When a status filter is supplied, the query MUST return only snapshots whose normalized status is included in the filter.
An empty status filter MUST produce an empty snapshot list.

An alive-subscription query MUST follow the same result shape but include only snapshots counted as alive at the query's evaluation time.

Subscriptions for one user MUST be ordered by subscription start descending, then by provider identifier, provider merchant, and provider subscription identifier ascending.
Queries MUST be read-only and MUST NOT produce audit records or business events.

## Public interface

The public interface MUST provide these operations:

- `save_subscription` creates, retries, or replaces one complete subscription snapshot.
- `get_subscription` returns the current snapshot for one exact subscription identity.
- `get_subscriptions_for_user` returns current snapshots for one requested user.
- `get_alive_subscriptions_for_user` returns alive current snapshots for one requested user.

`save_subscription` MUST accept the complete semantic snapshot fields described by this specification and the audit actor's kind and canonical identifier.
It MUST return the `created`, `updated`, or `skipped` save outcome described by the snapshot replacement contract.

`get_subscription` MUST accept the provider identifier, provider merchant, and provider subscription identifiers that form the subscription identity.

`get_subscriptions_for_user` MUST accept one user identifier and an optional collection of normalized statuses, defaulting to no status filter.
It MUST return the subscription list described by the current-state query contract.

`get_alive_subscriptions_for_user` MUST accept one user identifier and return the alive-only subscription list described by the current-state query contract.

The public interface MUST own transaction boundaries for subscription changes.
Each query operation MUST own the transaction boundary around all persistence work it performs and MUST execute independently of caller-owned transactions.

## Audit records

### `subscription_changed`

Every creation or business-state replacement MUST append one `subscription_changed` audit record in the same transaction as the state change.

The actor MUST identify the initiating user, administrator, payment service provider, or internal system component.
The subject MUST be the affected user.

The record attributes MUST include:

- `provider_id`, identifying the subscription provider integration.
- `provider_merchant_id`, identifying the provider-side seller or merchant.
- `provider_subscription_id`, identifying the subscription within that namespace.
- `provider_customer_id`, identifying the associated provider customer.
- `previous_state`, containing the complete previous audit state or `null` for a new subscription.
- `new_state`, containing the complete resulting audit state.

Each audit state MUST be serialized from the complete subscription snapshot by excluding only the provider identifier, provider merchant identifier, provider subscription identifier, Feeds Fun user identifier, and provider customer identifier.
Consequently, each audit state MUST include the normalized status, provider status, subscription start, next renewal, end, and provider update values, as well as any future subscription snapshot fields not explicitly excluded above.

A stale snapshot, idempotent retry, freshness-only update, or failed request MUST NOT append an audit record.

## Business events

### `subscription_changed`

Every successful creation or business-state replacement MUST emit one `subscription_changed` business event after the state and audit transaction succeeds.

The event MUST use the affected user as the business-event user and include the previous normalized status or `null` separately from the current subscription attributes.
The business event attributes MUST be serialized from the complete current subscription snapshot by excluding only the Feeds Fun user identifier.
Consequently, they MUST include `provider_id`, `provider_merchant_id`, `provider_subscription_id`, `provider_customer_id`, `provider_updated_at`, the resulting normalized status, the provider status, subscription start, next renewal, and end values, as well as any future subscription snapshot fields not explicitly excluded above.

A stale snapshot, idempotent retry, freshness-only update, failed request, or query MUST NOT emit the event.
