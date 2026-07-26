# Resources module

## Goal of the document

This document describes how the `ffun.resources` backend module stores interval-scoped per-user resource counters and atomically reserves and accounts resource usage against caller-supplied limits.
It also describes how the module tries caller-supplied shared resource options for each user in priority order.

## Scope

This specification covers resource identity, counter semantics, lazy initialization, reservation and conversion behavior, history and aggregate queries, the `r_resources` table, and the public interface exposed by `ffun.resources.domain`.
It also covers ordered reservation from shared options and per-user limit specifications.

The concrete resource-kind registry, resource units and conversions, selection of accounting intervals, user-configured limits, billing, and presentation of resource history are out of scope.

## Dictionary

- `resource kind` - a caller-owned stable integer identifier for one independently accounted category of resource.
- `resource interval` - an accounting period identified in this module only by its caller-supplied start timestamp.
- `resource record` - the counters for one user, resource kind, and resource interval.
- `reserved amount` - resource capacity provisionally claimed before final usage is known.
- `used amount` - finalized resource consumption accumulated for a resource record.
- `resource limit` - a caller-supplied upper bound applied to one reservation attempt.
- `reservation option` - one caller-supplied resource kind and interval; its position in the operation-wide option collection defines its priority for every user.
- `reservation specification` - one caller-supplied user and an ordered collection of limits aligned with the operation-wide reservation options.
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

`ffun.resources.entities` MUST define `ResourceReservationOption` with `kind` and `interval_started_at`.
It MUST define `ResourceReservationSpecification` with `user_id` and an ordered collection of optional limits.
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

A reservation attempt MUST accept a finite ordered collection of user-id and limit pairs plus one resource kind, interval start, and amount shared by every pair.
Repeated user ids MUST raise `ffun.resources.errors.DuplicateReservationUserIds` before any resource records are initialized.
An empty pair collection MUST return an empty list without initializing resource records.

The attempt MUST first ensure that every requested user's resource record exists and then atomically add the shared `amount` to `reserved` for each row only when `used + reserved + amount <= limit` for that user's paired limit.
Lazy initialization and all conditional counter updates in one attempt MUST execute within one database transaction.
An error during either step MUST roll back both steps.

The atomic bulk reservation primitive MUST remain internal to `ffun.resources`.
It MUST NOT be exposed through `ffun.resources.domain` or called by other top-level modules.

The operation MUST return a list of reservation results for the user ids whose conditional updates succeeded.
Each result MUST capture the successful user's id together with the shared resource kind, interval start, and amount.
Results MUST preserve the relative order of their corresponding input pairs.
Users whose current counters and supplied limits reject the reservation MUST be absent from the result.
Concurrent reservation attempts for the same resource identity MUST evaluate the limit against serialized row updates so their combined successful reservations cannot exceed the supplied limit when callers use the same limit.

The supplied limit applies only to that reservation attempt.
It MUST NOT be persisted, and reducing a later call's limit MUST NOT rewrite counters reserved or used by earlier calls.

A zero reservation amount MUST be allowed and MUST succeed only when the record's current total does not exceed the supplied limit.
A rejected reservation MUST leave `used` and `reserved` unchanged, but it MAY leave behind the zero-valued resource record created by lazy initialization.

### Ordered reservation from shared options and per-user specifications

The domain MUST provide an operation that accepts one non-negative amount, a finite ordered collection of reservation options, and a finite ordered collection of reservation specifications.
Each reservation option MUST supply one resource kind and interval start timestamp shared by every specification in the operation.
Each reservation specification MUST supply one user id and exactly one optional limit for each reservation option.
The position of each limit MUST correspond to the reservation option at the same position.
A non-`None` limit MUST be non-negative and MUST apply only to that specification's user and the corresponding reservation option.
A `None` limit MUST make the corresponding reservation option unavailable to that specification's user.
The operation MUST raise `ffun.resources.errors.ReservationOptionsAndLimitsMismatch` before attempting any reservation when any specification has a different number of limits than the operation has reservation options.

Repeated user ids in reservation specifications MUST raise `ffun.resources.errors.DuplicateReservationSpecifications` before any reservation is attempted.
It MUST process the shared reservation options in their supplied order.
For each option, it MUST submit every not-yet-reserved user whose corresponding limit is not `None` as one call to the internal atomic bulk reservation primitive.
It MUST exclude successful users from later option attempts.
A user MUST therefore receive at most one successful reservation from one invocation.

