# Benefits module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.benefits` backend module.

## Scope

This specification covers the caller-visible `ffun.benefits` responsibility for provider-independent product benefits associated with purchased states.

Payment-service-provider communication, product and price catalogs, checkout, invoices, purchased-state identity and lifecycle behavior, and persistence rules internal to purchased-state owners and entitlements are out of scope.

## Dictionary

- `benefit identifier` - a stable local non-empty identifier that provider metadata or another trusted caller uses to select one configured package.
- `benefit package` - configured user-facing title and description together with the entitlement guarantees sold as one product benefit.
- `transaction source identity` - the `source_id` and `source_transaction_id` tuple that identifies one durable operation at its origin.
- `transaction effective time` - the source-reported timestamp associated with the management operation recorded by a benefit transaction; it is retained as ledger provenance and does not schedule entitlement revocation.
- `entitlement action` - the provider-independent grant or revoke decision derived from the normalized subscription status and persisted by the benefit transaction.
- `internal subscription identifier` - the generated UUID that identifies one provider-independent subscription projection.

## Module responsibility

The module MUST own benefit-package configuration, benefit lookup by stable local identifier, benefit-transaction persistence and idempotency, translation of subscription benefit-granting semantics into entitlement actions, and atomic coordination of subscription and entitlement state.

Provider adapters and other trusted callers MUST resolve a benefit identifier from authoritative metadata and supply one complete normalized subscription snapshot.
The benefits module MUST derive the entitlement action from the supplied normalized subscription status's benefit-granting semantic.
Callers MUST NOT select a grant or revoke transaction type independently of that state.
The supplied subscription snapshot MUST be authoritative for the benefit identifier and current subscription period.

The module MUST NOT communicate with a provider or maintain a second mapping from provider product or price identifiers to benefits.
It MUST NOT own provider prices, currencies, amounts, tax behavior, billing periods, or checkout configuration.

The subscriptions module owns internal subscription identities, provider-subscription references, the persisted current benefit identifier, and the benefit-granting semantics of normalized statuses, but does not copy benefit details or apply entitlement changes.
The entitlements module owns source and effective entitlement state.
Callers MUST use the benefits workflow instead of independently recording one causal transaction across those modules.

## Domain behavior

### Benefit packages

Each benefit package MUST have one stable non-empty identifier, one non-empty user-facing title, one user-facing description, and zero or more entitlement guarantees.
Package identifiers MUST be unique in configuration.
Guarantee entitlement kinds MUST be unique within one package, and each guarantee value MUST be an integer.

Benefit configuration MUST NOT contain a revision number.
A configured package is the current desired entitlement definition for every granting subscription that references its benefit identifier.
The title, description, and guarantees of an existing package MAY change without introducing a new benefit identifier.
Such a configuration change MUST NOT mutate benefit transactions, subscriptions, or entitlements by itself.
It becomes effective for an existing subscription only when a newly identified benefit transaction actualizes that subscription; until then, the previously persisted entitlement state remains authoritative.
Benefit transactions MUST record the stable benefit identifier and MUST NOT snapshot the package title, description, or complete guarantee set.
A benefit identifier MUST NOT be reused for an unrelated product and MUST remain configured while a current subscription can reference it.

Looking up an unknown benefit identifier MUST fail without changing benefit-transaction, subscription, or entitlement state.

### Entitlement-action derivation

The subscriptions module MUST determine whether each normalized status grants benefits.
The benefits module MUST translate a benefit-granting status to the `grant` action and a non-benefit-granting status to the `revoke` action.
Accordingly, the resulting status-to-action mapping MUST be:

- `trialing`, `active`, and `past_due` MUST produce the `grant` action.
- `pending`, `paused`, and `ended` MUST produce the `revoke` action.

The action describes the desired entitlement state resulting from the complete subscription snapshot.
It is not an instruction to reverse an earlier benefit transaction.
A `grant` action MAY revoke superseded subscription-owned entitlement rows before granting the current package.
A `revoke` action MUST leave the subscription with no active or future subscription-owned entitlements and MUST NOT identify or reverse one historical transaction.

The derived action MUST be persisted in the immutable benefit transaction so historical operations retain the policy decision made when they were accepted.
Changing the status-to-action policy later MUST NOT reinterpret existing benefit transactions.

### Subscription selection

A subscription application MUST require a non-empty benefit identifier on the supplied subscription snapshot.
The workflow MAY accept a complete provider subscription identity to select an internal subscription.
It MUST resolve and persist that mapping through the subscriptions public domain boundary.
It MUST NOT persist or reproduce provider-subscription reference behavior inside benefits persistence.

