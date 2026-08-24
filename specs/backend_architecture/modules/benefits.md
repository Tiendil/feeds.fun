# Benefits module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.benefits` backend module.

## Scope

This specification covers the caller-visible `ffun.benefits` responsibility for provider-independent product benefits associated with subscription and one-time-purchase states.

Payment-service-provider communication, product and price catalogs, checkout, invoices, purchased-state identity and lifecycle behavior, and persistence rules internal to purchased-state owners and entitlements are out of scope.

## Dictionary

- `benefit parameter` - one named normalized integer value accepted by a benefit package template at materialization time.
- `benefit package template` - configured user-facing title and description, accepted benefit-parameter definitions, and the locally controlled mapping from entitlement kinds to constant or parameter-referenced values.
- `benefit package` - one concrete result of materializing a benefit package template with normalized benefit parameters; it contains only resolved entitlement guarantees.
- `package materialization` - deterministic validation and application of normalized benefit parameters to one configured benefit package template to produce one concrete benefit package.
- `transaction source identity` - the `source_id` and `source_transaction_id` tuple that identifies one durable operation at its origin.
- `transaction effective time` - the source-reported timestamp associated with the management operation recorded by a benefit transaction; it is retained as ledger provenance and does not schedule entitlement revocation.
- `entitlement action` - the provider-independent grant or revoke decision derived from the normalized purchased-state status and persisted by the benefit transaction.

## Module responsibility

The module MUST own benefit-package-template configuration, template lookup by stable local identifier, benefit-parameter validation, package materialization, benefit-transaction persistence and idempotency, translation of purchased-state benefit-granting semantics into entitlement actions, and atomic coordination of purchased and entitlement state.

Provider adapters and other trusted callers MUST resolve a benefit identifier and normalized benefit parameters from authoritative metadata and supply one complete normalized subscription or one-time-purchase snapshot.
The benefits module MUST derive the entitlement action from the supplied snapshot status's benefit-granting semantic.
Callers MUST NOT select a grant or revoke transaction type independently of that state.
Callers MUST NOT supply materialized entitlement guarantees.
Each supplied snapshot MUST be authoritative for its benefit identifier and purchased-state lifecycle data.

The module MUST NOT communicate with a provider or maintain a second mapping from provider product or price identifiers to benefits.
It MUST NOT own provider prices, currencies, amounts, tax behavior, billing periods, or checkout configuration.

The subscriptions module owns internal subscription identities, provider-subscription references, the persisted current benefit identifier, and the benefit-granting semantics of normalized statuses, but does not copy benefit details or apply entitlement changes.
The one-time-purchases module owns internal purchase identities, provider-purchase references, the persisted current benefit identifier, the benefit-granting semantics of normalized purchase statuses, and the lifetime applicable interval derived from purchase time, but does not copy benefit details, persist benefit parameters, or apply entitlement changes.
The entitlements module owns source and effective entitlement state.
Callers MUST use the benefits workflow instead of independently recording one causal transaction across those modules.

## Domain behavior

### Benefit package templates

Each benefit package template MUST have one stable non-empty identifier, one non-empty user-facing title, one user-facing description, zero or more parameter definitions, and a non-empty mapping from entitlement kinds to entitlement value templates.
Template identifiers MUST be unique in configuration.
Parameter identifiers MUST be non-empty and unique within one template.
Each parameter definition MUST declare one required inclusive minimum and one required inclusive maximum for its normalized integer value.

Each entitlement value template MUST be either one configured integer constant or one direct reference to a parameter declared by the same package template.
The template language MUST NOT allow callers to select entitlement kinds and MUST NOT contain general expressions or transformations.
Entitlement kinds MUST be unique by construction as mapping keys and MUST NOT be duplicated inside mapped values.
Package templates MUST make no token-specific assumption and MAY map any locally supported entitlement kind whose value contract is satisfied.

Configuration loading MUST reject duplicate template or parameter identifiers, parameter references to undeclared parameters, constants incompatible with their entitlement kinds, parameter definitions incompatible with the kinds that reference them, invalid or incomplete constraints, invalid constants, and declared parameters that are not referenced by any entitlement value template.
Benefits settings MUST expose configured templates as `package_templates`, not as already materialized packages.
An existing fixed package MUST be represented as a parameterless template whose entitlement mappings contain constants.

### Integer value constraints

