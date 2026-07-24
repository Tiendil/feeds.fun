# Resources module

## Goal of the document

This document describes how the `ffun.resources` backend module stores interval-scoped per-user resource counters and atomically reserves and accounts resource usage against caller-supplied limits.
It also describes how the module tries each caller-supplied user's resource options in priority order.

## Scope

This specification covers resource identity, counter semantics, lazy initialization, reservation and conversion behavior, history and aggregate queries, the `r_resources` table, and the public interface exposed by `ffun.resources.domain`.
It also covers ordered reservation from per-user specifications.

The concrete resource-kind registry, resource units and conversions, selection of accounting intervals, user-configured limits, billing, and presentation of resource history are out of scope.

## Dictionary

- `resource kind` - a caller-owned stable integer identifier for one independently accounted category of resource.
- `resource interval` - an accounting period identified in this module only by its caller-supplied start timestamp.
- `resource record` - the counters for one user, resource kind, and resource interval.
- `reserved amount` - resource capacity provisionally claimed before final usage is known.
- `used amount` - finalized resource consumption accumulated for a resource record.
- `resource limit` - a caller-supplied upper bound applied to one reservation attempt.
- `reservation option` - one caller-supplied resource kind, interval, and limit; its position in one user's reservation specification defines its priority.
- `reservation specification` - one caller-supplied user, amount, and ordered collection of reservation options.
- `reservation result` - the user, resource kind, interval start, and amount captured by one successful reservation.

## Module responsibility

`ffun.resources` MUST be a domain-level module that owns generic per-user resource accounting, persistence of used and reserved counters, atomic limit-checked reservations, conversion of reservations into finalized usage, and resource history and aggregate queries.
It MUST also own ordered reservation across caller-supplied per-user specifications.

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

`ffun.resources.entities` MUST define `ResourceReservationOption` with `kind`, `interval_started_at`, and `limit`.
It MUST define `ResourceReservationSpecification` with `user_id`, `amount`, and an ordered collection of reservation options.
It MUST define `ResourceReservation` with `user_id`, `kind`, `interval_started_at`, and `amount`.
Reservation results MUST contain the values captured by the successful attempt and MUST NOT recompute them during later conversion or release.

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

The atomic single-user reservation primitive MUST remain internal to `ffun.resources`.
It MUST NOT be exposed through `ffun.resources.domain` or called by other top-level modules.

The operation MUST return `true` when the conditional update succeeds and `false` when the current counters and supplied limit reject the reservation.
Concurrent reservation attempts for the same resource identity MUST evaluate the limit against serialized row updates so their combined successful reservations cannot exceed the supplied limit when callers use the same limit.

The supplied limit applies only to that reservation attempt.
It MUST NOT be persisted, and reducing a later call's limit MUST NOT rewrite counters reserved or used by earlier calls.

A zero reservation amount MUST be allowed and MUST succeed only when the record's current total does not exceed the supplied limit.
A rejected reservation MUST leave `used` and `reserved` unchanged, but it MAY leave behind the zero-valued resource record created by lazy initialization.

### Ordered reservation from per-user specifications

The domain MUST provide an operation that accepts a finite ordered collection of reservation specifications.
Each reservation specification MUST supply one user id, a non-negative amount, and a finite ordered collection of reservation options.
Each reservation option MUST supply a resource kind, an interval start timestamp, and a non-negative limit for that specification's user.

The operation MUST process reservation specifications in their supplied order.
For each specification, it MUST attempt options in their supplied order through the internal atomic single-user reservation primitive until one succeeds or all options reject the reservation.
It MUST stop processing a specification's options after its first success.
A user MUST therefore receive at most one successful reservation from one invocation.

Ordered reservation MUST be domain-level orchestration over that internal primitive and MUST NOT introduce separate persistence, resource-initialization, limit-checking, or counter-update logic.

Repeated specifications for the same user MUST be deduplicated while preserving the first specification and its position.
Processing of each specification MUST finish before processing starts for the next specification.

Every successful user reservation MUST be returned as a reservation result containing the user id, selected kind, selected interval start, and captured amount.
Users whose specifications have no options or whose every option rejects the reservation MUST be absent from the result.
Reservation results MUST be returned as a list in the relative order of their first-occurrence specifications.
An empty specification collection MUST return an empty list.

Each individual attempt retains the existing independently committed atomicity guarantee.
Successes for earlier users or options MUST NOT be rolled back when a later attempt is rejected.
The overall operation does not provide idempotency across invocations, and concurrent invocations may reserve different options for the same user while each individual resource limit remains enforced.

### Conversion of reserved capacity to used capacity

Conversion MUST atomically add the caller-supplied `used` amount to the stored used counter and subtract the caller-supplied `reserved` amount from the stored reserved counter.

The conversion MUST succeed only when the addressed resource record exists and its stored reserved counter is at least the reserved amount being released.
If the record is missing or has insufficient reserved capacity, the operation MUST raise `ffun.resources.errors.CanNotConvertReservedToUsed` and MUST leave the counters unchanged.

The finalized used amount MAY differ from the released reserved amount.
Consequently, conversion MAY increase or decrease the record's total relative to its total before conversion and MUST NOT reapply the reservation limit.
A caller MAY release a reservation without recording usage by converting it with a zero used amount.

The domain MUST also provide bulk conversion for a finite ordered collection of reservation results.
Bulk conversion MUST process reservations in their supplied order through the single-resource conversion operation.
When `consume` is true, it MUST add each reservation's captured amount to used and release the same amount from reserved.
When `consume` is false, it MUST add zero to used and release each reservation's captured amount from reserved.
An empty reservation collection MUST be a no-op.
If a conversion raises `CanNotConvertReservedToUsed`, bulk conversion MUST propagate the error immediately.
Successful earlier conversions MUST remain committed, and later reservations MUST remain unprocessed.

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
Ordered reservation composes those operations and does not add a transaction spanning users or resource options.
Bulk conversion also composes independently committed conversion operations and does not add a transaction spanning reservation results.

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
- `try_to_reserve_in_order(specifications)` accepts `ResourceReservationSpecification` values, tries each user's options in order, and returns successful `ResourceReservation` values in specification order.
- `convert_reserved_to_used(user_id, kind, interval_started_at, used, reserved)` finalizes usage and releases reserved capacity or raises `CanNotConvertReservedToUsed`.
- `convert_reservations_to_used(reservations, *, consume)` converts captured `ResourceReservation` values in order, either consuming or releasing their complete amounts.
- `load_resource_history(user_id, kind)` returns the ordered resource history.
- `count_total_resources_per_user(kind)` returns used-only totals grouped by user.

The batch loader MUST accept a finite iterable of user ids.
The interface MUST return resource mappings keyed by the semantic `UserId` values supplied by callers.
The ordered reservation operation MUST accept a finite iterable of reservation specifications and return a list ordered by the corresponding specifications.
Cross-module callers MUST use `try_to_reserve_in_order` for reservations, including reservations with one specification and one option.
The bulk conversion operation MUST accept a finite iterable of reservation results and MUST NOT recompute their captured identities or amounts.

The domain interface MUST NOT accept an execute callable or expose transaction ownership to callers.

## Audit records

Module does not produce audit records because it stores technical quota-accounting counters rather than durable explanations of caller-owned business changes.

## Business events

Module does not produce business events.
Calling modules own any business events generated by the activity whose resource consumption is reserved or finalized.