Benefit transactions MUST NOT contain provider identifiers.
Provider customer and product identifiers are inputs to provider-adapter decisions and MUST NOT be accepted or persisted by the benefits module.
The source-owned operation record remains responsible for provider payloads and diagnostic provenance.

The trusted caller MUST include the benefit identifier obtained from provider-owned product metadata.
Configured titles, descriptions, and entitlement guarantees MUST remain locally authoritative and MUST NOT be accepted as provider-supplied display data.

### Benefit transactions

Each benefit transaction accepted by the module MUST have an internally generated UUID, one transaction source identity, one derived entitlement action, one user, one benefit identifier, one internal subscription identifier, one effective time, and the subscription period start and end copied from its supplied subscription snapshot.
The source identifier MUST be a stable integer identifying the source subsystem.
The source transaction identifier MUST be a UUID identifying a durable source-owned operation, not an identifier generated independently for each retry or webhook delivery attempt.
For example, a Stripe adapter may supply the UUID of its persisted webhook record while retaining the original Stripe event identifier and payload in that record.
Local subscription identity MUST be represented directly by the internal subscription identifier and MUST NOT be encoded as a generic target kind and target identifier pair.
A future purchase workflow MUST introduce a distinct purchase identifier rather than generalizing the subscription relationship.

The supported entitlement actions and stable values MUST be:

- `grant`, stable value `1`, which makes the configured package the subscription's complete desired entitlement state.
- `revoke`, stable value `2`, which makes the subscription's complete desired entitlement state empty.

Assigned values MUST NOT be changed or reused.

The exact `source_id` and `source_transaction_id` tuple MUST be unique.
Trusted callers MUST guarantee that a source identity permanently identifies exactly one logical operation and MUST NOT reuse it for different transaction data.
The first accepted transaction for a source identity MUST remain authoritative.
Repeating a source identity MUST return the previously generated internal transaction identifier and MUST be a no-op regardless of the transaction data supplied by the repeated request.
An overlapping attempt that loses the race to accept the same previously unseen source identity MUST fail with a benefit transaction concurrency error.
Retrying after the winner commits MUST return the stored transaction normally.

Benefit transactions MUST be append-only and MUST NOT be updated or deleted by normal workflows.

### Subscription actualization

Every newly accepted transaction MUST apply the supplied subscription snapshot and actualize the complete set of entitlements owned by that subscription.
The benefits module MUST NOT provide a subscription-only command that can persist a subscription snapshot without considering its entitlements.
A transaction whose supplied snapshot produces the `stale` subscription save outcome MUST fail with a stale-benefit-transaction error and roll back the benefit transaction and every other change in the workflow.
The stale source identity MUST NOT be persisted as an accepted benefit transaction.
Actualization MUST run when the subscriptions module produces the `same` or `refreshed` save outcome even though the supplied snapshot did not change the persisted subscription business state.
Repeating an already accepted transaction source identity MUST remain an idempotent no-op and MUST NOT actualize the subscription again; a maintenance or mass actualization MUST use a new source transaction identity.

Actualization MUST revoke every subscription-owned entitlement that is active at the evaluation time or can become active afterward.
It MUST ignore entitlements whose effective lifetime ended before the evaluation time.
For both `grant` and `revoke` actions, existing entitlements MUST be revoked immediately at the workflow's evaluation time because revocation is a completed terminal transition rather than a planned subscription-period boundary.
The benefit transaction's effective time MUST remain recorded in the benefit ledger for causal provenance and MUST NOT be used as the source entitlement's revocation time.
For a `grant` action, the replacement package MUST still be granted from the supplied subscription period start.
Each revoked source entitlement MUST retain its original grant transaction identifier and record the newly accepted benefit transaction as its revoking transaction identifier.
The superseded source-entitlement grants MUST remain immutable except for their revocation state and audit history.

For a `grant` action, the workflow MUST then resolve the current configured package recorded by the transaction and create one source entitlement for every package guarantee.
Every resulting source entitlement MUST use `benefits` as its semantic entitlement source, the internal benefit transaction UUID as its grant transaction identifier, and the internal subscription identifier as its subscription owner.
The originating PSP, administrator, support tool, or system component MUST remain identifiable through the corresponding benefit transaction's source identity and source-owned operation record.
All non-lifetime guarantees MUST use the accepted transaction's persisted subscription period.
Lifetime guarantees MUST use `period_starts_at` and the project's stable lifetime interval-end marker.

