# Resources module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.resources` backend module.

## Scope

This specification covers interval-scoped per-user resource counters, lazy initialization, limit-checked reservations, ordered reservation options, conversion of reserved capacity to usage, history, and aggregate queries.

Resource-kind registries, resource units and conversions, accounting-interval selection, user-configured limits, billing, and presentation of resource history are out of scope.

## Dictionary

- `resource kind` - a caller-owned stable integer identifier for one independently accounted category of resource.
- `resource interval` - an accounting period identified by its caller-supplied start time.
- `resource record` - used and reserved counters for one user, resource kind, and resource interval.
- `reserved amount` - resource capacity provisionally claimed before final usage is known.
- `used amount` - finalized resource consumption accumulated for a resource record.
- `resource limit` - a caller-supplied upper bound applied to one reservation attempt.
- `reservation option` - one caller-supplied resource kind and interval, whose position defines its priority.
- `reservation specification` - one caller-supplied user and a collection of optional limits aligned with the reservation options.
- `reservation result` - the user, kind, interval, and amount captured by one successful reservation.

## Module responsibility

The module MUST own generic per-user resource accounting, durable used and reserved counters, atomic limit-checked reservation, reservation conversion and release, ordered reservation selection, history queries, and aggregate usage queries.

The module MUST treat resource kinds, counter units, interval starts, and limits as caller-owned inputs.
It MUST NOT own a resource-kind registry, derive interval boundaries, convert units, or persist resource limits.

Callers MUST use the public module boundary rather than independently changing resource counters.

## Domain behavior

### Resource identity and counters

One resource record MUST be identified by the exact tuple of user id, resource kind, and interval start.
Records with different identity values MUST be accounted independently.

A resource kind MUST be an integer whose stable meaning is owned by its caller.
The resource-kind namespace MUST remain open, and the module MUST NOT reject unknown integer kinds.
Assigned kind values MUST NOT be changed or reused while records or callers depend on their meaning.

An interval start MUST be a caller-supplied timezone-aware timestamp.
It identifies the interval without implying duration or alignment.
Callers MUST reuse the exact value for all operations addressing the same interval.

A resource record exposed to callers MUST contain its user id, kind, interval start, used counter, and reserved counter.
Its total MUST equal used plus reserved.

Used and reserved counters MUST be opaque integers.
For one resource record, limits, reservations, releases, and finalized usage MUST use the same caller-defined unit.

Callers MUST provide non-negative amounts and limits.
The module MUST NOT normalize units or infer a relationship between a provisional reservation and the finalized usage that replaces it.

### Lazy initialization

Loading a current resource record or attempting a reservation MUST initialize missing records with zero used and reserved counters.

Initialization MUST be idempotent.
Concurrent initialization of the same identity MUST preserve one record and MUST NOT reset existing counters.

Loading an existing current record MUST NOT change its counters.
History and aggregate queries MUST NOT initialize missing records.

### Reservation contract

An ordered reservation request MUST contain:

- one non-negative amount shared by all users.
- an ordered collection of options, each containing one resource kind and interval start.
- an ordered collection of specifications, each containing one user id and one optional limit for every option.

Each specification's limits MUST align positionally with the options.
A non-null limit MUST apply only to its user and corresponding option.
A null limit MUST make that option unavailable to that user.

A limit-count mismatch in any specification MUST fail before any reservation attempt.
Repeated user ids in the specification collection MUST also fail before any reservation attempt.

The options MUST be tried in their supplied order.
For each option, every not-yet-reserved user with a non-null corresponding limit MUST be considered.
A user MUST receive at most one successful reservation from one request.

A reservation succeeds only when adding the requested amount would leave the resource total at or below that user's limit for that attempt.
Rejected reservations MUST leave counters unchanged, although lazy initialization MAY leave a zero-valued record.

Successful results MUST contain the user id, selected kind, selected interval start, and captured amount.
They MUST be returned in the relative order of their specifications.
Users for whom every option is unavailable or rejected MUST be absent.

An empty specification or option collection MUST return an empty result.

A zero amount MUST be allowed.
It MUST succeed only when the current total does not exceed the supplied limit.

Concurrent attempts for the same resource identity MUST enforce their limit checks atomically so successful reservations using the same limit cannot collectively exceed it.

The supplied limit applies only to its attempt.
It MUST NOT become stored resource state or rewrite counters established by earlier attempts.

Each option attempt MUST be atomic and complete independently.
Successes for earlier options MUST remain committed when a later option is rejected or fails.
The overall ordered request MUST NOT promise atomicity or idempotency across options or invocations.

### Conversion and release

Conversion MUST accept an ordered collection of reservation results and one non-negative finalized used amount shared by all of them.

Each user MAY occur at most once in the collection, regardless of kind or interval.
Repeated users MUST fail before counters change.
An empty collection MUST be a no-op.

Conversion MUST add the shared finalized amount to each addressed used counter and subtract the amount captured by that reservation from its reserved counter.

Every addressed record MUST exist and contain at least the captured reserved amount.
If any reservation cannot be converted, the entire conversion MUST fail without changing any addressed counter.

The finalized amount MAY differ from captured reservation amounts.
Conversion MAY therefore increase or decrease each total and MUST NOT reapply reservation limits.
A zero finalized amount MUST release reservations without recording usage.

### Current-resource queries

The batch current-resource query MUST return one record for every distinct requested user for the selected kind and interval.
It MUST lazily initialize missing records.
Repeated user ids MUST correspond to one result entry.
An empty user collection MUST return an empty mapping.

The single current-resource query MUST provide the same result as a one-user batch query.

### History and aggregate queries

The history query MUST return all records for one user and kind ordered by interval start descending.
It MUST return an empty collection when no record matches and MUST NOT initialize state.

The aggregate query MUST sum used counters only, excluding reserved counters, across all intervals for the selected kind.
It MUST group results by user and include only users with records of that kind.

## Public interface

The public interface MUST provide these operations:

- `load_resources` loads current records for multiple users, one kind, and one interval.
- `load_resource` loads one current record.
- `try_to_reserve_in_order` applies ordered options and per-user limits and returns successful reservations.
- `convert_reserved_to_used` converts or releases captured reservations atomically.
- `load_resource_history` loads one user's history for a kind.
- `count_total_resources_per_user` returns used-only totals grouped by user for a kind.

`load_resources` MUST return a mapping keyed by the semantic user identifiers supplied by callers.
Each current-resource result MUST contain user id, kind, interval start, used, reserved, and derived total values.

`try_to_reserve_in_order` MUST accept the semantic option and specification fields defined by the reservation contract and return the semantic reservation-result fields defined there.
Callers MUST use this operation for reservations, including a single user and a single option.

`convert_reserved_to_used` MUST use the identities and captured amounts contained in its reservation inputs.
It MUST NOT require callers to recompute them or expose transaction ownership.

The public interface MUST own transaction boundaries for reservation attempts and conversions.
Current-resource, history, and aggregate queries MUST execute independently of caller-owned transactions.

## Audit records

Module does not produce audit records because it stores technical accounting counters rather than explanations of caller-owned business changes.

## Business events

Module does not produce business events because calling modules own events for the activity whose resources are reserved or finalized.
