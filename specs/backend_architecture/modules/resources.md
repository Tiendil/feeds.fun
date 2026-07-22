# Resources module

## Goal of the document

This document describes how the `ffun.resources` backend module stores interval-scoped per-user resource counters and atomically reserves and accounts resource usage against caller-supplied limits.

## Scope

This specification covers resource identity, counter semantics, lazy initialization, reservation and conversion behavior, history and aggregate queries, the `r_resources` table, and the public interface exposed by `ffun.resources.domain`.

The concrete resource-kind registry, resource units and conversions, selection of accounting intervals, user-configured limits, billing, and presentation of resource history are out of scope.

## Dictionary

- `resource kind` - a caller-owned stable integer identifier for one independently accounted category of resource.
- `resource interval` - an accounting period identified in this module only by its caller-supplied start timestamp.
- `resource record` - the counters for one user, resource kind, and resource interval.
- `reserved amount` - resource capacity provisionally claimed before final usage is known.
- `used amount` - finalized resource consumption accumulated for a resource record.
- `resource limit` - a caller-supplied upper bound applied to one reservation attempt.

## Module responsibility

`ffun.resources` MUST be a domain-level module that owns generic per-user resource accounting, persistence of used and reserved counters, atomic limit-checked reservations, conversion of reservations into finalized usage, and resource history and aggregate queries.

The module MUST treat resource kinds, counter units, interval start timestamps, and limits as caller-owned inputs.
It MUST NOT own a resource-kind registry, derive interval boundaries, convert between business units and stored counter units, or persist resource limits.

Callers that account resource consumption MUST use the module's domain boundary rather than read or write the resource table directly.

## Domain behavior

### Resource identity

One resource record MUST be identified by the exact tuple `(user_id, kind, interval_started_at)`.

`user_id` MUST identify a user by UUID.
`kind` MUST be an integer whose stable meaning is owned by the calling product or domain module.
Assigned resource-kind ids MUST NOT be changed or reused while persisted records or callers depend on their meaning.

The resource-kind namespace is extensible and caller-owned.
The resources module MUST accept integer kind ids without validating them against a module-owned registry, and the database MUST NOT constrain the set of kind ids.

`interval_started_at` MUST be a timestamp with time zone supplied by the caller.
It identifies an interval but does not imply an interval duration or alignment rule.
Callers MUST use the same exact timestamp for all operations intended to address the same interval.

Records with different users, kinds, or interval start timestamps MUST be accounted independently.

### Resource entity and counters

A resource entity MUST expose `user_id`, `kind`, `interval_started_at`, `used`, and `reserved`.
It MUST expose `total` as the sum of `used` and `reserved`.
Persistence timestamps MUST NOT be part of the resource entity returned to callers.

The `used` and `reserved` counters MUST be stored as opaque integers.
For one resource record, reservation amounts, finalized used amounts, released reserved amounts, and limits MUST use the same caller-defined unit.

Callers MUST supply non-negative reservation, conversion, and limit values.
The module does not normalize units or infer the relationship between a provisional reservation and the finalized usage that replaces it.

### Lazy initialization

A missing resource record MUST be initialized with `used = 0` and `reserved = 0` when it is loaded through the single-resource or batch current-resource interface or when a reservation is attempted.

Initialization MUST be idempotent.
Concurrent initialization of the same identity MUST preserve one record and MUST NOT reset or overwrite counters already stored in that record.

Loading an existing resource record MUST NOT change its counters.
Loading resource history and aggregate usage MUST NOT initialize missing records.

### Reservation

A reservation attempt MUST first ensure that its resource record exists and then atomically add `amount` to `reserved` only when `used + reserved + amount <= limit` for the current stored row.

The operation MUST return `true` when the conditional update succeeds and `false` when the current counters and supplied limit reject the reservation.
Concurrent reservation attempts for the same resource identity MUST evaluate the limit against serialized row updates so their combined successful reservations cannot exceed the supplied limit when callers use the same limit.

The supplied limit applies only to that reservation attempt.
It MUST NOT be persisted, and reducing a later call's limit MUST NOT rewrite counters reserved or used by earlier calls.

A zero reservation amount MUST be allowed and MUST succeed only when the record's current total does not exceed the supplied limit.
A rejected reservation MUST leave `used` and `reserved` unchanged, but it MAY leave behind the zero-valued resource record created by lazy initialization.

### Conversion of reserved capacity to used capacity

Conversion MUST atomically add the caller-supplied `used` amount to the stored used counter and subtract the caller-supplied `reserved` amount from the stored reserved counter.

