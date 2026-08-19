# Benefits module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.benefits` backend module.

## Scope

This specification covers configured user-facing benefit packages, the immutable ledger of accepted benefit transactions, and the workflow that applies a benefit transaction to subscription and entitlement state.

Payment-service-provider communication, product and price catalogs, checkout, invoices, and the persistence rules internal to subscriptions and entitlements are out of scope.
Applying benefits to one-time purchases is also out of scope until a purchase-owning workflow exists, but benefit packages and benefit transactions MUST remain reusable by that future workflow.

## Dictionary

- `benefit identifier` - a stable local non-empty identifier that provider metadata or another trusted caller uses to select one configured package.
- `benefit package` - configured user-facing title and description together with the entitlement guarantees sold as one product benefit.
- `entitlement guarantee` - one entitlement kind and integer value promised by a benefit package.
- `benefit transaction` - one immutable, accepted business operation that grants a package or revokes an earlier grant while recording the associated subscription state.
- `benefit transaction identifier` - the internally generated UUID that canonically identifies one benefit transaction.
- `transaction source identity` - the `source_id` and `source_transaction_id` tuple that identifies one durable operation at its origin.
- `internal subscription identifier` - the generated UUID that identifies one provider-independent subscription projection.
- `grant transaction to revoke` - the earlier benefit grant transaction targeted by a benefit revocation transaction.

## Module responsibility

The module MUST own benefit-package configuration, benefit lookup by stable local identifier, benefit-transaction persistence and idempotency, and atomic coordination of subscription state with explicitly requested grant or revocation operations.

Provider adapters and other trusted callers MUST resolve a benefit identifier from authoritative metadata and explicitly classify each accepted operation as a benefit grant or benefit revocation by choosing the corresponding command type.
The supplied subscription snapshot MUST be authoritative for both the benefit identifier and the current subscription period.
The module MUST NOT infer a grant or revocation from a subscription status.

The module MUST NOT communicate with a provider or maintain a second mapping from provider product or price identifiers to benefits.
It MUST NOT own provider prices, currencies, amounts, tax behavior, billing periods, or checkout configuration.

The subscriptions module owns internal subscription identities, provider-subscription references, and the persisted current benefit identifier but does not copy benefit details.
The entitlements module owns source and effective entitlement state.
Callers MUST use the benefits workflow instead of independently recording one causal transaction across those modules.

## Domain behavior

### Benefit packages

Each benefit package MUST have one stable non-empty identifier, one non-empty user-facing title, one user-facing description, and zero or more entitlement guarantees.
Package identifiers MUST be unique in configuration.
Guarantee entitlement kinds MUST be unique within one package, and each guarantee value MUST be an integer.

Benefit configuration MUST NOT contain a revision number.
A configured package is the current desired entitlement definition for every subscription that references its benefit identifier.
The title, description, and guarantees of an existing package MAY change without introducing a new benefit identifier.
Such a configuration change MUST NOT mutate benefit transactions, subscriptions, or entitlements by itself.
It becomes effective for an existing subscription only when a newly identified benefit transaction actualizes that subscription; until then, the previously persisted entitlement state remains authoritative.
Benefit transactions MUST record the stable benefit identifier and MUST NOT snapshot the package title, description, or complete guarantee set.
A benefit identifier MUST NOT be reused for an unrelated product and MUST remain configured while a current subscription can reference it.

Looking up an unknown benefit identifier MUST fail without changing benefit-transaction, subscription, or entitlement state.

### Subscription selection

A subscription application MUST require a non-empty benefit identifier on the supplied subscription snapshot.
The workflow MAY accept a complete provider subscription identity to select an internal subscription.
It MUST resolve and persist that mapping through the subscriptions public domain boundary.
It MUST NOT persist or reproduce provider-subscription reference behavior inside the benefits module.

Benefit transactions MUST NOT contain provider identifiers.
Provider customer and product identifiers are inputs to provider-adapter decisions and MUST NOT be accepted or persisted by the benefits module.
The source-owned operation record remains responsible for provider payloads and diagnostic provenance.

The trusted caller MUST include the benefit identifier obtained from provider-owned product metadata.
Configured titles, descriptions, and entitlement guarantees MUST remain locally authoritative and MUST NOT be accepted as provider-supplied display data.

