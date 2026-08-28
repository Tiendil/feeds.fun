# Subscriptions module

## Goal of the document

This document describes the responsibility and observable subscription behavior of the `ffun.subscriptions` backend module.

## Scope

This specification applies to provider-independent purchased-subscription state and provider-to-local subscription identity associations managed by `ffun.subscriptions`.
The following adjacent concerns are outside the module's responsibility:

- payment-provider communication and commerce workflows.
- provider objects other than subscription identities.
- benefit definition.
- entitlement derivation or application.

## Dictionary

- `provider subscription identity` - the identity assigned by an external subscription authority, including the provider and account context needed to distinguish one subscription unambiguously.
- `provider subscription reference` - the immutable association between one provider subscription identity and one internal subscription identity.
- `subscription state` - the current provider-independent understanding of one purchased subscription at one provider update time.
- `subscription status` - one normalized provider-independent lifecycle category owned by this module.
- `alive subscription` - a subscription whose normalized status and end time indicate that it has not ended at the evaluation time.
- `subscription period` - the current benefit-bearing period reported for a subscription.
- `expected renewal` - an optional provider-reported expectation of renewal rather than a renewal scheduled or managed by this module.

## Module responsibility

The module owns:

- provider-independent subscription state.
- internal subscription identities.
- provider subscription references.
- normalized lifecycle meanings.
- the rules for accepting authoritative state.
- current-state retrieval semantics.

The external subscription authority owns commercial subscription truth, while `ffun.benefits` owns benefit-transaction and entitlement-application decisions.

Callers MUST use the module's domain boundary for subscription state and provider subscription references and MUST respect its decisions about:

- ownership.
- freshness.
- replacement.
- lifecycle.

The module MUST NOT independently:

- infer provider-side state transitions.
- derive benefit identity from provider products.
- apply entitlement grants.
- define resource limits.
- make access decisions.

## Special module rules

Subscription-state acceptance MUST participate in the atomic purchased-state workflow owned by `ffun.benefits`, and provider-reference effects MAY participate when that workflow selects a subscription from a provider identity.
The module MUST keep its state and required audit evidence bound to that workflow's outcome and MUST respect the workflow's decisions about the causal benefit transaction and entitlement effects.
This participation MUST remain limited to subscription-owned state and effects and MUST NOT transfer ownership of subscription policy to `ffun.benefits` or ownership of benefit and entitlement policy to `ffun.subscriptions`.

## Domain model

### Subscriptions

A subscription is the current provider-independent representation of one purchased subscription reported by an external subscription authority.
Each subscription MUST have one unique and stable internal identity that is independent of its provider subscription identity.

Each subscription MUST belong to exactly one Feeds Fun user, and that ownership MUST remain immutable.
A user MAY own multiple subscriptions, and subscriptions with different internal identities MUST remain independent.

The current subscription state MUST identify the configured benefit associated with the provider-reported purchase and the benefit transaction that causally established or most recently advanced that state.
The benefit association MAY change when newer authoritative state moves the subscription to another product, but the module MUST accept the association from a trusted workflow rather than infer it from provider product data.

At most one current state MAY exist for one internal subscription identity.
That state MUST preserve the normalized and provider-reported lifecycle meanings and the authoritative timing observations needed to interpret:

- the subscription's current period.
- its renewal expectation.
- its end.
- its freshness.

### Provider subscription references

A provider subscription reference associates one complete and unambiguous provider subscription identity with one internal subscription identity.
One provider subscription identity MUST refer to at most one internal subscription, and one internal subscription MUST have at most one provider subscription reference.
The association MUST remain immutable after it is established.

### Subscription statuses

The normalized subscription statuses form an intentionally closed set:

- `pending` means that the subscription is not yet commercially active but may still become active.
- `trialing` means that the subscription is in a provider-recognized trial period.
- `active` means that the provider reports the subscription in good standing.
- `past_due` means that the provider reports an overdue but potentially recoverable subscription.
- `paused` means that the provider reports the subscription temporarily suspended.
- `ended` means that the provider reports the subscription ended and no longer current.

The meaning of an assigned status MUST remain stable.
The `trialing`, `active`, and `past_due` statuses grant the subscription's configured benefits.
The `pending`, `paused`, and `ended` statuses do not grant those benefits.

Every subscription state MUST preserve both one normalized status and the non-empty provider status from which it was obtained.
Provider statuses are open-ended external descriptions and MUST NOT be constrained to a provider-specific closed set by this module.

### Lifecycle observations

Every subscription state MUST establish when the subscription began, one current subscription period, and the provider update time.
The current period MUST begin before it ends and MUST have a finite end rather than represent lifetime validity.
Every lifecycle time MUST identify an unambiguous instant.

