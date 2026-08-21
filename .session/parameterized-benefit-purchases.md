# Draft: Parameterized Benefits and One-Time Purchases

## Goal

Extend `ffun.benefits` so the same benefit model can serve subscriptions and one-time purchases.

A trusted PSP integration or administrator should be able to select a configured benefit package template and supply runtime parameters, such as the number of tokens purchased. The template remains authoritative about which entitlements those parameters produce, so callers cannot grant arbitrary entitlement kinds or bypass local benefit policy.

The design must also support packages that grant non-token entitlements, such as disabling advertisements, and packages that combine multiple kinds of entitlements.

## High-level architecture

```text
configured BenefitPackageTemplate
                 +
PSP / administrator normalized parameters
                 |
                 v
            ffun.benefits
       materialized BenefitPackage
                 |
        +--------+----------------------+
        |                               |
        v                               v
ffun.one_time_purchases          ffun.entitlements
one-time purchase state          purchase-owned grants
```

Responsibilities remain separated:

- PSP integrations own provider communication and translate authoritative provider metadata into a local benefit identifier and normalized parameters.
- `ffun.benefits` owns package-template configuration, parameter validation, materialization into concrete packages, benefit-transaction idempotency, and atomic orchestration.
- `ffun.one_time_purchases` owns provider-independent one-time purchase identity and current purchase state.
- `ffun.subscriptions` continues to own provider-independent subscription identity and current subscription state.
- `ffun.entitlements` owns source grants and effective entitlement state.

Provider prices, currencies, taxes, invoices, payment attempts, and checkout configuration remain outside `ffun.benefits`.

## Benefit package templates

Configured benefits are represented by `BenefitPackageTemplate`. A template contains:

- A stable identifier, title, and description.
- Zero or more accepted parameter definitions.
- A non-empty mapping from entitlement kinds to entitlement value templates.

Applying normalized parameter values to a template materializes a concrete `BenefitPackage`. The concrete package contains normalized parameter values and fully resolved entitlement guarantees. It contains no unresolved parameter references.

A parameter definition declares a stable name and validation constraints. The first implementation supports integer parameter values because the current runtime requirement is a purchased quantity. Additional parameter types should be introduced only for concrete product requirements.

The template's entitlement mapping associates each locally known entitlement kind with a value template, which is either:

- A `ParameterConstant` containing a configured entitlement value.
- A `ParameterReference` identifying one declared package parameter.

Both value-template variants expose the same materialization operation. The initial template language should not contain a general expression engine. Constants and direct parameter references are sufficient for the first implementation. Simple transformations can be introduced later when supported by a concrete product requirement.

Conceptual entities:

```python
BenefitParameters = Mapping[BenefitParameterId, int]


class BenefitParameterDefinition:
    id: BenefitParameterId
    constraints: ParameterConstraints


class ParameterConstant:
    value: int

    def materialize(
        self,
        parameters: BenefitParameters,
    ) -> int: ...


class ParameterReference:
    parameter_id: BenefitParameterId

    def materialize(
        self,
        parameters: BenefitParameters,
    ) -> int: ...


class BenefitPackage:
    id: BenefitId
    parameters: BenefitParameters
    entitlements: Mapping[EntitlementKindId, int]


class BenefitPackageTemplate:
    id: BenefitId
    title: str
    description: str
    parameters: tuple[BenefitParameterDefinition, ...]
    entitlements: Mapping[EntitlementKindId, ParameterConstant | ParameterReference]

    def materialize(
        self,
        parameters: BenefitParameters,
    ) -> BenefitPackage: ...
```

Entitlement kinds are unique by construction because they are mapping keys. A package has no business-significant entitlement order, and the model does not duplicate `kind_id` inside every value.

`ParameterConstant` and `ParameterReference` implement the same `materialize(parameters)` contract. `BenefitPackageTemplate` can therefore materialize every mapping value without branching on its source type.

