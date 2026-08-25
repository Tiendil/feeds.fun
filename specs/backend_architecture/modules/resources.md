# Resources module

## Goal of the document

This document describes the responsibility and observable accounting behavior of the `ffun.resources` backend module.

## Scope

This specification applies to generic per-user resource accounting owned by `ffun.resources`.
The business meaning of resources and the policies that choose their units, accounting intervals, limits, billing, and presentation are outside the module's responsibility.

## Dictionary

- `resource kind` - a caller-owned stable category of independently accounted resources.
- `resource interval` - an accounting period identified by its caller-supplied start.
- `resource identity` - one exact user, resource kind, and interval start that together distinguish a resource record.
- `resource record` - the current finalized and provisionally claimed quantities for one resource identity.
- `reservation` - a provisional claim on one user's resource capacity that counts against an applicable limit until it is replaced by finalized usage or released.
- `reserved amount` - the total capacity currently claimed by reservations against one resource record.
- `used amount` - finalized resource consumption accumulated for a resource record.
- `resource limit` - a caller-supplied upper bound applied to one reservation attempt.
- `reservation option` - one resource kind and interval considered at a caller-defined priority.
- `resource statistics record` - cumulative finalized consumption for one user, resource kind, and UTC calendar date.

## Module responsibility

The module owns per-user used and reserved resource quantities, the rules for changing them, and the resulting consumption history.
Callers own each resource kind's meaning, the unit shared by related quantities, the intervals to account against, the limits applied to reservation attempts, and the business activity represented by consumption.
The module MUST NOT define resource kinds, derive interval boundaries, convert units, or retain caller-supplied limits as accounting state.

Callers MUST respect the module's reservation decisions and MUST NOT independently change the accounting state it owns.

## Special module rules

This module has no special module rules.

## Domain model

A resource record is the durable current accounting state for exactly one user, resource kind, and caller-defined interval start.
That identity MUST remain stable for the record's lifetime, and records with different identities MUST be accounted independently.
Each record has a used amount and a reserved amount in one caller-defined unit; its total resource commitment is their sum.

A resource kind's stable meaning belongs to its caller.
The resource-kind namespace MUST remain open, and the module MUST accept kinds it has not previously encountered.
A kind's identity MUST NOT be changed or reused while records or callers depend on its meaning.

An interval start MUST identify one unambiguous caller-defined instant without implying an interval duration or alignment.
Callers MUST use the same instant whenever they refer to the same resource interval.

A reservation allows work to claim resource capacity before its final consumption is known.
While the reservation remains active, its capacity counts as committed so that the same capacity cannot be promised to competing work.
Each reservation belongs to exactly one resource record and has a captured amount fixed when the reservation succeeds.
The resource record's reserved amount represents the total capacity claimed by its active reservations.

A reservation remains active until it is finalized or released.

A resource statistics record is durable historical accounting for exactly one user, resource kind, and UTC calendar date.
It accumulates finalized consumption attributed to that date independently of the resource interval against which the consumption was accounted.
Statistics records with different users, kinds, or dates MUST be accounted independently.

## Domain behavior

### Quantity validity

Used amounts, reserved amounts, reservation amounts, finalized amounts, and limits MUST be non-negative quantities.
Every limit, reservation, release, and finalized use affecting one resource record MUST use the same caller-defined unit.
The module MUST NOT normalize units or infer a relationship between a provisional amount and the finalized amount that replaces it.

### Reservations

Callers MAY provide reservation options in priority order.
For each user, the module MUST select the first available option whose resulting resource total does not exceed the applicable limit.
An option without an applicable limit MUST be unavailable to that user, and one selection MUST produce at most one reservation per user.

**Example:** Suppose A, B, and C are illustrative names for caller-owned resource kinds listed in descending priority.
When a reservation fits the applicable limit for A, A is selected and B and C are not considered.
When A is unavailable, a reservation would raise B's total from 80 to 105 under a limit of 100, and the reservation fits C's limit, B is rejected and C is selected.

A successful reservation MUST add its captured amount to the resource record's reserved amount.
A rejected reservation MUST leave accounting state unchanged.
The supplied limit MUST apply only to that attempt and MUST NOT become accounting state.

Concurrent attempts against the same resource identity MUST enforce their limits atomically so that successful reservations cannot collectively exceed the applicable limit.

### Reservation finalization and release

Finalizing a reservation MUST remove its captured amount from reserved capacity and add the actual consumption to used capacity.
Releasing a reservation MUST remove its captured amount without adding consumption.

The actual consumption MAY differ from the captured amount, and reservation limits MUST NOT be reapplied during finalization.

**Example:** When 30 units of B are reserved and actual consumption is 18 units, finalization removes 30 units from B's reserved amount and adds 18 units to its used amount.

Finalization or release MUST fail without effects when the resource record's reserved amount is less than the reservation's captured amount.

When several reservations are finalized as one accounting change, all corresponding resource and statistics effects MUST succeed or fail together.

### Consumption statistics

Successful finalization MUST add the actual consumption to the statistics for the affected user and resource kind on the current UTC date.
All consumption finalized by one accounting change MUST be attributed to the same UTC date.
Reservations, releases, and failed finalizations MUST NOT change statistics.

Each statistics change and the resource-accounting change that produced it MUST succeed or fail together.
Statistics for different users, kinds, or dates MUST remain independent.

Statistics MUST be retrievable at daily, monthly, and yearly UTC calendar granularity without changing accounting state.
Daily statistics MUST preserve their calendar dates, while monthly and yearly statistics MUST sum the corresponding daily consumption.

When recorded consumption exists, statistics retrieval MUST present a continuous series from the earliest through the latest recorded interval, using zero for gaps.

**Example:** When finalized consumption for C is 5 units on August 1 and 2 units on August 3, the daily series for those dates is 5, 0, 2 and the monthly total is 7.

When no consumption has been recorded, statistics retrieval MUST report zero for the current interval without creating accounting state.

### Accounting retrieval

Current accounting state MUST be retrievable for a resource identity without changing accounting state.
When no resource record exists, its current used and reserved amounts MUST be treated as zero.

Every resource record for one user and resource kind MUST be retrievable in descending order of interval start.
Missing records MUST contribute no historical result.

Used amounts MUST be aggregatable across all intervals for one resource kind, grouped by user.
The aggregate MUST exclude reserved amounts, and missing records MUST contribute no aggregate result.

## Audit records

This module produces no audit records.

**Rationale:** It stores technical accounting state rather than evidence explaining caller-owned business changes.

## Business events

This module produces no business events.

**Rationale:** Calling modules own events for the activity whose resources are reserved or finalized.
