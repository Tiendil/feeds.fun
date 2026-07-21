# Entitlements module

## Goal of the document

This document defines source-owned entitlement state, materialized effective entitlement intervals, and entitlement change records owned by `ffun.entitlements`.

## Scope

This specification covers the entitlement kind registry, time-bounded source state, effective interval materialization and cleanup, merge behavior, transactions, audit records, and business events.

Purchased subscription lifecycle, payment service provider protocols, product pricing, frontend behavior, and the concrete set of entitlement sources are out of scope.

## Dictionary

- `entitlement kind` - a predefined capability or limit whose registry assigns its merge policy and whether it is lifetime.
- `source` - a semantic identifier for one system allowed to maintain its own entitlement state, such as a payment service provider or support tooling.
- `transaction id` - a stable source-supplied identifier for one entitlement grant to one user and entitlement kind.
- `source entitlement` - one durable entitlement grant recorded by one source and transaction id for one user and entitlement kind.
- `active source entitlement` - a source entitlement whose activation time is less than or equal to, and whose expiration and optional revocation times are later than, the time at which effective entitlements are evaluated.
- `effective entitlement interval` - a materialized time interval during which the merged source state grants one entitlement kind to one user with one value.
- `merge policy` - the operation used to combine integer values from multiple active source entitlements of the same kind.

## Module responsibility

`ffun.entitlements` MUST be a domain-level module that owns entitlement entities, persistence, merging, timeline materialization, and queries. Sources MUST change entitlements through its domain boundary; they MUST NOT write entitlement tables directly or change another source's state.

Callers that check a user's current entitlements MUST read effective entitlements through the module boundary. They SHOULD NOT reproduce merge behavior or derive access directly from the source entitlement table.

## Domain behavior

### Entitlement kinds

`ffun.entitlements.entities` MUST define `EntitlementKindId` as an integer enum. Every member and its stable value MUST be defined by this specification and MUST NOT be changed or reused.

The module MUST maintain an immutable code-owned collection containing exactly one `EntitlementKind` for every `EntitlementKindId` member. Each entry MUST pair the id with its merge policy and `is_lifetime` boolean. This collection is the entitlement kind registry and source of truth for kind metadata; entitlement kinds MUST NOT be stored in a database registry table or runtime settings.

The registry MUST include these entitlement-kind mappings:

- `day_tokens` with stable value `1`, merge policy `max`, and `is_lifetime` set to `false`.
- `month_tokens` with stable value `2`, merge policy `max`, and `is_lifetime` set to `false`.
- `lifetime_tokens` with stable value `3`, merge policy `sum`, and `is_lifetime` set to `true`.

Merge policies MUST be a closed set of named values. The supported policies are:

- `max` - the effective value is the largest candidate value.
- `min` - the effective value is the smallest candidate value.
- `sum` - the effective value is the sum of all candidate values.

The Python representations of entitlement kind ids and merge policies MUST use their corresponding enums.

`is_lifetime` MUST distinguish only expiration validation. Non-lifetime grants MUST have source-supplied finite expiration timestamps. Lifetime grants MUST have the module-owned stable future expiration constant rather than a creation-relative expiration.

### Source entitlement state

All sources MUST store their grants in `en_source_entitlements`, with at most one row per `(user_id, kind_id, source, transaction_id)`. Source ids and transaction ids MUST use semantic Python types.

Every source entitlement MUST have an integer value and finite activation and expiration timestamps, and its activation timestamp MUST be earlier than its expiration timestamp. It is inactive before its activation timestamp, at or after its expiration timestamp, and at or after a non-null `revoked_at`. An already expired entitlement MAY be stored, but it is immediately inactive.

After creation, only `revoked_at` and `updated_at` MAY change. Correcting another field requires revoking the entitlement and creating a new one with a new transaction id. A future-dated grant MUST contribute from `starts_at` without replacing any earlier grant.

Creating an entitlement whose identity and immutable fields match an existing row MUST be a no-op. Reusing the identity with different immutable fields MUST fail. Revocation MUST set a null `revoked_at` to one captured current timestamp without changing other meaningful fields. Revoking an already revoked entitlement MUST be a no-op and preserve its original `revoked_at`; revoking a missing entitlement MUST fail.

