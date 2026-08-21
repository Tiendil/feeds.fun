# One-time purchases module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.one_time_purchases` backend module.

## Scope

This specification applies to provider-independent current-state projections and provider-to-local identity references for one-time purchases owned by `ffun.one_time_purchases`.

Payment collection, provider APIs and notification protocols, provider objects other than purchase identities, checkout workflows, invoices and payment attempts, product catalogs and pricing, benefit-package configuration and parameters, benefit-transaction history and intervals, entitlement derivation, resource accounting, and frontend presentation are out of scope.

## Dictionary

- `one-time purchase identifier` - the internally generated UUID that identifies one purchase projection.
- `provider purchase identity` - the provider identifier, provider account identifier, and provider purchase identifier tuple that identifies one external purchase.
- `provider purchase reference` - the persistent mapping from one provider purchase identity to one internal one-time purchase identifier.
- `state transaction identifier` - the internal benefit transaction UUID whose application most recently changed the persisted purchase projection.
- `purchase status` - the normalized provider-neutral lifecycle state stored for a purchase.
- `provider status` - the open-ended status value supplied by the external purchase authority.
- `purchase snapshot` - the complete provider-independent caller-supplied state of one purchase at one provider update time.
- `benefit identifier` - the stable local identifier of the configured benefit package associated with a purchase.
- `business state` - every purchase snapshot field except the provider update time.
- `audit state` - every purchase snapshot field except the Feeds Fun user identifier represented separately by the audit record.
- `business event attributes` - the one-time purchase identifier, state transaction identifier, and every purchase snapshot field except the Feeds Fun user identifier represented separately by the business event.
- `save outcome` - the high-level result of comparing and saving one purchase snapshot: `created`, `updated`, `refreshed`, `same`, or `stale`.

## Module responsibility

The module MUST own internal one-time purchase identifiers, provider-purchase references, current purchase snapshots, their causal state-transaction references, benefit identifiers, normalized statuses and their benefit-granting semantics, provider statuses, purchase timestamps, durable state replacement, current-state queries, audit records, and business events.

The external purchase provider remains authoritative for commercial purchase state.
The module MUST represent the latest accepted state locally and MUST NOT independently infer provider-side state transitions.

Callers MUST read and change locally persisted purchase state through the public module boundary.
They MUST NOT reproduce validation, freshness, ownership, or replacement behavior.

The module MUST NOT own payment-provider communication, provider objects beyond the provider purchase identity tuple, product catalogs or pricing, provider-product-to-benefit resolution, benefit-package configuration, benefit parameters, benefit-transaction history or applicable intervals, payment or invoice state, application of entitlement grants, resource limits, or access decisions.
The module MUST NOT persist benefit titles, descriptions, parameters, or entitlement guarantees.
Callers MUST resolve benefit details and apply guarantees through the benefits domain boundary.

## Domain behavior

### Purchase identity, causality, and ownership

Every one-time purchase MUST have one internally generated UUID represented across module boundaries by a semantically specific identifier type.
The identifier MUST remain stable for the lifetime of the purchase projection and MUST NOT encode a provider identity.

Every persisted purchase MUST reference the internal benefit transaction that created or most recently changed its stored snapshot.

Each purchase MUST be associated with exactly one Feeds Fun user.
The user association MUST remain immutable after creation.
Reusing an existing one-time purchase identifier with a different user MUST fail.

The benefit identifier MUST remain immutable after creation.
Reusing an existing one-time purchase identifier with a different benefit identifier MUST fail.
A user MAY have multiple purchases, and different internal one-time purchase identifiers MUST be stored and queried independently.

### Provider purchase references

Every provider purchase identity component MUST be non-empty.
One provider purchase identity MUST map to at most one internal one-time purchase identifier.
One internal one-time purchase identifier MUST map from at most one provider purchase identity.
Recreating the same mapping MUST be a no-op.
Attempting to map the same provider purchase identity to another internal one-time purchase identifier MUST fail without changing the stored reference.
Attempting to map another provider purchase identity to the same internal one-time purchase identifier MUST fail without changing the stored reference.

Provider purchase references MUST be immutable after creation.
They MUST record their creation time and MAY omit an update time because normal workflows never change them.

Provider adapters and higher-level workflows MUST use the one-time-purchases public domain boundary to resolve and persist provider purchase references.
They MUST NOT maintain provider-specific purchase-identity tables or reproduce mapping behavior.

### Purchase statuses

Normalized purchase statuses MUST form a closed set of stable identifiers.
The supported statuses MUST be:

