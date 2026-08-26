# Entitlements module

## Goal of the document

This document describes the responsibility and observable entitlement behavior of the `ffun.entitlements` backend module.

## Scope

This specification applies to source-owned entitlement grants and the effective entitlement state derived from them by `ffun.entitlements`.
The following adjacent concerns are outside the module's responsibility:

- purchased-state lifecycles.
- product policy.
- payment-provider protocols.
- entitlement consumption.
- presentation.

## Dictionary

- `entitlement kind` - a stable category of capability or limit with one rule for combining active grant values and one lifetime status.
- `source` - one entitlement-granting system that owns and may change its own grants.
- `source entitlement` - one durable grant made by one source for one user and entitlement kind as part of one benefit transaction.
- `purchased-state owner` - the optional subscription or one-time purchase whose entitlement state includes a source entitlement.
- `active source entitlement` - an unrevoked source entitlement whose effective period covers the evaluation time.
- `effective entitlement interval` - a maximal period during which active source entitlements grant one entitlement kind to one user with one unchanged combined value.

## Module responsibility

The module owns the supported entitlement kinds, each source's grants and revocations, and the rules that determine every user's effective entitlement state.
Entitlement-granting callers own the meaning of their source identities and their decisions to establish or revoke grants.
Purchased-state modules own subscription and one-time-purchase lifecycles rather than the entitlement module.

Sources MUST change grants through the module's domain boundary and MUST NOT change another source's grants.
Callers making entitlement decisions MUST use the module's effective state and MUST NOT independently combine source grants.

## Special module rules

Entitlement state changes MAY participate in atomic domain workflows owned by `ffun.benefits`.
When they do, entitlement and purchased-state effects MUST succeed or fail together.
This participation is limited to entitlement-owned state and effects and MUST NOT transfer ownership of purchased-state policy or workflow decisions from `ffun.benefits`.

## Domain model

An entitlement kind is a stable category whose meaning, value-combination rule, and lifetime status MUST NOT change while grants or callers depend on them.
The supported set is intentionally closed and consists of:

- daily token entitlements, which use the largest active grant value and are not lifetime.
- monthly token entitlements, which use the largest active grant value and are not lifetime.
- lifetime token entitlements, which use the sum of all active grant values and are lifetime.

A source entitlement is the durable record of one source's grant to one user for one entitlement kind, caused by one benefit transaction.
Its stable identity combines the source, granting benefit transaction, user, and entitlement kind.
Source entitlements with different identities MUST coexist, including future grants and multiple grants from one source, when their establishment satisfies the value and effective-state validity rules below.

A source entitlement MAY belong to one subscription, one one-time purchase, or no purchased-state owner, but MUST NOT belong to both owner kinds.
Ownerless grants MAY represent explicitly supported administrative or system entitlements.
A grant's meaning and purchased-state ownership MUST remain unchanged after establishment; correcting either requires a distinct grant.

Every source-entitlement value MUST be a positive whole quantity no greater than `2**63 - 1`.
This explicit upper bound is developer-approved because source and materialized effective values use a durable signed-64-bit contract; without it, a source change could establish source state whose required effective state cannot be represented atomically.
A non-lifetime grant MUST have a finite effective period.
A lifetime grant does not semantically expire.

Revocation is the only lifecycle transition of an established grant.
It is terminal, takes effect at one evaluation time, and remains attributable to the benefit transaction that caused it.

Effective entitlement intervals are half-open: their activation is inclusive and their expiration is exclusive.
At most one effective interval MAY cover one user and entitlement kind at any time.
Absence of a covering interval means that entitlement is not granted.

## Domain behavior

### Grant establishment

A grant whose effective period has already ended MAY be established as source history but MUST be immediately inactive.

Repeating a grant with the same identity and meaning MUST have no additional effect.
This remains true after that grant has been revoked and MUST NOT reactivate it.
Reusing the identity with a different meaning MUST fail without changing entitlement state.

### Revocation

Revoking an existing grant MUST make it permanently inactive from the workflow's evaluation time.
Revoking an already revoked grant MUST have no additional effect and MUST preserve the meaning of the original revocation.
Attempting to revoke a missing grant MUST fail without changing entitlement state.

A subscription-owned revocation MUST revoke every unrevoked grant belonging to that subscription, including grants whose effective periods have ended.
A one-time-purchase-owned revocation MUST apply the same rule within that purchase's ownership scope.
An owner-scoped revocation MUST leave grants belonging to every other purchased-state owner unchanged and MUST have no effect when its owner has no unrevoked grants.

### Effective state

The effective state for one user and entitlement kind at any time MUST be derived from every source entitlement active at that time.
Daily and monthly token entitlements MUST use the largest active grant value, while lifetime token entitlements MUST use the sum of all active grant values.
The combined effective value MUST NOT exceed `2**63 - 1`.
A source change whose required combined value would exceed that bound MUST fail without changing source state, effective state, or audit history.
When no source entitlement is active, the entitlement MUST be not granted and have no effective value.

Periods without an active source entitlement MUST be absent from the effective timeline.
Adjacent periods with the same effective value MUST form one effective entitlement interval.

### Source-change consistency

Each grant or revocation that changes source state, its effective-state consequence, and its required audit evidence MUST succeed or fail together.
Failure MUST leave the prior source state, effective state, and audit history unchanged.

Competing source changes for the same user and entitlement kind MUST produce an outcome equivalent to one complete ordering of those changes, without losing a grant or deriving effective state from partial changes.
Every source change MUST use one evaluation time consistently for every time-dependent decision and effect.

### Effective-state retrieval

Callers MUST be able to determine whether any supported entitlement kind is effective for any user at a chosen evaluation time and, when granted, its value and effective interval.
Retrieval MUST NOT change entitlement state merely because time has passed.

## Audit records

Every source grant or revocation that changes source state MUST produce durable evidence of who initiated the change, which user's grant changed and why, and its effective-entitlement consequence.
The evidence and entitlement change MUST succeed or fail together.

Evidence MUST be produced even when source state changes without changing the effective entitlement.
A failed change or a request with no additional effect MUST NOT produce audit evidence.

## Business events

Every successful source change MUST notify consumers of both the resulting source grant and its effective-entitlement consequence for the affected user.
The notification MUST describe the effective outcome even when it did not change.

Notification MUST occur only after the entitlement change and its audit evidence are durable.
An unsuccessful change or a request with no additional effect MUST NOT produce notification.
Delivery failure MUST NOT alter durable entitlement state, and an idempotent retry MUST NOT replay notification for the earlier change.

Time passage and effective-state retrieval MUST NOT produce business events.
