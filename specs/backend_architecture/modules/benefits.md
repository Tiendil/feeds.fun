# Benefits module

## Goal of the document

This document describes the responsibility and observable benefit-application behavior of the `ffun.benefits` backend module.

## Scope

This specification applies to the provider-independent interpretation and application of configured product benefits by `ffun.benefits`.
The following adjacent concerns are outside the module's responsibility:

- payment-provider communication.
- commercial product and price policy.
- purchased-state lifecycle policy.
- entitlement merge or effective-state policy.

## Dictionary

- `transaction source identity` - the stable identity by which a source subsystem identifies one durable logical operation.
- `transaction effective time` - the source-reported time associated with the operation recorded by a benefit transaction.
- `entitlement action` - the provider-independent grant or revoke decision derived from a purchased state's normalized status.

## Module responsibility

The module owns:

- configured benefit definitions and their validation.
- package materialization.
- the immutable benefit-transaction ledger.
- source-operation idempotency.
- translation of purchased-state benefit-granting semantics into entitlement actions.
- coordination of purchased and entitlement state.

Purchased-state modules own:

- internal purchased-state identities.
- provider references.
- lifecycle state.
- status meanings.
- applicable intervals.

The entitlements module owns source grants, revocations, and effective entitlement state.

Trusted callers MUST supply an authoritative benefit identifier, normalized benefit parameters, and one complete provider-independent subscription or one-time-purchase state.
The benefits module MUST derive the entitlement action from policy owned by the corresponding purchased-state module.
Callers MUST NOT select that action independently or supply materialized entitlement guarantees.

The module MUST NOT communicate with a payment provider, own commercial product data, or maintain provider-product-to-benefit mappings.
Callers MUST use the benefits domain boundary when one logical operation must apply purchased state and its corresponding entitlement state together.

## Special module rules

Subscription benefit application is a benefits-owned workflow in which the following MUST share one database transaction:

- the benefit transaction.
- subscription state managed through `ffun.subscriptions`.
- entitlement state managed through `ffun.entitlements`.
- all required audit evidence.

One-time-purchase benefit application is a benefits-owned workflow in which the following MUST share one database transaction:

- the benefit transaction.
- purchase state managed through `ffun.one_time_purchases`.
- entitlement state managed through `ffun.entitlements`.
- all required audit evidence.

These database-transaction exceptions apply only to the two benefit-application workflows and MUST NOT transfer ownership of participating modules' domain policies or permit bypassing their public domain boundaries.

**Rationale:** Without these exceptions, a failure could leave purchased state inconsistent with its causal benefit transaction or owned entitlements.

## Domain model

### Benefit package templates

A benefit package template is one locally controlled definition of a configured product benefit.
Each template MUST have one stable non-empty benefit identifier that is unique in the active configuration.
It MUST provide local user-facing meaning and define one or more entitlement guarantees through constants or declared benefit parameters.

Each parameter MUST have a non-empty identity that is unique within its template and one inclusive valid range.
Every value in that range MUST satisfy the value contract of each entitlement kind that references the parameter.
A declared parameter MUST be referenced by at least one entitlement guarantee.

Each entitlement guarantee MUST select a distinct entitlement kind and obtain its value from either one compatible configured constant or one direct reference to a parameter declared by the same template.
Templates MUST NOT support general expressions, transformations, or caller-selected entitlement kinds.
They MUST make no token-specific assumption and MAY use any supported entitlement kind whose value contract they satisfy.

A template with no parameters represents a fixed package through constant entitlement guarantees.

### Benefit packages

A benefit package is the fully resolved result of applying one complete normalized parameter collection to one template.
It MUST preserve the template's benefit identity and contain one concrete guarantee for each entitlement kind selected by the template.
It MUST contain no unresolved parameter references.

### Benefit transactions

A benefit transaction is the immutable accepted record of one source-owned logical operation that applies one complete purchased state and its corresponding entitlement decision.
Each transaction MUST have a unique internal identity.
It MUST be associated with exactly one item in each of the following categories:

- transaction source identity.
- user.
- benefit identifier.
- derived entitlement action.
- transaction effective time.
- applicable interval.
- purchased-state target.

Its target MUST be either one subscription or one one-time purchase and MUST NOT be both.

The transaction source identity MUST remain stable across retries of the same logical operation and MUST NOT be reused for a different logical operation.
The following provider identities MUST NOT become benefit-transaction state:

- customer identities.
- product identities.
- subscription identities.
- purchase identities.

The source-owned operation remains responsible for provider payloads and diagnostic provenance.

The entitlement action forms an intentionally closed set of two decisions.
A grant decision means that the materialized package becomes the target's complete desired entitlement state.
A revoke decision means that the target's complete desired entitlement state is empty.

Benefit transactions MUST be append-only.
The following transaction properties MUST remain unchanged after acceptance:

- benefit association.
- target.
- source identity.
- applicable interval.
- effective time.
- derived action.

## Domain behavior

### Template validation and materialization

Invalid or internally inconsistent template configuration MUST be rejected before the affected template is available for lookup or materialization.
This includes:

- duplicate identities.
- invalid parameter ranges.
- undeclared or unused parameter references.
- incompatible constants or ranges.
- missing guarantees.
- incomplete definitions.

Callers MUST be able to determine whether a benefit identifier has a configured template and to retrieve that template.
They MUST also be able to materialize a configured template from normalized parameters.
An unknown benefit identifier MUST fail lookup or materialization without changing benefit-transaction, purchased-state, or entitlement state.

A materialization request MUST provide exactly one value for every declared parameter and no value for an undeclared parameter.
Each value MUST be a whole number within its declared range and satisfy every referenced entitlement kind's value contract.
Materialization MUST resolve every guarantee and MUST be deterministic for the same valid template configuration and normalized parameters.
A parameterless template MUST materialize only from an empty parameter collection.