- `pending`, stable value `1`, meaning the purchase has been initiated but has not completed.
- `completed`, stable value `2`, meaning the provider reports the purchase successfully completed.
- `refunded`, stable value `3`, meaning the provider reports the purchase fully refunded.
- `reversed`, stable value `4`, meaning the provider reports the completed payment reversed.
- `disputed`, stable value `5`, meaning the provider reports the purchase disputed or otherwise contested.

Assigned status identifiers MUST NOT be changed or reused.

Every purchase MUST contain both one normalized status and the non-empty provider status from which the caller obtained the normalized state.
Provider statuses MUST remain open-ended external strings and MUST NOT be validated against a provider-specific closed set by this module.

Each normalized purchase status MUST expose whether it grants the purchase's configured benefits.
Only the `completed` status MUST grant benefits.
The `pending`, `refunded`, `reversed`, and `disputed` statuses MUST NOT grant benefits.

The module MUST NOT translate this status semantic into a benefit transaction action, apply entitlement grants, make access decisions, or own resource-limit policy.
The benefits workflow MUST use this status semantic when deriving its entitlement action.
All other callers that make access decisions MUST use the owning domain boundaries rather than infer access directly from purchase state.

Status transitions MUST be accepted from any supported status to any supported status when supplied by a newer valid snapshot.
The module MUST NOT reject a newer snapshot merely because its transition would be unusual for a particular provider.

Time passage alone MUST NOT change a stored purchase status.
Queries MUST NOT mutate purchase state.

### Purchase timestamps

Every purchase snapshot MUST contain timezone-aware purchase and provider-update timestamps.
The purchase timestamp MUST identify when the provider reports that the purchase originated.
The provider-update timestamp MUST identify the freshness of the complete snapshot.

### Benefit references

A purchase snapshot MUST contain the local benefit identifier resolved from trusted provider product metadata.

The one-time-purchases module MUST store and return that reference without independently inferring a benefit.
It MUST NOT persist provider product or other provider object identifiers; the causal benefit transaction owns that provenance.
It MUST NOT copy benefit display details, benefit parameters, applicable entitlement intervals, or entitlement guarantees into purchase persistence, query a payment provider for benefit details, or directly change entitlement state.

### Snapshot validation and replacement

A purchase snapshot MUST be validated completely before persisted state changes.
Invalid ownership, status, provider status, benefit identifier, or timestamp data MUST fail without changing stored state.

At most one current snapshot MUST exist for one internal one-time purchase identifier.
Creating a missing identifier MUST durably store the complete snapshot and supplied state transaction identifier and produce the `created` save outcome.

A snapshot whose provider update time is earlier than the stored provider update time MUST be a no-op and produce the `stale` save outcome.
A snapshot with the same provider update time and identical business state MUST be an idempotent no-op and produce the `same` save outcome.
A snapshot with the same provider update time and different business state MUST fail as an ambiguous conflict.

A snapshot whose provider update time is later than the stored provider update time and whose business state differs MUST replace the complete mutable business state, advance the stored provider update time, record the supplied state transaction identifier, and produce the `updated` save outcome.
When only the provider update time differs, the module MUST advance that time and the state transaction identifier and produce the `refreshed` save outcome because the stored freshness and causality changed while the business state did not.
A `same` or `stale` no-op MUST preserve the stored state transaction identifier.

Replacement of a purchase's state transaction identifier, status, provider status, purchase timestamp, and provider update time MUST be atomic.
Concurrent replacements for the same internal one-time purchase identifier MUST serialize their freshness decisions so older state cannot overwrite newer state.

Failure at any point in a business-state replacement MUST leave the previous snapshot and audit history unchanged.
Business events MUST be emitted only after the new state and required audit record become durable.

### Current-state queries

An identity query MUST return the complete current purchase for the exact requested internal one-time purchase identifier, or no value when it is unknown.

A user query without a status filter MUST return every current purchase associated with the requested user.
When a status filter is supplied, the query MUST return only purchases whose normalized status is included in the filter.
An empty status filter MUST produce an empty purchase list.

Purchases for one user MUST be ordered by purchase time descending, then by internal one-time purchase identifier ascending.
Queries MUST be read-only and MUST NOT produce audit records or business events.

## Public interface

The public interface MUST provide these operations:

- `new_purchase_id` generates one internal one-time purchase identifier.
- `load_provider_purchase_reference` returns the internal one-time purchase identifier mapped from one exact provider purchase identity, or no value when it is unknown.
- `insert_provider_purchase_reference` creates or retries one exact provider-to-internal purchase mapping inside a caller-owned transaction.
- `save_purchase` creates, retries, or replaces one complete purchase snapshot inside a caller-owned transaction and returns the resulting current and previous purchases together with the save outcome.
- `get_purchase` returns the current purchase for one exact internal one-time purchase identifier.
- `get_purchases_for_user` returns current purchases for one requested user.