Each parameter minimum and maximum MUST be a strict integer within the `ffun.entitlements` entitlement value range, and the minimum MUST NOT exceed the maximum.
Boolean, floating-point, string, and implicitly coerced constraint values MUST be invalid.
The complete declared parameter range MUST fit within the accepted source-grant bounds of every entitlement kind that references that parameter.

Every configured constant MUST be a strict integer within the accepted source-grant bounds of its mapped entitlement kind.
Template validation MUST enforce parameter-range and constant compatibility before the template becomes available for lookup or materialization.
Runtime parameter values and materialized guarantees MUST use the same kind-owned bounds rather than defining a second, wider benefits-specific value range.

### Package materialization and configuration evolution

Package materialization MUST resolve the configured template by benefit identifier and validate the complete supplied parameter collection.
The collection MUST supply each declared parameter exactly once and MUST contain no undeclared parameter.
An input representation capable of carrying duplicate parameter names MUST reject duplicates rather than selecting one value.
Each supplied value MUST be a strict integer within its declared inclusive bounds.
Boolean, floating-point, string, and implicitly coerced values MUST be rejected rather than normalized into integers.

Materialization MUST resolve every constant or parameter reference, validate each resolved integer against its entitlement kind, and return a concrete benefit package containing the template identifier, the normalized parameter mapping, and the fully resolved kind-keyed entitlement guarantees.
The result MUST contain no unresolved parameter references.
Materialization MUST be deterministic for the same validated template configuration and normalized parameter values.
A parameterless template MUST materialize only from an empty parameter collection.
Looking up or materializing an unknown benefit identifier MUST fail without changing benefit-transaction, purchased-state, or entitlement state.

Every previously unseen subscription or one-time-purchase benefit transaction MUST materialize the current configured template from the parameters supplied for that transaction.
This requirement applies whether the purchased-state status grants or revokes benefits.
An idempotent retry of an already accepted source identity MUST return the stored transaction result without resolving the template, validating parameters, or materializing a package again.

Benefit configuration MUST NOT contain a revision number.
The current template is the desired entitlement definition for every new transaction that references its benefit identifier.
Changing a template MUST NOT mutate existing benefit transactions, purchased-state snapshots, or entitlements by itself.
The change becomes effective for an existing purchased state only when a newly identified benefit transaction actualizes that state; until then, the previously persisted entitlement state remains authoritative.
Benefit transactions MUST record the stable benefit identifier and MUST NOT store supplied parameters or snapshot the template, materialized package, title, description, or complete guarantee set.
Source-entitlement records MUST remain authoritative for the concrete entitlement values and intervals actually granted or revoked by historical transactions.
Changing template display text MAY retain the same benefit identifier.
Incompatible changes to parameter names or entitlement bindings SHOULD use a new benefit identifier, and an old template MUST remain configured while provider records can still initiate transactions that reference it.
A benefit identifier MUST NOT be reused for an unrelated product.

### Entitlement-action derivation

Each purchased-state-owning module MUST determine whether each of its normalized statuses grants benefits.
The benefits module MUST translate a benefit-granting status to the `grant` action and a non-benefit-granting status to the `revoke` action.
For subscriptions, the resulting status-to-action mapping MUST be:

- `trialing`, `active`, and `past_due` MUST produce the `grant` action.
- `pending`, `paused`, and `ended` MUST produce the `revoke` action.

The one-time-purchases module MUST define the corresponding benefit-granting semantic for every normalized purchase status, and the benefits module MUST apply the same translation without reproducing that status policy.

The action describes the complete desired entitlement state owned by the selected subscription or one-time purchase after applying its supplied snapshot.
It is not an instruction to reverse an earlier benefit transaction.
A `grant` action MAY revoke entitlements superseded within that purchased-state owner's scope before granting the materialized package.
A `revoke` action MUST leave the selected subscription or one-time purchase with no active or future owned entitlements and MUST NOT identify or reverse one historical transaction.

The derived action MUST be persisted in the immutable benefit transaction so historical operations retain the policy decision made when they were accepted.
Changing the status-to-action policy later MUST NOT reinterpret existing benefit transactions.

### Purchased-state selection

#### Subscription selection

A subscription application MUST require a non-empty benefit identifier on the supplied subscription snapshot.
The workflow MAY accept a complete provider subscription identity to select an internal subscription.
It MUST resolve and persist that mapping through the subscriptions public domain boundary.
It MUST NOT persist or reproduce provider-subscription reference behavior inside benefits persistence.

The trusted caller MUST include the benefit identifier obtained from provider-owned product metadata.
The benefit parameters for a subscription transaction MUST be supplied separately from its subscription snapshot.

