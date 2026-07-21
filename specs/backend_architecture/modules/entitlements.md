# Entitlements module

## Goal of the document

This document defines source-owned entitlement state, materialized effective entitlement intervals, and entitlement change records owned by `ffun.entitlements`.

## Scope

This specification covers the entitlement kind registry, time-bounded source state, effective interval materialization and cleanup, merge behavior, transactions, audit records, and business events.

Purchased subscription lifecycle, payment service provider protocols, product pricing, frontend behavior, and the concrete set of entitlement sources are out of scope.

## Dictionary

- `entitlement kind` - a predefined capability or limit whose registry assigns the policy used to merge values for that kind.
- `source` - a semantic identifier for one system allowed to maintain its own current entitlement state, such as a payment service provider or support tooling.
- `source entitlement` - the latest entitlement state written by one source for one user and entitlement kind.
- `active source entitlement` - a granted source entitlement whose activation time is less than or equal to, and whose expiration time is later than, the time at which effective entitlements are evaluated.
- `effective entitlement interval` - a materialized time interval during which the merged source state grants one entitlement kind to one user with one value.
- `merge policy` - the operation used to combine integer values from multiple granted source entitlements of the same kind.

## Module responsibility

`ffun.entitlements` MUST be a domain-level module that owns entitlement entities, persistence, merging, timeline materialization, and queries. Sources MUST change entitlements through its domain boundary; they MUST NOT write entitlement tables directly or change another source's state.

Callers that check a user's current entitlements MUST read effective entitlements through the module boundary. They SHOULD NOT reproduce merge behavior or derive access directly from the source entitlement table.

## Domain behavior

### Entitlement kinds

`ffun.entitlements.entities` MUST define `EntitlementKindId` as an integer enum with exactly these members and stable values:

- `day_tokens = 1`.
- `month_tokens = 2`.

The module MUST maintain an immutable code-owned collection containing exactly one `EntitlementKind` for every `EntitlementKindId` member. Each entry MUST pair the id with its merge policy. This collection is the entitlement kind registry and source of truth for kind metadata; entitlement kinds MUST NOT be stored in a database registry table or runtime settings.

The registry MUST define these entitlement kinds:

- `day_tokens` with merge policy `max`.
- `month_tokens` with merge policy `max`.

Merge policies MUST be a closed set of named values. The supported policies are:

- `max` - the effective value is the largest candidate value.
- `min` - the effective value is the smallest candidate value.
- `sum` - the effective value is the sum of all candidate values.

The Python representations of entitlement kind ids and merge policies MUST use their corresponding enums.

### Source entitlement state

All sources MUST store their latest state in `en_source_entitlements`, with at most one row per `(user_id, kind_id, source)`. Updating that row replaces the source's previous state. Source ids MUST use a semantic Python type.

Every source entitlement state MUST have finite activation and expiration timestamps, and its activation timestamp MUST be earlier than its expiration timestamp. A state is inactive before its activation timestamp and at or after its expiration timestamp. An already expired state MAY be stored when it is the latest successfully processed change from its source, but it is immediately inactive.

A future-dated grant MUST contribute from `starts_at`. Because each source has one row, storing it immediately replaces and deactivates that source's previous contribution.

A revoked row MUST remain representable as a source's latest state. It removes only that source's contribution; durable history is stored through `ffun.audit`.

Repeated requests whose `granted`, `value`, `starts_at`, and `expires_at` values already match the stored source state MUST be treated as no-ops.

### Effective entitlement timeline materialization

`en_entitlements` MUST store non-overlapping merged grant intervals derived from `en_source_entitlements`. Multiple rows MAY exist for one `(user_id, kind_id)` pair. Absence of a covering interval means the entitlement is not granted.

Intervals are half-open: `starts_at` is inclusive and `expires_at` is exclusive. Each timeline rebuild MUST capture one evaluation time and use it consistently. For one `(user_id, kind_id)` pair, the module MUST build the timeline as follows:

1. Load the granted source rows and order their distinct `starts_at` and `expires_at` boundaries.
2. For each interval between consecutive boundaries whose end is later than the evaluation time, select the source rows active throughout it and skip the interval when none are active.
3. Apply the kind's merge policy to the active values and materialize the result.
4. Coalesce adjacent intervals with the same value.

For source-change domain results and business event payloads, the effective state at an evaluation time is `(true, value)` when a materialized interval covers that time and `(false, null)` otherwise.

### Effective entitlement queries and cleanup

Every effective entitlement query MUST capture one evaluation time and select intervals satisfying `starts_at <= evaluation_time < expires_at`. At most one row can match each user-kind pair. Queries MUST NOT mutate entitlement state when time passes.

The module MUST provide a cleanup method that captures one cleanup time and deletes effective rows with `expires_at <= cleanup_time`. It MUST NOT delete source rows and MAY run opportunistically because expired effective rows do not affect query correctness.

### Change workflow

Every source change MUST update its source state and rebuild the affected timeline in one transaction. Changes for the same `(user_id, kind_id)` pair MUST be serialized.