Every newly identified benefit transaction MUST materialize the currently configured template, including a transaction whose derived action is revoke.
Repeating an already accepted transaction source identity MUST use the accepted outcome without resolving or materializing the template again.

Changing a template MUST NOT by itself alter benefit transactions, purchased state, or entitlements.
The change becomes effective for an existing purchased state only when a newly identified benefit transaction actualizes that state.
Existing source entitlements remain authoritative for the concrete values and intervals established by historical transactions.

Display-text changes MAY retain a benefit identifier.
Incompatible changes to parameters or entitlement guarantees SHOULD use a new benefit identifier, and an old template MUST remain configured while an authoritative source can still initiate transactions that reference it.
A benefit identifier MUST NOT be reused for an unrelated product.

### Purchased-state selection and provider boundary

Benefit application MUST support an existing internal purchased-state target, a complete provider identity resolved through its owning module, or creation of a new internal target.
When a previously unknown provider identity selects the target, the owning purchased-state module MUST establish its immutable association with the new internal target as part of the same application outcome.
One provider identity MUST NOT resolve to multiple internal targets.

Provider adapters and other trusted callers MUST obtain the benefit identifier and normalized parameters from authoritative metadata.
The benefits module MUST NOT infer that information from provider product data.
Benefit parameters MUST remain separate from purchased state and MUST NOT be persisted as subscription or one-time-purchase state.

### Entitlement-action and interval derivation

Each purchased-state module MUST determine whether each of its normalized statuses grants benefits.
The benefits module MUST translate a benefit-granting status into a grant decision and every non-benefit-granting status into a revoke decision without reproducing the owning module's status policy.

The accepted benefit transaction MUST preserve the derived action so later policy changes do not reinterpret the historical operation.
The action describes the selected purchased-state target's complete desired entitlement state and MUST NOT be interpreted as a request to reverse one historical transaction.

The benefits module MUST use the applicable interval determined by the selected purchased state.
Every package guarantee's lifetime status MUST match that applicable interval: a lifetime entitlement kind requires the project's stable lifetime interval-end marker, while a non-lifetime entitlement kind requires a finite interval end.
The transaction effective time MUST remain causal provenance and MUST NOT replace the purchased state's interval boundaries or schedule entitlement revocation.

### Transaction acceptance and idempotency

The first accepted transaction for one transaction source identity MUST remain authoritative.
Repeating that source identity MUST have no additional domain effect and MUST identify the previously accepted transaction and target, regardless of different data supplied by the repeated request.

Competing attempts to accept the same previously unseen source identity MUST permit at most one transaction to succeed.
An overlapping losing attempt MAY fail, while a retry after the winning outcome is durable MUST receive the accepted idempotent outcome.

Callers MUST be able to retrieve an accepted transaction by its internal identity, with absence reported when it is unknown.
Retrieval MUST have no domain effects.

### Purchased-state application and entitlement actualization

Every newly accepted transaction MUST apply the supplied purchased state through its owning module and actualize the complete entitlement state owned by that target.
The module MUST NOT accept a purchased-state update without considering its corresponding entitlement state.

Purchased state that is older than current authoritative state MUST fail benefit application because it cannot authorize replacement of the target's entitlement state.
Failure MUST leave the transaction source identity unaccepted and preserve:

- the prior transaction ledger.
- purchased state.
- entitlements.
- audit history.

Actualization MUST occur for every newly identified transaction whose supplied purchased state is accepted, including identical state and state that advances only authoritative freshness.
An idempotent retry of an already accepted transaction source identity MUST NOT actualize the target again.

Actualization MUST use one evaluation time for every time-dependent decision and effect.
Actualization MUST replace the selected target's active or future owned entitlements with its complete desired entitlement state.
That replacement takes effect at the workflow's evaluation time rather than at the transaction effective time.

For a grant decision, the workflow MUST establish one source entitlement for each guarantee in the materialized package using the target's applicable interval.
Those grants MUST remain attributable to the benefits source, the accepted benefit transaction, and exactly the selected purchased-state target.
Template mapping order MUST NOT affect:

- entitlement outcomes.
- audit outcomes.
- business-event outcomes.
- concurrency outcomes.

For a revoke decision, the workflow MUST establish no replacement source entitlements.
Revoking a target that has no active or future owned entitlements MUST succeed without an entitlement change.

Each one-time purchase MUST retain an independent entitlement-ownership scope.
A non-granting state for one purchase MUST NOT revoke entitlements owned by another purchase.

The following MUST succeed or fail together:

- the accepted benefit transaction.
- the purchased-state outcome.
- entitlement changes.
- derived effective entitlement state.
- required audit evidence.

Competing applications affecting any of the following MUST preserve the serialization guarantees owned by the participating modules:

- the same source identity.
- the same purchased-state target.
- the same user.
- the same entitlement kind.

## Audit records

The module produces no additional audit record beyond the immutable benefit transaction.
That transaction MUST durably preserve the source-owned operation reference, selected purchased-state target, and derived entitlement action.

Every participating purchased-state or entitlement change MUST produce the audit evidence required by its owning module.
The benefit transaction, all participating state changes, and all required audit evidence MUST succeed or fail together.
A failed or idempotent application MUST NOT produce new audit evidence.

## Business events

The module produces no additional business event.
Every participating purchased-state or entitlement change MUST produce the business notification required by its owning module only after the complete application outcome and required audit evidence are durable.

A failed or idempotent application MUST emit no notification.
Retrying an accepted transaction source identity MUST NOT replay notifications from its original application.