`BenefitPackageTemplate.materialize` validates and normalizes the complete parameter collection before invoking each value template. Individual value templates resolve one value; they do not reject parameters required by other entitlements in the same package.

Exact supporting class names and serialization formats are implementation details. The important distinction is that configuration stores templates, while transaction workflows consume concrete packages. Package-template configuration defines the allowed mapping from caller-supplied parameters to entitlement guarantees.

Benefits settings should therefore expose `package_templates`, not `packages`. Existing configured packages become templates with no parameters and kind-keyed `ParameterConstant` values.

### Constant-valued subscription package example

An existing subscription package template requires no parameters:

```text
template: pro-monthly
parameters: none
entitlements:
  day_tokens: constant(1000)
  month_tokens: constant(20000)
```

Materializing this template with an empty parameter collection produces a concrete `BenefitPackage` with the same guarantees as the current fixed package.

### Arbitrary lifetime-token purchase example

```text
template: lifetime-tokens
parameters:
  quantity: integer, minimum 1
entitlements:
  lifetime_tokens: parameter(quantity)
```

The trusted caller supplies:

```text
benefit_id: lifetime-tokens
parameters:
  quantity: 500
```

The template materializes to a concrete package:

```text
package: lifetime-tokens
parameters:
  quantity: 500
entitlements:
  lifetime_tokens: 500
```

The caller selects the quantity but does not select `lifetime_tokens`; that binding remains controlled by local configuration.

### Composite package example

A package template can combine parameter references and constants:

```text
template: supporter-pack
parameters:
  quantity: integer, minimum 1
entitlements:
  lifetime_tokens: parameter(quantity)
  ads_disabled: constant(1)
```

Materializing the template with `quantity=500` produces a concrete package that grants 500 lifetime tokens and disables advertisements. The caller cannot omit or replace the `ads_disabled` entitlement and cannot redirect `quantity` to another entitlement kind.

### Template validation

Configuration loading should reject templates with:

- Duplicate package or parameter identifiers.
- Entitlement value templates that reference undeclared parameters.
- `ParameterConstant` values incompatible with their entitlement kind.
- Parameter references whose declared value type is incompatible with their entitlement kind.
- Missing required constraints or invalid constant values.
- Unused parameters, unless a concrete use case requires allowing them.

## Template validation and package materialization

The template and package lifecycle has two distinct validation stages:

1. Configuration loading validates every `BenefitPackageTemplate`, including its parameter definitions and entitlement references.
2. Runtime materialization validates supplied parameter values and produces one concrete `BenefitPackage`.

`ffun.benefits` exposes an internal domain operation that resolves a template by benefit identifier and materializes it with normalized parameters.

Conceptually:

```python
package = materialize_benefit_package(
    benefit_id=BenefitId("supporter-pack"),
    parameters={"quantity": 500},
)
```

Materialization must:

1. Resolve the configured package template.
2. Reject missing, unexpected, or duplicated parameters for the complete package.
3. Validate parameter types and constraints.
4. Materialize every kind-keyed constant or parameter-reference value template.
5. Validate each resulting value against its entitlement kind.
6. Return a normalized `BenefitPackage` containing only concrete guarantees.

Conceptual result:

```python
BenefitPackage(
    id=BenefitId("supporter-pack"),
    parameters={"quantity": 500},
    entitlements={
        lifetime_tokens: 500,
        ads_disabled: 1,
    },
)
```

Materialization must be deterministic for the same package-template configuration and normalized parameter values.

Every previously unseen benefit transaction materializes its package from the current template and caller-supplied parameters. This rule applies to subscriptions and one-time purchases, and to both benefit-granting and benefit-revoking transaction states. An idempotent retry of an already accepted source transaction returns the stored result and does not initiate materialization again.

The term `materialize` describes the runtime template-plus-parameters operation. The term `compile` should be reserved for an optional earlier transformation from raw configuration into a validated or optimized `BenefitPackageTemplate`; the first implementation does not require a separate compiled representation.