#### One-time-purchase selection

A one-time-purchase application MUST require a non-empty benefit identifier on the supplied purchase snapshot.
The workflow MAY accept a complete provider-purchase identity to select an internal one-time purchase.
It MUST resolve and persist that mapping through the one-time-purchases public domain boundary.
It MUST NOT persist or reproduce provider-purchase reference behavior inside benefits persistence.

The trusted caller MUST include the benefit identifier and normalized benefit parameters obtained from authoritative provider metadata or another trusted source record.
Benefit parameters MUST be supplied separately from the purchase snapshot and MUST NOT be persisted as purchase state.

#### Provider boundary

Benefit transactions MUST NOT contain provider identifiers.
Provider customer, product, subscription, and purchase identifiers are inputs to provider-adapter decisions and MUST NOT be accepted or persisted as benefit-transaction data.
The source-owned operation record remains responsible for provider payloads and diagnostic provenance.
Configured titles, descriptions, parameter bindings, and entitlement guarantees MUST remain locally authoritative and MUST NOT be accepted as provider-supplied package data.

### Benefit transactions

Each benefit transaction accepted by the module MUST have an internally generated UUID, one transaction source identity, one derived entitlement action, one user, one benefit identifier, one effective time, one applicable entitlement interval, and exactly one target identifier.
A subscription transaction MUST contain one internal subscription identifier and no one-time-purchase identifier.
A one-time-purchase transaction MUST contain one internal one-time-purchase identifier and no subscription identifier.
A transaction with no target or with both targets MUST be invalid.
Target identity MUST NOT be encoded as a generic target-kind and target-identifier pair.
The target kind MUST be derived from the populated target identifier and MUST NOT be duplicated as independent transaction data.

The source identifier MUST be a stable integer identifying the source subsystem.
The source transaction identifier MUST be a UUID identifying a durable source-owned operation, not an identifier generated independently for each retry or webhook delivery attempt.
For example, a Stripe adapter may supply the UUID of its persisted webhook record while retaining the original Stripe event identifier and payload in that record.

The applicable interval for a subscription transaction MUST be copied from its supplied subscription snapshot.
The applicable interval for a one-time-purchase transaction MUST be copied from its supplied purchase snapshot.
Its start MUST be the snapshot's purchase time and its end MUST be the project's stable lifetime interval-end marker.
Every lifetime entitlement MUST use the project's stable lifetime interval-end marker regardless of target type.

The transaction MUST NOT contain benefit parameters or a materialized package.
The corresponding application command MUST select exactly one target.
The corresponding application result MUST identify the applied transaction and selected internal target and report whether the transaction was newly created.

The supported entitlement actions and stable values MUST be:

- `grant`, stable value `1`, which makes the materialized package the selected purchased-state target's complete desired entitlement state.
- `revoke`, stable value `2`, which makes the selected purchased-state target's complete desired entitlement state empty.

Assigned values MUST NOT be changed or reused.

The exact `source_id` and `source_transaction_id` tuple MUST be unique.
Trusted callers MUST guarantee that a source identity permanently identifies exactly one logical operation and MUST NOT reuse it for different transaction data.
The first accepted transaction for a source identity MUST remain authoritative.
Repeating a source identity MUST return the previously generated internal transaction identifier and MUST be a no-op regardless of the transaction data supplied by the repeated request.
An overlapping attempt that loses the race to accept the same previously unseen source identity MUST fail with a benefit transaction concurrency error.
Retrying after the winner commits MUST return the stored transaction normally.

Benefit transactions MUST be append-only and MUST NOT be updated or deleted by normal workflows.

### Purchased-state actualization

Every newly accepted transaction MUST apply the supplied snapshot through its owning module and actualize the complete set of entitlements owned by the selected subscription or one-time purchase.
The benefits module MUST NOT provide a purchased-state-only command that can persist a subscription or purchase snapshot without considering its entitlements.
A transaction whose supplied snapshot is stale MUST fail with a benefits-owned stale-benefit-transaction error and roll back the benefit transaction and every other workflow change.
The stale source identity MUST NOT be persisted as an accepted benefit transaction.
Actualization MUST run when the owning module accepts an unchanged or freshness-only snapshot even though the supplied snapshot did not change persisted business state.
Repeating an already accepted transaction source identity MUST remain an idempotent no-op and MUST NOT actualize the purchased state again; maintenance or mass actualization MUST use a new source transaction identity.