### Benefit transactions

Each benefit transaction currently accepted by the module MUST have an internally generated UUID, one transaction source identity, one stable transaction kind, one user, one benefit identifier, one internal subscription identifier, and one effective time.
A grant transaction MUST additionally persist the subscription period start and end copied from its supplied subscription snapshot.
The source identifier MUST be a stable `SMALLINT` identifying the source subsystem.
The source transaction identifier MUST be a UUID identifying a durable source-owned operation, not an identifier generated independently for each retry or webhook delivery attempt.
For example, a Stripe adapter may supply the UUID of its persisted webhook record while retaining the original Stripe event identifier and payload in that record.
Local subscription identity MUST be represented directly by the internal subscription identifier and MUST NOT be encoded as a generic target kind and target identifier pair.
A future purchase workflow MUST introduce a distinct purchase identifier rather than generalizing the subscription relationship.

The supported benefit transaction kinds and stable values MUST be:

- `grant`, stable value `2`, which grants every entitlement guarantee in one benefit package.
- `revoke`, stable value `3`, which revokes the guarantees created by one earlier grant transaction.

Assigned values MUST NOT be changed or reused.

The exact `source_id` and `source_transaction_id` tuple MUST be unique.
Trusted callers MUST guarantee that a source identity permanently identifies exactly one logical operation and MUST NOT reuse it for different transaction data.
The first accepted transaction for a source identity MUST remain authoritative.
Repeating a source identity MUST return the previously generated internal transaction identifier and MUST be a no-op regardless of the transaction data supplied by the repeated request.
If overlapping first attempts both pass the initial source lookup, the unique-key loser MUST fail with a benefit transaction concurrency error rather than loading the winner inside the same attempt.
Retrying after the winner commits MUST return the stored transaction normally.

Benefit transactions MUST be append-only and MUST NOT be updated or deleted by normal workflows.

### Grants and subscription actualization

A grant command MUST NOT contain a separate grant marker or entitlement interval.
Its command type MUST identify the operation as a grant.
The supplied subscription snapshot MUST contain timezone-aware `period_starts_at` and `period_ends_at` values with the start earlier than the end.
The accepted grant transaction MUST persist those values unchanged under the same field names.

Every newly accepted grant command MUST both apply the supplied subscription snapshot and actualize the complete set of entitlements owned by that subscription.
The benefits module MUST NOT provide a subscription-only command that can persist a subscription snapshot without considering its entitlements.
A grant whose supplied snapshot produces the `stale` subscription save outcome MUST fail with a stale-benefit-grant error and roll back the benefit transaction and every other change in the workflow.
The stale source identity MUST NOT be persisted as an accepted benefit transaction.
Actualization MUST run when the subscriptions module produces the `same` or `refreshed` save outcome even though the supplied snapshot did not change the persisted subscription business state.
Repeating an already accepted transaction source identity MUST remain an idempotent no-op and MUST NOT actualize the subscription again; a maintenance or mass actualization MUST use a new source transaction identity.

The workflow MUST resolve the current configured package recorded by the grant transaction and create one source entitlement for every package guarantee as the subscription's resulting desired entitlement state.
Every resulting source entitlement MUST use `benefits` as its semantic entitlement source and the internal benefit transaction UUID as its grant transaction identifier.
The originating PSP, administrator, support tool, or system component MUST remain identifiable through the corresponding benefit transaction's source identity and source-owned operation record.

All non-lifetime guarantees MUST use the accepted grant transaction's persisted subscription period.
Lifetime guarantees MUST use `period_starts_at` and the project's stable lifetime interval-end marker.
Actualization MUST replace prior entitlement state owned by the same subscription as required to make its current and future entitlement state match the newly accepted transaction.
Actualization MUST revoke every subscription-owned entitlement that is active at the evaluation time or can become active afterward.
It MUST ignore entitlements whose effective lifetime ended before the evaluation time.
The superseded source-entitlement grants MUST remain immutable except for their revocation state and audit history.

### Revocations

A revocation MUST be a new benefit transaction and MUST identify the internal benefit grant transaction it revokes.
The grant transaction to revoke MUST exist, MUST be a grant, and MUST belong to the same user and internal subscription.