`lifetime_tokens` represents a non-resetting token allowance. Its effective value is the sum of active grants; token consumption is outside this module's responsibility.

### Effective entitlement timeline materialization

`en_entitlements` MUST store non-overlapping merged grant intervals derived from `en_source_entitlements`. Multiple rows MAY exist for one `(user_id, kind_id)` pair. Absence of a covering interval means the entitlement is not granted.

Intervals are half-open: `starts_at` is inclusive and `expires_at` is exclusive. Each timeline rebuild MUST capture one evaluation time and use it consistently. For one `(user_id, kind_id)` pair, the module MUST build the timeline as follows:

1. Load the source rows and order their distinct `starts_at`, `expires_at`, and non-null `revoked_at` boundaries.
2. For each interval between consecutive boundaries whose end is later than the evaluation time, select the source rows active throughout it and skip the interval when none are active.
3. Apply the kind's merge policy to the active values and materialize the result.
4. Coalesce adjacent intervals with the same value.

For source-change domain results and business event payloads, the effective state at an evaluation time is `(true, value)` when a materialized interval covers that time and `(false, null)` otherwise.

### Effective entitlement queries and cleanup

Every effective entitlement query MUST capture one evaluation time and select intervals satisfying `starts_at <= evaluation_time < expires_at`. At most one row can match each user-kind pair. Queries MUST NOT mutate entitlement state when time passes.

The module MUST provide a cleanup method that captures one cleanup time and deletes effective rows with `expires_at <= cleanup_time`. It MUST NOT delete source rows and MAY run opportunistically because expired effective rows do not affect query correctness.

### Change workflow

Every non-no-op source grant or revocation MUST change its source state and rebuild the affected timeline in one transaction. Changes for the same `(user_id, kind_id)` pair MUST be serialized.

The workflow MUST:

1. validate the source and transaction ids, entitlement kind, integer value and finite interval for grants, and expiration against the kind's `is_lifetime` metadata.
2. capture one evaluation time, also using it as `revoked_at` for revocation, and load the previous effective intervals ending after that time.
3. create or revoke the identified source entitlement according to the idempotency and immutability rules above.
4. derive a timeline from all source rows for the user and kind.
5. replace all effective rows for that user and kind with the derived intervals.
6. determine the new effective state at the captured time and append the required audit record, including the previous and new effective interval lists, through `ffun.audit.domain` with the same transaction execute callable.
7. commit the source state, effective intervals, and audit record atomically.

A failed workflow MUST leave the source state, effective timeline, and audit history unchanged.

## Database schema

The module MUST own `en_source_entitlements` for source-owned state and `en_entitlements` for the merged effective timeline. Both tables use the `en_` prefix.

### `en_source_entitlements`

```sql
-- Stores entitlement grants supplied by sources.
CREATE TABLE en_source_entitlements (
    source_id TEXT NOT NULL, -- Semantic id of the source that owns this state.
    transaction_id TEXT NOT NULL, -- Stable source-supplied id of this grant.
    user_id UUID NOT NULL, -- Semantic id of the user whose source state is stored.
    kind_id SMALLINT NOT NULL, -- Stable integer EntitlementKindId value configured for this source state.
    value BIGINT NOT NULL, -- Immutable integer grant value.
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Time at which this source state becomes active.
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Time at or after which this source state is inactive.
    revoked_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Time at or after which this grant is revoked; null until revocation.
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Time at which this source first received this grant.
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Time at which the source state row last changed.

    PRIMARY KEY (user_id, kind_id, source_id, transaction_id) -- Identifies one source grant transaction.
);
```

### `en_entitlements`

```sql
-- Materialized effective entitlement intervals derived from the source entitlement table.
CREATE TABLE en_entitlements (
    user_id UUID NOT NULL, -- Semantic id of the user who has the effective entitlement.
    kind_id SMALLINT NOT NULL, -- Stable integer EntitlementKindId value configured for this interval.
    value BIGINT NOT NULL, -- Value produced by the kind's merge policy for this interval.
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Inclusive start of the effective granted interval.
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Exclusive end of the effective granted interval.
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Time at which this materialized interval row was created.
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Time at which this materialized interval row was last changed.

    PRIMARY KEY (user_id, kind_id, starts_at) -- Identifies each interval in the effective timeline.
);

CREATE INDEX en_entitlements_expires_at_idx ON en_entitlements (expires_at); -- Supports removal of expired intervals.
```