Actualization MUST revoke every entitlement owned by the selected subscription or one-time purchase that is active at the evaluation time or can become active afterward.
It MUST ignore entitlements whose effective lifetime ended before the evaluation time.
For both `grant` and `revoke` actions, existing entitlements MUST be revoked immediately at the workflow's evaluation time because revocation is a completed terminal transition rather than a planned period boundary.
The benefit transaction's effective time MUST remain recorded in the benefit ledger for causal provenance and MUST NOT be used as the source entitlement's revocation time.
For a `grant` action, the replacement package MUST be granted from the applicable interval start.
Each revoked source entitlement MUST retain its original grant transaction identifier and record the newly accepted benefit transaction as its revoking transaction identifier.
The superseded source-entitlement grants MUST remain immutable except for their revocation state and audit history.

For a `grant` action, the workflow MUST create one source entitlement for every guarantee in the package materialized for that transaction.
Guarantees MUST be applied in entitlement-kind identifier order so template mapping insertion order cannot affect persistence, audit records, business events, or lock acquisition.
Every resulting source entitlement MUST use `benefits` as its semantic entitlement source, the internal benefit transaction UUID as its grant transaction identifier, and exactly one subscription or one-time-purchase owner matching the transaction's populated target identifier.
The originating PSP, administrator, support tool, or system component MUST remain identifiable through the corresponding benefit transaction's source identity and source-owned operation record.
All non-lifetime guarantees MUST use the transaction's applicable interval.
Lifetime guarantees MUST use that interval's start and the project's stable lifetime interval-end marker.

For a `revoke` action, the workflow MUST NOT create source entitlements after revoking the selected owner's state.
A revoke action for a target without current or future source entitlements MUST succeed with an empty entitlement-change result.

Different one-time purchases MUST have independent ownership scopes.
Consequently, a correction, refund, reversal, or other non-granting state for one purchase MUST NOT revoke entitlements owned by another purchase, and entitlement-kind merge policy alone MUST determine their combined effective value.

### Subscription application

Every transaction accepted by `apply_subscription_transaction` MUST be associated with one internal subscription identifier.
The command MUST select the subscription by supplying an existing internal subscription identifier, supplying a complete provider subscription identity, or explicitly requesting a new subscription.
For a transaction with a provider subscription identity, the workflow MUST resolve the internal subscription through the subscriptions module's dedicated provider-subscription reference; when no reference exists, it MUST generate a new internal subscription identifier and ask the subscriptions module to persist the reference atomically.
When the command explicitly requests a new subscription, the workflow MUST generate a new internal subscription identifier and MUST reuse it when the same source transaction is retried.
One provider subscription identity MUST NOT resolve to multiple internal subscriptions.
The source identity constraint MUST prevent concurrent retries from applying one operation more than once.
The workflow MAY reject one of two distinct operations that concurrently attempt to create the same previously unknown provider subscription reference.

For each newly accepted benefit transaction, the workflow MUST materialize the current configured template with the separately supplied benefit parameters, derive and persist the entitlement action, and apply the supplied subscription snapshot through the subscriptions domain boundary.
A subscription using a parameterless template MUST supply an empty parameter collection.
A stale snapshot MUST fail and roll back because an obsolete snapshot cannot authorize replacement of the subscription's entitlement state.

### One-time-purchase application

Every transaction accepted by `apply_one_time_purchase_transaction` MUST be associated with one internal one-time-purchase identifier.
The command MUST select the purchase by supplying an existing internal purchase identifier, supplying a complete provider-purchase identity, or explicitly requesting a new purchase.
For a transaction with a provider-purchase identity, the workflow MUST resolve the internal purchase through the one-time-purchases module's dedicated provider-purchase reference; when no reference exists, it MUST generate a new internal purchase identifier and ask that module to persist the reference atomically.
When the command explicitly requests a new purchase, the workflow MUST generate a new internal purchase identifier and MUST reuse it when the same source transaction is retried.
One provider-purchase identity MUST NOT resolve to multiple internal purchases.
The source identity constraint MUST prevent concurrent retries from applying one operation more than once.
The workflow MAY reject one of two distinct operations that concurrently attempt to create the same previously unknown provider-purchase reference.

For each newly accepted transaction, the workflow MUST materialize the current configured template with benefit parameters supplied separately from the purchase snapshot, derive and persist the entitlement action from the normalized purchase status, and apply the snapshot through the one-time-purchases domain boundary.
This materialization requirement MUST apply to completions, corrections, refunds, reversals, disputes, and every other granting or non-granting purchase status.
A one-time-purchase package MUST contain only entitlement kinds whose interval policy is lifetime; supporting a time-limited purchase requires a concrete authoritative interval source not present in the current purchase model.
A stale snapshot MUST fail and roll back because obsolete purchase state cannot authorize replacement of the purchase's entitlement state.