The workflow MUST:

1. validate that the entitlement kind is present in the entitlement kind registry, a granted state has an integer value, a revoked state has no value, `starts_at` and `expires_at` are finite timestamps, and `starts_at` is earlier than `expires_at`.
2. capture one evaluation time and load the previous effective intervals ending after that time.
3. store the new source state and derive a timeline from all current source rows for the user and kind.
4. replace all effective rows for that user and kind with the derived intervals.
5. determine the new effective state at the captured time and append the required audit record, including the previous and new effective interval lists, through `ffun.audit.domain` with the same transaction execute callable.
6. commit the source state, effective intervals, and audit record atomically.

A failed workflow MUST leave the source state, effective timeline, and audit history unchanged.

## Database schema

The module MUST own exactly two tables, `en_source_entitlements` for source-owned current state and `en_entitlements` for the merged effective timeline. Both tables use the `en_` prefix.

### `en_source_entitlements`

```sql
-- Stores the latest entitlement state supplied by every source.
CREATE TABLE en_source_entitlements (
    source_id TEXT NOT NULL, -- Semantic id of the source that owns this state.
    user_id UUID NOT NULL, -- Semantic id of the user whose source state is stored.
    kind_id SMALLINT NOT NULL, -- Stable integer EntitlementKindId value configured for this source state.
    granted BOOLEAN NOT NULL, -- Whether the source grants the entitlement during this state's activation interval.
    value BIGINT, -- Integer grant value; null only for a revoked state.
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Time at which this source state becomes active.
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Time at or after which this source state is inactive.
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Time at which this source first received a state row for the user and kind.
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Time at which the source state row was last replaced.

    PRIMARY KEY (user_id, kind_id, source_id) -- Keeps only the current state from each source for a user and kind.
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

`en_source_entitlements` remains the source of truth. Replacing source state MUST preserve `created_at` and set `updated_at` to the database's current timestamp. Domain logic MUST ensure effective intervals are finite, satisfy `starts_at < expires_at`, and do not overlap for the same user and kind. `kind_id` MUST NOT have a foreign key because kind ids and their merge policies are defined by the code-owned registry. The effective primary key supports user-kind queries, and the expiration index supports cleanup.

## Domain interface

`ffun.entitlements.domain` MUST provide source changes, interval cleanup, and a batch effective-entitlement listing function. Operation names are not specified.

The batch function MUST accept lists of user ids and entitlement kind ids, use one evaluation time for the whole request, and return `Mapping[UserId, Mapping[EntitlementKindId, EffectiveEntitlementInterval | None]]`. An empty entitlement kind id list MUST select every registered entitlement kind. Every requested user and selected kind MUST be present in the result. A value MUST be the complete effective interval that covers the evaluation time when the entitlement is granted, and `None` otherwise.

## Audit records

### `source_entitlement_changed`

Every non-no-op source change MUST append one `source_entitlement_changed` audit record in the same transaction. Its actor MUST identify the initiating user, administrator, payment service provider, or system component; its subject MUST use kind `user` and the affected user id.

The record attributes MUST include:

- `source` - semantic id of the source that owns the changed row.
- `kind_id` - entitlement kind id.
- `previous_source_state` and `new_source_state` - the complete JSON-mode Pydantic serialization of the corresponding source entitlement entity; the previous state is `null` when no row existed.
- `previous_effective_intervals` and `new_effective_intervals` - lists containing the complete JSON-mode Pydantic serialization of each corresponding effective entitlement interval whose expiration is later than the workflow's evaluation time, ordered by `starts_at`; an empty list means there are no current or future effective intervals.

The audit record MUST be appended even when the effective entitlement is unchanged, because the source-owned state changed. A no-op request MUST NOT append an audit record.

## Business events

The module MUST generate business events only after a successful source change transaction. No-op and rolled-back transactions MUST NOT generate them. Event payloads MUST describe only the resulting state and MUST NOT contain previous or historical values.

### `source_entitlement_changed`

This event MUST be generated whenever a source row changes, even when the effective entitlement does not.

The event MUST use the affected user as the business event user and include:

- `source` - semantic source id.
- `kind_id` - entitlement kind id.
- `granted` - whether the source grants the entitlement during the new state's activation interval.
- `value` - new integer value, or `null` for a revoked state.
- `starts_at` - activation time of the new source state.
- `expires_at` - expiration time of the new source state.

### `entitlement_changed`

This event MUST be generated after every successful non-no-op source change and timeline rebuild, whether or not the effective timeline changed.

The event MUST use the affected user as the business event user and include:

- `kind_id` - entitlement kind id.
- `granted` - whether the entitlement is granted after the timeline rebuild.
- `value` - new effective integer value, or `null` when the effective entitlement was revoked.
- `new_effective_intervals` - the resulting effective intervals represented by their `value`, `starts_at`, and `expires_at` fields.

Every successful non-no-op source change MUST generate both events. Time passage, queries, and cleanup MUST NOT append entitlement audit records or generate business events.