Ordered reservation MUST be domain-level orchestration over that internal primitive and MUST NOT introduce separate persistence, resource-initialization, limit-checking, or counter-update logic.

Every successful user reservation MUST be returned as a reservation result containing the user id, selected kind, selected interval start, and the operation-wide captured amount.
Users for whom every option is unavailable or rejects the reservation, and all users when the shared option collection is empty, MUST be absent from the result.
Reservation results MUST be returned as a list in the relative order of their first-occurrence specifications.
An empty specification collection MUST return an empty list.

Each option's bulk attempt retains its own transaction and commit guarantee.
Successes for earlier options MUST NOT be rolled back when a later attempt is rejected.
The overall operation does not provide idempotency across invocations, and concurrent invocations may reserve different options for the same user while each individual resource limit remains enforced.

### Conversion of reserved capacity to used capacity

Bulk conversion MUST accept a finite ordered list of reservation results plus one non-negative used amount shared by every reservation.
It MUST submit all reservation identities and captured amounts through one heterogeneous database update rather than grouping them by common values.
Each user MAY occur at most once in the reservation list, regardless of resource kind or interval start.
Repeated user ids MUST raise `ffun.resources.errors.DuplicateReservationUserIds` before any counters are changed.
An empty reservation collection MUST be a no-op.

Bulk conversion MUST add the shared used amount to every addressed stored used counter and release each reservation's captured amount from its addressed reserved counter.
Bulk conversion MUST succeed only when every addressed resource record exists and every stored reserved counter is at least the corresponding reservation's captured amount.
The heterogeneous update MUST still address rows by full resource identity, but conversion completeness MUST be verified by comparing the set of user ids returned by the update with the set of requested user ids.
The operation-wide user-id uniqueness invariant makes this comparison sufficient without separately comparing returned resource kinds or interval starts.
If any reservation cannot be converted, the operation MUST raise `ffun.resources.errors.CanNotConvertReservedToUsed` and leave every addressed counter unchanged.
All validation of the database update result MUST occur inside the transaction that owns the heterogeneous update.

The shared finalized used amount MAY differ from each released reservation amount.
Consequently, conversion MAY increase or decrease each record's total relative to its total before conversion and MUST NOT reapply the reservation limit.
A caller MAY release reservations without recording usage by supplying a zero used amount.

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

Standalone initialization and queries use the module's independently committed database operations and do not participate in a caller-owned transaction.
Each bulk reservation attempt owns a database transaction that covers its lazy initialization and conditional counter updates.
A rejected reservation MAY commit initialization of an empty record, while an error during the attempt MUST roll back that initialization.
Ordered reservation composes those operations and does not add a transaction spanning resource options.
One bulk conversion owns one database transaction that covers every heterogeneous reservation in the operation.

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
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Database time at which this resource record was initialized.
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Database time of the latest successful counter update.
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
- `try_to_reserve_in_order(*, amount, options, specifications)` accepts one shared amount, ordered `ResourceReservationOption` values, and ordered `ResourceReservationSpecification` values; it tries the shared options for each user in order and returns successful `ResourceReservation` values in specification order.
- `convert_reserved_to_used(reservations, *, used)` adds one shared finalized used amount and releases all captured `ResourceReservation` values in one heterogeneous atomic operation.
- `load_resource_history(user_id, kind)` returns the ordered resource history.
- `count_total_resources_per_user(kind)` returns used-only totals grouped by user.

The batch loader MUST accept a finite iterable of user ids.
The interface MUST return resource mappings keyed by the semantic `UserId` values supplied by callers.
The ordered reservation operation MUST accept finite ordered collections of options and reservation specifications and return a list ordered by the corresponding specifications.
Cross-module callers MUST use `try_to_reserve_in_order` for reservations, including reservations with one specification and one option.
The bulk conversion operation MUST accept a finite list of reservation results and MUST NOT recompute their captured identities or amounts.

The domain interface MUST NOT accept an execute callable or expose transaction ownership to callers.

## Audit records

Module does not produce audit records because it stores technical quota-accounting counters rather than durable explanations of caller-owned business changes.

## Business events

Module does not produce business events.
Calling modules own any business events generated by the activity whose resource consumption is reserved or finalized.