### Atomicity and callbacks

The benefit transaction, purchased-state snapshot, changed source entitlements, derived effective entitlement intervals, and all required audit records MUST commit or roll back as one unit.
Changes for the same transaction source identity, internal purchased-state identity, and affected user and entitlement kind MUST retain the serialization guarantees of the participating modules.

The `ffun.benefits.apply_subscription_transaction` workflow is explicitly approved as the owner of one database transaction that includes benefit-transaction persistence, subscription persistence through `ffun.subscriptions`, and entitlement persistence through `ffun.entitlements`.
The `ffun.benefits.apply_one_time_purchase_transaction` workflow is explicitly approved as the owner of one database transaction that includes benefit-transaction persistence, purchase persistence through `ffun.one_time_purchases`, and entitlement persistence through `ffun.entitlements`.
These exceptions apply only to the two named benefits application workflows.

Business events from participating modules MUST be emitted only after the shared transaction commits.
The workflow MUST collect the callbacks returned by transaction-participating purchased-state and entitlement operations and begin invoking them only after that commit.
Any failure before commit MUST leave the previous transaction ledger, purchased state, source entitlements, effective entitlements, and audit history unchanged and MUST emit no events.
Callback invocation is best-effort post-commit delivery: a callback failure MUST NOT roll back or otherwise invalidate the already committed state.
One callback failure MAY prevent the workflow from invoking callbacks that remain in the collection.
The workflow does not guarantee durable callback replay, and retrying an already accepted transaction source identity MUST NOT replay callbacks from the original application.

## Public interface

The public interface MUST provide these operations:

- `has_benefit` reports whether one benefit identifier has a configured package template.
- `get_benefit` returns one configured package template for a benefit identifier and fails when the identifier is unknown.
- `materialize_benefit_package` resolves one configured template and returns its concrete package for a complete normalized parameter collection.
- `get_benefit_transaction` returns one benefit transaction for an internal transaction identifier, or no value when it is unknown.
- `apply_subscription_transaction` atomically records one subscription-related benefit transaction and applies one complete subscription snapshot.
- `apply_one_time_purchase_transaction` atomically records one purchase-related benefit transaction and applies one complete one-time-purchase snapshot.

`apply_subscription_transaction` MUST accept one complete provider-neutral subscription snapshot, one complete benefit-parameter collection, one benefit transaction command, and the audit actor.
The command MUST contain the `source_id` and `source_transaction_id` transaction identity, subscription selection, and effective time.
It MUST NOT contain a caller-selected entitlement action or a historical transaction to revoke.
A stale subscription snapshot MUST raise a benefits-owned stale-benefit-transaction error containing the subscription identifier and the incoming and current provider update times.

`apply_one_time_purchase_transaction` MUST accept one complete provider-neutral purchase snapshot, one complete benefit-parameter collection, one benefit transaction command, and the audit actor.
The command MUST contain the `source_id` and `source_transaction_id` transaction identity, one-time-purchase selection, and effective time.
It MUST NOT contain a caller-selected entitlement action, arbitrary entitlement guarantees, or a historical transaction to revoke.
A stale purchase snapshot MUST raise a benefits-owned stale-benefit-transaction error containing the one-time-purchase identifier and the incoming and current provider update times.

Each application workflow MUST return an application result containing the internal benefit transaction identifier, the selected target's internal identifier, and whether the transaction was newly created.
The subscription workflow MUST return the internal subscription identifier as the target identifier, while the one-time-purchase workflow MUST return the internal one-time-purchase identifier as the target identifier.
An idempotent retry of either transaction type MUST report that the transaction was not created because its original atomic effects already committed.

## Audit records

The module does not define an additional audit event.
The immutable benefit transaction records the source-owned operation reference, purchased-state target identifier, and derived entitlement action, while its application MUST cause the corresponding purchased-state and entitlement modules to append their specified audit records inside the shared transaction for every corresponding non-no-op state change.

## Business events

The module does not define an additional business event.
After commit, each purchased-state application MUST attempt to cause the corresponding purchased-state and entitlement modules to emit their specified events for every corresponding non-no-op state change.
That delivery is best-effort: callback failure does not invalidate committed state, and this module does not provide durable replay.