The conversion MUST succeed only when the addressed resource record exists and its stored reserved counter is at least the reserved amount being released.
If the record is missing or has insufficient reserved capacity, the operation MUST raise `ffun.resources.errors.CanNotConvertReservedToUsed` and MUST leave the counters unchanged.

The finalized used amount MAY differ from the released reserved amount.
Consequently, conversion MAY increase or decrease the record's total relative to its total before conversion and MUST NOT reapply the reservation limit.
A caller MAY release a reservation without recording usage by converting it with a zero used amount.

### Queries

The batch current-resource query MUST return a mapping from every requested user id to the resource entity for the requested kind and interval, lazily initializing missing records.
Repeated user ids MUST correspond to one mapping entry.
An empty user-id input MUST return an empty mapping.

The single current-resource query MUST return the same entity as the batch query for a one-user input and MUST lazily initialize a missing record.

The history query MUST return all resource records for one user and kind ordered by `interval_started_at` descending.
It MUST return an empty list when no records match and MUST NOT create a record.

The aggregate query MUST sum only `used`, excluding `reserved`, across every interval for the requested kind and group the result by user id.
It MUST return entries only for users that have records of that kind.

### Atomicity and timestamps

Initialization, reservation, conversion, and queries use the module's independently committed database operations and do not participate in a caller-owned transaction.
A reservation's lazy initialization and conditional counter update are separate database operations; therefore a failed or rejected reservation can still commit initialization of an empty record.

Every successful reservation or conversion, including a successful zero-value update, MUST set `updated_at` to the database's current timestamp.
Initialization MUST set `created_at` and `updated_at` from database time.
Read-only queries MUST NOT change either timestamp.

## Database schema

The module MUST own exactly one table, `r_resources`.

### `r_resources`

```sql
-- Stores interval-scoped resource accounting counters for users.
CREATE TABLE r_resources (
    user_id UUID NOT NULL, -- User whose resource usage is accounted; stored without a cross-module foreign key.
    kind INTEGER NOT NULL, -- Stable caller-owned resource-kind id; the open set is not constrained by this module.
    interval_started_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Exact caller-supplied start of the accounting interval.
    used BIGINT NOT NULL DEFAULT 0, -- Finalized resource consumption in the caller-defined unit.
    reserved BIGINT NOT NULL DEFAULT 0, -- Provisionally claimed resource capacity in the same unit.
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), -- Database time at which this resource record was initialized.
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), -- Database time of the latest successful counter update.
    PRIMARY KEY (kind, user_id, interval_started_at) -- Ensures one resource record per resource identity and supports kind-prefixed queries.
);
```

The table MUST NOT define foreign keys because the user id belongs to another top-level module and resource kinds belong to caller-owned registries.
The database MUST NOT use constraints to validate counter signs, interval alignment, resource-kind membership, or relationships among counters and limits; callers and domain behavior own those invariants.

No secondary indexes are required.
The primary key supports exact identity lookups, user history within a kind through its `(kind, user_id)` prefix, and kind-wide aggregation through its `kind` prefix.

## Domain interface

Cross-module callers MUST import resource behavior from `ffun.resources.domain`, resource entities from `ffun.resources.entities`, and resource errors from `ffun.resources.errors`.
They MUST NOT import `ffun.resources.operations` or access `r_resources` directly.

`ffun.resources.domain` MUST expose these asynchronous operations:

- `load_resources(user_ids, kind, interval_started_at)` returns the lazily initialized current-resource mapping described above.
- `load_resource(user_id, kind, interval_started_at)` returns one lazily initialized resource entity.
- `try_to_reserve(user_id, kind, interval_started_at, amount, limit)` performs the conditional reservation and returns whether it succeeded.
- `convert_reserved_to_used(user_id, kind, interval_started_at, used, reserved)` finalizes usage and releases reserved capacity or raises `CanNotConvertReservedToUsed`.
- `load_resource_history(user_id, kind)` returns the ordered resource history.
- `count_total_resources_per_user(kind)` returns used-only totals grouped by user.

The batch loader MUST accept a finite iterable of user ids.
The interface MUST return resource mappings keyed by the semantic `UserId` values supplied by callers.

The domain interface MUST NOT accept an execute callable or expose transaction ownership to callers.

## Audit records

Module does not produce audit records because it stores technical quota-accounting counters rather than durable explanations of caller-owned business changes.

## Business events

Module does not produce business events.
Calling modules own any business events generated by the activity whose resource consumption is reserved or finalized.
