# One-time purchases module

## Goal of the document

This document describes the responsibility and observable one-time-purchase behavior of the `ffun.one_time_purchases` backend module.

## Scope

This specification applies to provider-independent purchased state and provider-to-local purchase identity associations managed by `ffun.one_time_purchases`.
The following adjacent concerns are outside the module's responsibility:

- payment-provider communication and commerce workflows.
- provider objects other than purchase identities.
- benefit definition.
- entitlement derivation or application.

## Dictionary

- `provider purchase identity` - the identity assigned by an external purchase authority, including the provider and account context needed to distinguish one purchase unambiguously.
- `provider purchase reference` - the immutable association between one provider purchase identity and one internal one-time-purchase identity.
- `purchase state` - the current provider-independent understanding of one purchase at one provider update time.
- `purchase status` - one normalized provider-independent lifecycle category owned by this module.
- `lifetime applicable interval` - the benefit-bearing interval derived from the purchase time and the project's stable lifetime interval-end marker.

## Module responsibility

The module owns:

- provider-independent one-time-purchase state.
- internal purchase identities.
- provider purchase references.
- normalized lifecycle meanings and their benefit-granting semantics.
- the lifetime applicable interval.
- the rules for accepting authoritative state.
- current-state retrieval semantics.

The external purchase authority owns commercial purchase truth, while `ffun.benefits` owns benefit-transaction and entitlement-application decisions.

Callers MUST use the module's domain boundary for one-time-purchase state and provider purchase references and MUST respect its decisions about:

- ownership.
- freshness.
- replacement.
- lifecycle.
- the applicable interval.

The module MUST NOT independently:

- infer provider-side state transitions.
- derive benefit identity from provider products.
- apply entitlement grants.
- define resource limits.
- make access decisions.

## Special module rules

One-time-purchase-state acceptance MUST participate in the atomic purchased-state workflow owned by `ffun.benefits`, and provider-reference effects MAY participate when that workflow selects a purchase from a provider identity.
The module MUST keep its state and required audit evidence bound to that workflow's outcome and MUST respect the workflow's decisions about the causal benefit transaction and entitlement effects.
This participation MUST remain limited to one-time-purchase-owned state and effects and MUST NOT transfer ownership of purchase policy to `ffun.benefits` or ownership of benefit and entitlement policy to `ffun.one_time_purchases`.

## Domain model

### One-time purchases

A one-time purchase is the current provider-independent representation of one purchase reported by an external purchase authority.
Each purchase MUST have one unique and stable internal identity that is independent of its provider purchase identity.

Each purchase MUST belong to exactly one Feeds Fun user, and that ownership MUST remain immutable.
A user MAY own multiple purchases, and purchases with different internal identities MUST remain independent.

The current purchase state MUST identify the configured benefit associated with the provider-reported purchase and the benefit transaction that causally established or most recently advanced that state.
The benefit association MUST remain immutable after the purchase is established, and the module MUST accept it from a trusted workflow rather than infer it from provider product data.

At most one current state MAY exist for one internal purchase identity.
That state MUST preserve the normalized and provider-reported lifecycle meanings and the authoritative purchase and update times needed to interpret its current status, lifetime applicable interval, and freshness.

### Provider purchase references

A provider purchase reference associates one complete and unambiguous provider purchase identity with one internal purchase identity.
One provider purchase identity MUST refer to at most one internal purchase, and one internal purchase MUST have at most one provider purchase reference.
The association MUST remain immutable after it is established.

### Purchase statuses

The normalized purchase statuses form an intentionally closed set:

- `pending` means that the purchase has been initiated but has not completed.
- `completed` means that the external authority reports the purchase successfully completed.
- `refunded` means that the external authority reports the purchase fully refunded.
- `reversed` means that the external authority reports the completed payment reversed.
- `disputed` means that the external authority reports the purchase disputed or otherwise contested.

The meaning of an assigned status MUST remain stable.
Only the `completed` status grants the purchase's configured benefits.
The `pending`, `refunded`, `reversed`, and `disputed` statuses do not grant those benefits.

Every purchase state MUST preserve both one normalized status and the non-empty provider status from which it was obtained.
Provider statuses are open-ended external descriptions and MUST NOT be constrained to a provider-specific closed set by this module.