## One-time purchases module

Introduce `ffun.one_time_purchases`, analogous to but smaller than `ffun.subscriptions`. It owns:

- Internally generated `OneTimePurchaseId` values.
- Provider-purchase references and their uniqueness rules.
- Current provider-independent purchase snapshots.
- Normalized purchase statuses and whether each status grants benefits.
- Snapshot freshness and conflict handling.
- Purchase queries, audit records, and business events.

The identifier uses the explicit cross-context name `OneTimePurchaseId`. Entities scoped to the clearly named module remain compact, such as `PurchaseSnapshot`, `PurchaseStatus`, and `Purchase`.

A conceptual purchase snapshot is:

```python
PurchaseSnapshot(
    user_id=user_id,
    benefit_id=BenefitId("supporter-pack"),
    status=PurchaseStatus.completed,
    provider_status="paid",
    purchased_at=purchased_at,
    provider_updated_at=provider_updated_at,
)
```

The snapshot retains `benefit_id`, consistently with `SubscriptionSnapshot`, but does not contain benefit parameters. Benefit parameters are supplied separately to each newly initiated `ffun.benefits.apply_one_time_purchase_transaction`, used for package materialization, and not persisted.

When one-time purchases can grant non-lifetime entitlements, the snapshot or package context must also provide the applicable benefit interval. Lifetime entitlement kinds continue to use the stable lifetime interval marker.

Purchase statuses should expose a `grants_benefits` semantic, just as subscription statuses do. `ffun.benefits` derives grant or revoke behavior from that semantic; PSP integrations must not directly select an entitlement action.

The exact status set will be specified with the one-time purchases module. It will likely distinguish states such as pending, completed, refunded, and reversed or disputed.

## Applying a one-time purchase transaction

Add `ffun.benefits.apply_one_time_purchase_transaction`, parallel to `apply_subscription_transaction`.

For each previously unseen source transaction, the workflow atomically:

1. Resolves or creates the internal purchase identity.
2. Resolves the configured `BenefitPackageTemplate`.
3. Validates and normalizes the benefit parameters supplied separately from the purchase snapshot.
4. Materializes a concrete `BenefitPackage` containing entitlement guarantees.
5. Creates and records an immutable benefit transaction.
6. Saves the authoritative purchase snapshot through the `ffun.one_time_purchases` public domain boundary.
7. Rejects stale purchase snapshots and rolls back all work.
8. Revokes current or future entitlements owned by that purchase.
9. Grants the materialized entitlements when the normalized purchase status grants benefits.
10. Commits benefit, purchase, entitlement, lock, and audit changes together.
11. Invokes collected business-event callbacks after commit.

The workflow follows the existing transaction rules used for subscriptions:

- The exact source identity provides operation idempotency.
- A retry of an accepted source transaction returns the stored result without materializing or applying the package again.
- An overlapping first attempt that loses the source-identity race fails and may be retried after the winner commits.
- A stale purchase snapshot does not consume the source identity.
- Business events are emitted only after commit and are not replayed by an idempotent retry.

Steps 2–4 run for every previously unseen one-time purchase transaction, including status changes, corrections, refunds, and reversals. A granting transaction applies the freshly materialized package; a revoking transaction still materializes the package before actualizing the purchase-owned entitlement state to empty. The materialized output is not stored in the benefit transaction.

### Additive purchases example

One user makes two purchases:

```text
purchase A -> lifetime_tokens: 100
purchase B -> lifetime_tokens: 250
```

The purchases create independent source entitlements. Because `lifetime_tokens` uses the `sum` merge policy, the effective value is 350.

### Refund example

If purchase A is later refunded, a new benefit transaction actualizes purchase A to an empty entitlement state. Its 100-token grant is revoked, while purchase B remains active. The effective value becomes 250.

### Correction example