The workflow MUST revoke every source entitlement owned by the benefits source and the original grant transaction identifier at the revocation transaction's effective time.
It MUST discover those historical grants through the entitlements public domain boundary and MUST NOT resolve current benefit-package configuration to reconstruct the original guarantee kinds.
Each changed source entitlement MUST retain the original transaction as its grant transaction identifier and record the new revocation transaction as its revoking transaction identifier.
The original grant transaction and its immutable entitlement grant values and interval MUST retain their identities.

Revoking an already revoked grant MAY record another idempotent causal benefit transaction but MUST NOT change the preserved entitlement revocation time.
A grant with no source entitlements MUST produce an empty entitlement-revocation result because benefit packages MAY contain no guarantees.

### Subscription application

Every transaction accepted by `apply_subscription_transaction` MUST be associated with one internal subscription identifier.
The command MUST select the subscription by supplying an existing internal subscription identifier, supplying a complete provider subscription identity, or explicitly requesting a new subscription.
For a revocation, the command MUST NOT request a new subscription, and the selected subscription MUST match the grant transaction being revoked.
For another transaction with a provider subscription identity, the workflow MUST resolve the internal subscription through the subscriptions module's dedicated provider-subscription reference; when no reference exists, it MUST generate a new internal subscription identifier and ask the subscriptions module to persist the reference atomically.
When the command explicitly requests a new subscription, the workflow MUST generate a new internal subscription identifier and MUST reuse it when the same source transaction is retried.
One provider subscription identity MUST NOT resolve to multiple internal subscriptions.
The source identity constraint MUST prevent concurrent retries from applying one operation more than once.
The initial implementation MAY reject one of two different operations concurrently creating the same provider subscription reference; it need not serialize this unlikely race until provider-identity locking is required in practice.

For each newly accepted benefit transaction, the workflow MUST apply the supplied subscription snapshot through the subscriptions domain boundary.
A new grant MUST resolve the package and entitlement interval from that same snapshot.
A new grant MUST fail and roll back when the subscriptions module reports that its supplied snapshot is stale, because an obsolete snapshot cannot authorize replacement of the subscription's entitlement state.
A new revocation transaction MUST still apply its targeted entitlement revocation when the supplied subscription snapshot is stale, because subscription freshness and revocation of an explicitly identified historical grant are separate decisions.

The benefit transaction, subscription snapshot, changed source entitlements, derived effective entitlement intervals, and all required audit records MUST commit or roll back as one unit.
Changes for the same transaction source identity, internal subscription identity, and affected user and entitlement kind MUST retain the serialization guarantees of the participating modules.

The `ffun.benefits.apply_subscription_transaction` workflow is explicitly approved as the owner of one database transaction that includes benefit-transaction persistence, subscription persistence, and entitlement grant or revocation persistence.
Within that transaction, it MAY pass its execute callable to the subscription-reference and subscription-save operations exposed by `ffun.subscriptions`, and to the grant and revocation operations exposed by `ffun.entitlements`, including `ffun.entitlements.revoke_by_grant_transaction_id`.
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
- `apply_subscription_transaction` atomically applies one subscription-related benefit transaction and one complete subscription snapshot.

`apply_subscription_transaction` MUST accept one complete provider-neutral subscription snapshot, one grant or revocation command, and the audit actor.
Both command types MUST contain the `source_id` and `source_transaction_id` transaction identity, subscription selection, and effective time.
The concrete command type MUST identify the operation without a separate kind or effect marker; a revocation command MUST additionally contain the grant transaction identifier to revoke.
A stale grant MUST raise a benefits-owned stale-benefit-grant error containing the selected subscription identity and the incoming and current provider update times.

The result MUST contain the internal benefit transaction identifier, the internal subscription identifier, and whether the transaction was newly created.
An idempotent transaction retry MUST report that the transaction was not created because its original atomic effects already committed.

## Audit records

The module does not define an additional audit event.
The immutable benefit transaction records the source-owned operation reference, while its application MUST cause subscriptions and entitlements to append their specified audit records inside the shared transaction for every corresponding non-no-op state change.

## Business events

The module does not define an additional business event.
After commit, its subscription application MUST attempt to cause subscriptions and entitlements to emit their specified events for every corresponding non-no-op state change.
That delivery is best-effort: callback failure does not invalidate committed state, and this module does not provide durable replay.