### Lifecycle observations

Every purchase state MUST establish when the purchase originated according to the external authority and the provider update time.
Both times MUST identify unambiguous instants, and the purchase time MUST precede the project's stable lifetime interval-end marker.

The purchase's applicable interval MUST begin at its purchase time and end at the project's stable lifetime interval-end marker.
A benefit transaction's effective time MUST NOT replace the purchase time as the interval start.

## Domain behavior

### Provider purchase references

Establishing a missing provider purchase reference MUST preserve its one-to-one association.
Repeating the same association MUST have no additional effect.
Attempting to associate either identity with a different counterpart MUST fail without changing the existing association.

Callers MUST be able to resolve one exact provider purchase identity to its associated internal purchase identity, with absence reported when no reference exists.
Resolution MUST have no domain effects.

Provider adapters and higher-level workflows MUST resolve and establish provider purchase references through this module's domain boundary.
They MUST NOT reproduce provider-to-local purchase identity behavior.

### State acceptance and causality

Proposed purchase state MUST be complete and valid before it has any effect.
Invalid proposed-purchase information in any of the following areas MUST fail without changing current state:

- ownership.
- benefit association.
- lifecycle.
- status.
- timing.

Accepting the first state for an internal purchase identity MUST establish its complete current state and causal benefit transaction.
Reusing an existing internal identity for another user or benefit MUST fail without changing current state.

State with a provider update time earlier than the current state MUST have no effect.
State with the same provider update time and the same business state MUST have no additional effect.
State with the same provider update time but different business state MUST fail as an ambiguous authoritative conflict.

Newer state with different business state MUST replace the complete mutable business state and advance the provider update time and causal benefit transaction.
When only the provider update time differs, accepting newer state MUST advance its freshness and causal benefit transaction without treating the acceptance as a business-state change.
State that has no effect because it is older or identical MUST preserve the existing causal benefit transaction.

The current state and its causal benefit transaction MUST change atomically.
Competing proposals for one purchase MUST produce an outcome consistent with authoritative freshness, and older state MUST NOT overwrite newer state.
Callers MUST be able to distinguish the following outcomes so the owning workflow can apply the corresponding domain effects:

- creation.
- business-state change.
- freshness-only acceptance.
- identical-state no-op.
- older-state no-op.

### Status and time semantics

Any normalized status transition MUST be accepted when it belongs to newer valid authoritative state.
The module MUST NOT reject a transition merely because it would be unusual for a particular provider.

The benefit workflow MUST respect the module's benefit-granting status meaning when determining entitlement effects.
Other callers making access decisions MUST use the domain that owns those decisions rather than infer access directly from purchase state.

Time passage alone MUST NOT change stored purchase state or status.

### Current-state retrieval

Callers MUST be able to retrieve the complete current state for one exact internal purchase identity, with absence reported when the identity is unknown.
They MUST also be able to retrieve every current purchase for one user.

Retrieval by user MUST support restriction to selected normalized statuses.
Selecting no statuses MUST produce no purchases, while applying no status restriction MUST include every status.

Purchases for one user MUST be ordered by purchase time descending and then by internal purchase identity ascending.
Retrieval MUST have no domain effects and MUST NOT produce audit evidence or business events.

## Audit records

Every purchase creation or business-state change MUST produce durable audit evidence sufficient to explain the accepted purchase-state change.

The purchase change and its audit evidence MUST succeed or fail together.
A failed change MUST leave both the prior purchase state and its audit history unchanged.

The following cases MUST NOT produce audit evidence:

- advancing only authoritative freshness and causality.
- accepting state with no additional effect.
- establishing a provider purchase reference.
- a failed request.
- retrieval.

## Business events

Every successful purchase creation or business-state change MUST notify consumers of the purchase-state change.

Notification MUST occur only after the purchase state and required audit evidence are durable.
The following cases MUST NOT produce notification:

- advancing only authoritative freshness and causality.
- accepting state with no additional effect.
- establishing a provider purchase reference.
- a failed request.
- retrieval.

Notification delivery is best-effort and failure MUST NOT alter durable purchase or audit state.
Repeating an idempotent request MUST NOT replay notification for the earlier change.