If authoritative provider state corrects purchase B from 250 to 200 tokens, a new transaction revokes B's previous grant and creates a 200-token replacement. No other purchase or subscription is affected.

## Benefit transaction model

Keep all subscription and one-time purchase benefit transactions in the existing common immutable transaction table. Do not introduce target-specific transaction detail tables.

Conceptual persistence shape:

```text
b_transactions
  id
  source_id
  source_transaction_id
  entitlement_action
  user_id
  benefit_id
  subscription_id             nullable
  one_time_purchase_id        nullable
  effective_at
  period_starts_at
  period_ends_at
  created_at
```

The existing source-identity uniqueness constraint continues to provide idempotency across all benefit operations. The table keeps explicit `subscription_id` and `one_time_purchase_id` columns rather than introducing a generic target-kind/target-id pair.

A database check constraint must require exactly one target column to be non-null. A populated `subscription_id` identifies a subscription transaction, while a populated `one_time_purchase_id` identifies a one-time purchase transaction. This makes neither-target and both-target rows invalid without persisting a redundant transaction-kind discriminator.

Domain code may expose the transaction kind as a computed property when needed for dispatch, serialization, or events.

The benefit identifier identifies the source `BenefitPackageTemplate`. Both input parameters and the materialized package are transient to the benefit transaction workflow and are not duplicated in `b_transactions`.

For granting transactions, `ffun.entitlements` persists each concrete kind, value, and interval in `en_source_entitlements`, linked to the benefit transaction by `grant_transaction_id`. Revocations remain traceable through `revoked_by_transaction_id`. These source-entitlement records are the authoritative persistence of what was actually granted or revoked.

The concrete entitlement interval is also common transaction data. Lifetime purchases use the stable lifetime interval marker; time-limited purchases and subscriptions store their applicable interval directly.

Transaction application results should remain typed:

- Subscription results contain the internal subscription identifier.
- One-time purchase results contain the internal purchase identifier.
- Both contain the benefit transaction identifier and whether the transaction was newly created.

## Configuration evolution

Subscriptions and one-time purchases follow the same materialization semantics:

- Every previously unseen source transaction resolves the current configured template and materializes it with the parameters supplied for that transaction.
- Materialization occurs regardless of target type, purchase or subscription status, and whether the resulting entitlement action grants or revokes benefits.
- The benefit transaction stores neither input parameters nor materialized entitlements. Concrete grants and revocations are preserved by `en_source_entitlements`; later configuration changes do not alter those historical records.
- A later status update, correction, refund, reversal, or subscription update is a new transaction and materializes against configuration current at that time.
- An idempotent retry returns the stored result and never rematerializes because it does not initiate a new transaction.
- Parameterless templates receive an empty parameter mapping on every new transaction.

Changing template display text does not affect existing transactions. Incompatible changes to parameter names or entitlement bindings should normally use a new benefit identifier, and old templates should remain available while provider records can still initiate transactions that reference them.

## Entitlement ownership

Extend source entitlements with an explicit optional one-time purchase owner alongside the existing optional subscription owner:

```python
subscription_id: SubscriptionId | None
one_time_purchase_id: OneTimePurchaseId | None
```

A source entitlement may have at most one of these owners. Entitlements without either owner may remain available for explicitly supported administrative or system grants.

Add `revoke_one_time_purchase_entitlements`, equivalent to `revoke_subscription_entitlements`. It revokes every current or future source entitlement owned by a single one-time purchase and rebuilds the affected effective entitlement timelines.

Grant operations should accept an explicit subscription owner, one-time purchase owner, or no owner. Persistence must retain concrete owner columns and must not encode ownership as a generic target-kind/target-id pair.

`ffun.benefits` keeps package entitlements as mappings. When calling the current `ffun.entitlements` grant API, it converts the mapping into `EntitlementGuarantee` command entities ordered by `EntitlementKindId`. Mapping insertion order must not influence persistence, audit records, events, or lock acquisition.