`en_source_entitlements` remains the source of truth and requires no secondary index. After insertion, only a null `revoked_at` may change to a timestamp; the same statement MUST set `updated_at` to the database's current timestamp. Source rows MUST NOT be deleted by effective-interval cleanup. Domain logic MUST ensure effective intervals are finite, satisfy `starts_at < expires_at`, and do not overlap for the same user and kind. `kind_id` MUST NOT have a foreign key because kind ids and their merge policies are defined by the code-owned registry. The effective primary key supports user-kind queries, and the expiration index supports cleanup.

## Domain interface

`ffun.entitlements.domain` MUST provide source grants, revocations, interval cleanup, and a batch effective-entitlement listing function. Operation names are not specified.

Grant and revocation calls MUST identify the source entitlement by source, transaction id, user id, and entitlement kind id and accept the audit actor. Grant calls MUST also accept its value and interval. Revocation calls MUST capture the revocation time internally and MUST NOT accept replacement grant fields.

The batch function MUST accept lists of user ids and entitlement kind ids, use one evaluation time for the whole request, and return `Mapping[UserId, Mapping[EntitlementKindId, EffectiveEntitlementInterval | None]]`. An empty entitlement kind id list MUST select every registered entitlement kind. Every requested user and selected kind MUST be present in the result. A value MUST be the complete effective interval that covers the evaluation time when the entitlement is granted, and `None` otherwise.

## Audit records

### `source_entitlement_changed`

Every non-no-op source change MUST append one `source_entitlement_changed` audit record in the same transaction. Its actor MUST identify the initiating user, administrator, payment service provider, or system component; its subject MUST use kind `user` and the affected user id.

The record attributes MUST include:

- `source` - semantic id of the source that owns the changed row.
- `transaction_id` - stable source-supplied id of the changed transaction.
- `kind_id` - entitlement kind id.
- `previous_source_state` and `new_source_state` - the complete JSON-mode Pydantic serialization of the corresponding source entitlement entity; the previous state is `null` when the grant is created, and revocation changes only `revoked_at`.
- `previous_effective_intervals` and `new_effective_intervals` - lists containing the complete JSON-mode Pydantic serialization of each corresponding effective entitlement interval whose expiration is later than the workflow's evaluation time, ordered by `starts_at`; an empty list means there are no current or future effective intervals.

The audit record MUST be appended even when the effective entitlement is unchanged, because the source-owned state changed. A no-op request MUST NOT append an audit record.

## Business events

The module MUST generate business events only after a successful source change transaction. No-op and rolled-back transactions MUST NOT generate them. Event payloads MUST describe only the resulting state and MUST NOT contain previous or historical values.

### `source_entitlement_changed`

This event MUST be generated whenever a source row changes, even when the effective entitlement does not.

The event MUST use the affected user as the business event user and include:

- `source` - semantic source id.
- `transaction_id` - stable source-supplied transaction id.
- `kind_id` - entitlement kind id.
- `granted` - whether the source entitlement remains unrevoked.
- `value` - immutable integer value.
- `starts_at` - activation time of the source entitlement.
- `expires_at` - expiration time of the source entitlement.
- `revoked_at` - revocation time, or `null` when not revoked.

### `entitlement_changed`

This event MUST be generated after every successful non-no-op source change and timeline rebuild, whether or not the effective timeline changed.

The event MUST use the affected user as the business event user and include:

- `kind_id` - entitlement kind id.
- `granted` - whether the entitlement is granted after the timeline rebuild.
- `value` - new effective integer value, or `null` when the effective entitlement was revoked.
- `new_effective_intervals` - the resulting effective intervals represented by their `value`, `starts_at`, and `expires_at` fields.

Every successful non-no-op source change MUST generate both events. Time passage, queries, and cleanup MUST NOT append entitlement audit records or generate business events.