`save_purchase` MUST accept a caller-owned transaction, the internal one-time purchase identifier, the causal state transaction identifier, the complete semantic snapshot described by this specification, and the audit actor's kind and canonical identifier.
It MUST return the resulting current purchase, the previous purchase for a business-state replacement, the `created`, `updated`, `refreshed`, `same`, or `stale` save outcome described by the snapshot replacement contract, and a zero-argument callback that emits the corresponding business event after commit.
For a `refreshed`, `same`, or `stale` outcome, the returned callback MUST be a no-op.
The resulting purchase state and required audit record MUST participate in the supplied transaction, and the operation MUST NOT emit a business event before commit.

`load_provider_purchase_reference` MUST accept a caller-owned transaction and one complete provider purchase identity.
It MUST return the mapped internal one-time purchase identifier or no value without changing state.

`insert_provider_purchase_reference` MUST accept a caller-owned transaction, one complete provider purchase identity, and one internal one-time purchase identifier.
It MUST create a missing mapping, treat the same existing mapping as a no-op, and fail when either the provider purchase identity or internal one-time purchase identifier already participates in another mapping.

`get_purchase` MUST accept the internal one-time purchase identifier.

`get_purchases_for_user` MUST accept one user identifier and an optional collection of normalized statuses, defaulting to no status filter.
It MUST return the purchase list described by the current-state query contract.

Each current-state or provider-reference query operation that does not explicitly accept a caller-owned transaction MUST own the transaction boundary around all persistence work it performs and MUST execute independently of caller-owned transactions.

`save_purchase` MUST be called by the approved `ffun.benefits` one-time-purchase-application workflow so the causal benefit transaction, purchase snapshot, and any entitlement effects share one transaction.
After a successful commit, that caller MUST invoke the returned business-event callback; after rollback, it MUST discard the callback without invoking it.
Post-commit callback invocation is best-effort: callback failure MUST NOT invalidate or roll back the committed purchase and audit state, and this module does not guarantee durable callback replay.

`ffun.one_time_purchases.load_provider_purchase_reference`, `ffun.one_time_purchases.insert_provider_purchase_reference`, and `ffun.one_time_purchases.save_purchase` are explicitly approved to participate in the database transaction owned by `ffun.benefits.apply_one_time_purchase_transaction`.
Their provider-reference, purchase-state, and required audit effects MAY participate in that workflow's transaction.
This exception does not allow benefits to import one-time-purchase operations or access one-time-purchase tables directly, and it does not approve transaction sharing for unrelated workflows.

## Audit records

### `one_time_purchase_changed`

Every creation or business-state replacement MUST append one `one_time_purchase_changed` audit record in the same transaction as the state change.

The actor MUST identify the initiating user, administrator, payment service provider, or internal system component.
The subject MUST be the affected user.

The record attributes MUST include:

- `one_time_purchase_id`, identifying the internal one-time purchase.
- `state_transaction_id`, identifying the causal benefit transaction applied to the current state.
- `previous_state`, containing the complete previous audit state or `null` for a new purchase.
- `new_state`, containing the complete resulting audit state.

Each audit state MUST be serialized from the complete purchase snapshot by excluding only the Feeds Fun user identifier.
Consequently, each audit state MUST include the benefit identifier, normalized status, provider status, purchase time, and provider update values, as well as any future purchase snapshot fields not explicitly excluded above.

A `stale`, `same`, or `refreshed` save, provider-reference change, or failed request MUST NOT append an audit record.

## Business events

### `one_time_purchase_changed`

Every successful creation or business-state replacement MUST produce one `one_time_purchase_changed` business event for best-effort emission after the state and audit transaction succeeds.

The event MUST use the affected user as the business-event user and include the previous normalized status or `null` separately from the current purchase attributes.
The business event attributes MUST include the internal one-time purchase identifier and state transaction identifier and be serialized from the complete current snapshot by excluding only the Feeds Fun user identifier.
Consequently, they MUST include the benefit identifier, provider update time, resulting normalized status, provider status, and purchase time, as well as any future purchase snapshot fields not explicitly excluded above.

A `stale`, `same`, or `refreshed` save, provider-reference change, failed request, or query MUST NOT emit the event.
Failure while delivering the event after commit MUST NOT change this durable state and does not make an otherwise idempotent retry emit the event again.