For a `revoke` action, the workflow MUST NOT create source entitlements after revoking the subscription-owned state.
A revoke action for a subscription without current or future source entitlements MUST succeed with an empty entitlement-change result.

### Subscription application

Every transaction accepted by `apply_subscription_transaction` MUST be associated with one internal subscription identifier.
The command MUST select the subscription by supplying an existing internal subscription identifier, supplying a complete provider subscription identity, or explicitly requesting a new subscription.
For a transaction with a provider subscription identity, the workflow MUST resolve the internal subscription through the subscriptions module's dedicated provider-subscription reference; when no reference exists, it MUST generate a new internal subscription identifier and ask the subscriptions module to persist the reference atomically.
When the command explicitly requests a new subscription, the workflow MUST generate a new internal subscription identifier and MUST reuse it when the same source transaction is retried.
One provider subscription identity MUST NOT resolve to multiple internal subscriptions.
The source identity constraint MUST prevent concurrent retries from applying one operation more than once.
The workflow MAY reject one of two distinct operations that concurrently attempt to create the same previously unknown provider subscription reference.

For each newly accepted benefit transaction, the workflow MUST resolve the configured package, derive and persist the entitlement action, and apply the supplied subscription snapshot through the subscriptions domain boundary.
A stale snapshot MUST fail and roll back because an obsolete snapshot cannot authorize replacement of the subscription's entitlement state.

The benefit transaction, subscription snapshot, changed source entitlements, derived effective entitlement intervals, and all required audit records MUST commit or roll back as one unit.
Changes for the same transaction source identity, internal subscription identity, and affected user and entitlement kind MUST retain the serialization guarantees of the participating modules.

The `ffun.benefits.apply_subscription_transaction` workflow is explicitly approved as the owner of one database transaction that includes benefit-transaction persistence, subscription persistence, and entitlement persistence.
Within that transaction, it MAY pass its execute callable to the subscription-reference and subscription-save operations exposed by `ffun.subscriptions`, and to the grant and subscription-revocation operations exposed by `ffun.entitlements`.
This exception applies only to this benefits subscription-application workflow.
The workflow MUST call both modules through their public domain boundaries and MUST NOT import their operation modules or access their tables directly.

Business events from participating modules MUST be emitted only after the shared transaction commits.
The workflow MUST collect the callbacks returned by transaction-participating subscription and entitlement operations and begin invoking them only after that commit.
Any failure before commit MUST leave the previous transaction ledger, subscription, source entitlements, effective entitlements, and audit history unchanged and MUST emit no events.
Callback invocation is best-effort post-commit delivery: a callback failure MUST NOT roll back or otherwise invalidate the already committed state.
One callback failure MAY prevent the workflow from invoking callbacks that remain in the collection.
The workflow does not guarantee durable callback replay, and retrying an already accepted transaction source identity MUST NOT replay callbacks from the original application.

## Public interface

The public interface MUST provide these operations:

- `has_benefit` reports whether one benefit identifier has a configured package.
- `get_benefit` returns one configured package for a benefit identifier and fails when the identifier is unknown.
- `get_benefit_transaction` returns one benefit transaction for an internal transaction identifier, or no value when it is unknown.
- `apply_subscription_transaction` atomically records one subscription-related benefit transaction and applies one complete subscription snapshot.

`apply_subscription_transaction` MUST accept one complete provider-neutral subscription snapshot, one neutral benefit transaction command, and the audit actor.
The command MUST contain the `source_id` and `source_transaction_id` transaction identity, subscription selection, and effective time.
It MUST NOT contain a caller-selected entitlement action or a historical transaction to revoke.
A stale snapshot MUST raise a benefits-owned stale-benefit-transaction error containing the selected subscription identity and the incoming and current provider update times.

The result MUST contain the internal benefit transaction identifier, the internal subscription identifier, and whether the transaction was newly created.
An idempotent transaction retry MUST report that the transaction was not created because its original atomic effects already committed.

## Audit records

The module does not define an additional audit event.
The immutable benefit transaction records the source-owned operation reference and derived entitlement action, while its application MUST cause subscriptions and entitlements to append their specified audit records inside the shared transaction for every corresponding non-no-op state change.

## Business events

The module does not define an additional business event.
After commit, its subscription application MUST attempt to cause subscriptions and entitlements to emit their specified events for every corresponding non-no-op state change.
That delivery is best-effort: callback failure does not invalidate committed state, and this module does not provide durable replay.