This produces two distinct actualization scopes:

- A subscription transaction replaces the complete benefit state owned by one subscription.
- A one-time purchase transaction replaces the complete benefit state owned by one purchase.

Different one-time purchases remain independent, so their additive entitlement values accumulate.

## Non-token entitlements

Benefit package templates must not assume that entitlements are tokens. Entitlement kinds remain responsible for defining valid values and merge behavior.

All entitlement guarantees in this draft use the current integer value contract. A non-token capability such as `ads_disabled` is represented by value `1` and uses the existing `max` merge policy:

```text
ads_disabled
  granted value: 1
  merge policy: max
```

Non-integer entitlement values are outside this draft and require a separate design change to `ffun.entitlements`.

## Trust and validation boundaries

- Browser or checkout input is not authoritative package input.
- PSP integrations derive the benefit identifier and parameters from trusted provider metadata or persisted source records.
- Administrator commands use the same package validation and materialization path as PSP integrations.
- Callers supply parameters, never arbitrary materialized guarantees.
- Package-template configuration controls entitlement kinds and parameter bindings.
- Individual numeric values and merged totals must respect persistence bounds even when purchase quantities are not enumerated in configuration.

## Open policy decisions

The implementation specifications should resolve:

- The exact normalized purchase statuses and their benefit-granting semantics.
- How partial refunds are represented: reduced authoritative parameters or full revocation plus a replacement purchase.
- How refunds behave after some purchased consumable entitlement has already been used. Consumption history should not be deleted, but remaining-credit behavior must be explicit.
- Numeric bounds for individual parameters and accumulated entitlement values.
- Whether parameter transformations beyond constants and direct references are needed.

## Refactoring plan

- [x] Update the benefits architecture specification with the `BenefitPackageTemplate` and concrete `BenefitPackage` distinction, materialization, typed transaction details, and purchase application semantics.
- [x] Define validation constraints and persistence bounds for integer package parameters and entitlement values.
- [x] Add `BenefitPackageTemplate`, integer parameter definitions, kind-keyed entitlement mappings, uniform `ParameterConstant | ParameterReference` value templates, normalized integer parameters, and concrete `BenefitPackage` to `ffun.benefits`.
- [x] Change benefits settings to store `package_templates`, validate them during configuration loading, and add focused template-validation tests.
- [x] Add runtime package materialization and tests for missing, unknown, invalid, and incompatible parameter values.
- [x] Convert existing fixed subscription configuration to parameterless templates and route subscription application through materialization without changing current behavior.
- [x] Extend the existing `b_transactions` ledger with explicit nullable subscription and one-time purchase identifiers and a strict exactly-one-target check constraint while preserving source idempotency, stale-update rollback, and post-commit callbacks.
- [ ] Add `OneTimePurchaseId` and specify `ffun.one_time_purchases` identity, statuses, snapshots, references, freshness rules, audits, events, and public operations.
- [ ] Implement the `ffun.one_time_purchases` entities, persistence, domain operations, migrations, and tests.
- [ ] Add explicit one-time purchase ownership to source entitlements and implement one-time-purchase-level revocation, timeline rebuilding, audits, events, migrations, and tests.
- [ ] Add one-time-purchase transaction entities and typed application results backed by the common `b_transactions` table.
- [ ] Implement `apply_one_time_purchase_transaction` with atomic benefit, purchase, and entitlement coordination and fresh package materialization for every previously unseen transaction.
- [ ] Add workflow tests for arbitrary quantities, composite packages, independent additive purchases, retries, concurrent attempts, stale updates, corrections, refunds, rollback, and post-commit event behavior.
- [ ] Update PSP and administrator entry points to submit benefit identifiers and normalized parameters through the new workflow.
- [ ] Update related architecture, behavior, database, entity, audit, event, and CLI specifications.
- [ ] Run the project polish workflow and the required dependency-consistency workflow, resolving all affected relations before completion.