Expected renewal and subscription end MAY be absent.
When present, expected renewal MUST preserve an expectation reported by the external authority and MUST NOT be interpreted as a locally managed renewal schedule.
Expected renewal MUST be absent when the authority reports that no renewal is expected.
When present, the subscription end MUST represent either the scheduled end of a subscription that remains current or the actual end of an ended subscription and MUST be interpreted together with the normalized status.

## Domain behavior

### Provider subscription references

Resolving a provider subscription identity MUST return its existing internal subscription identity or establish and return a new internal identity when no reference exists.
Repeated or concurrent resolution of the same provider identity MUST converge on one internal identity and MUST NOT create multiple references.
The resolver MUST own internal identity creation; callers MUST NOT propose an internal identity for a provider subscription reference.

Callers that only inspect one exact provider subscription identity MUST be able to load its associated internal identity, with absence reported when no reference exists.
Inspection MUST have no domain effects.

Provider adapters and higher-level workflows MUST resolve provider subscription references through this module's domain boundary.
They MUST NOT reproduce provider-to-local subscription identity behavior.

### State acceptance and causality

Proposed subscription state MUST be complete and valid before it has any effect.
Invalid proposed-subscription information in any of the following areas MUST fail without changing current state:

- ownership.
- lifecycle.
- status.
- timing.

Accepting the first state for an internal subscription identity MUST establish its complete current state and causal benefit transaction.
Reusing an existing internal identity for another user MUST fail without changing current state.

State with a provider update time earlier than the current state MUST have no effect.
State with the same provider update time and the same business state MUST have no additional effect.
State with the same provider update time but different business state MUST fail as an ambiguous authoritative conflict.

Newer state with different business state MUST replace the complete mutable business state and advance the provider update time and causal benefit transaction.
When only the provider update time differs, accepting newer state MUST advance its freshness and causal benefit transaction without treating the acceptance as a business-state change.
State that has no effect because it is older or identical MUST preserve the existing causal benefit transaction.

The current state and its causal benefit transaction MUST change atomically.
Competing proposals for one subscription MUST produce an outcome consistent with authoritative freshness, and older state MUST NOT overwrite newer state.
Callers MUST be able to distinguish the following outcomes so the owning workflow can apply the corresponding domain effects:

- creation.
- business-state change.
- freshness-only acceptance.
- identical-state no-op.
- older-state no-op.

### Status and time semantics

Any normalized status transition MUST be accepted when it belongs to newer valid authoritative state.
The module MUST NOT reject a transition merely because it would be unusual for a particular provider.

Subscriptions in the following statuses are eligible to be alive:

- `pending`.
- `trialing`.
- `active`.
- `past_due`.
- `paused`.

An eligible subscription is alive at an evaluation time only when its end is absent or later than that time.
A subscription in `ended` status, or whose end is not later than the evaluation time, is not alive.

The benefit workflow MUST respect the module's benefit-granting status meaning when determining entitlement effects.
Other callers making access decisions MUST use the domain that owns those decisions rather than infer access directly from subscription state.

Time passage alone MUST NOT change stored subscription state.
It MAY change whether a subscription is alive once the recorded end is reached.

### Current-state retrieval

Callers MUST be able to retrieve the complete current state for one exact internal subscription identity, with absence reported when the identity is unknown.
They MUST also be able to retrieve every current subscription for one user, including ended subscriptions.

Retrieval by user MUST support restriction to selected normalized statuses.
Selecting no statuses MUST produce no subscriptions, while applying no status restriction MUST include every status.
Callers MUST be able to retrieve only the subscriptions that are alive at the query's evaluation time.

The benefits workflow MUST be able to retrieve every subscription identity associated with one benefit.
It MUST load each identified subscription and use the module's status and time semantics to determine whether that subscription can grant benefits at the evaluation time or later.
An eligible subscription MUST have a benefit-granting status, a current period ending after the evaluation time, and no subscription end at or before the evaluation time.
A current period beginning after the evaluation time MUST remain eligible.

Subscriptions for one user MUST be ordered by subscription start descending and then by internal subscription identity ascending.
Subscription identities retrieved for a benefit refresh MUST be ordered by internal subscription identity ascending.
Retrieval MUST have no domain effects and MUST NOT produce audit evidence or business events.

## Audit records

Every subscription creation or business-state change MUST produce durable audit evidence explaining the authorized subscription transition and its benefit-transaction causality.

The subscription change and its audit evidence MUST succeed or fail together.
A failed change MUST leave both the prior subscription state and its audit history unchanged.

The following cases MUST NOT produce audit evidence:

- advancing only authoritative freshness and causality.
- accepting state with no additional effect.
- a failed request.
- retrieval.

## Business events

Every successful subscription creation or business-state change MUST notify consumers of the subscription transition.

Notification MUST occur only after the subscription state and required audit evidence are durable.
The following cases MUST NOT produce notification:

- advancing only authoritative freshness and causality.
- accepting state with no additional effect.
- a failed request.
- retrieval.

Repeating an idempotent request MUST NOT replay notification for the earlier change.
