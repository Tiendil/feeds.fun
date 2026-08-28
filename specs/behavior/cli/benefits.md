# Benefits CLI

## Goal of the document

This document describes the Feeds Fun CLI command family for applying administrator-authorized benefit transactions and refreshing subscription entitlements from current benefit configuration.

## Scope

This specification covers the public `ffun benefits` command family.

The following concerns are out of scope:

- benefit template configuration.
- provider communication.
- direct entitlement management.
- purchased-state inspection.
- other CLI command families.

## Command group

The root CLI MUST expose `benefits` as a command group.

The command group MUST provide commands that apply one complete subscription or one-time-purchase snapshot and a command that conditionally refreshes subscription entitlements through the benefits domain workflow.

## Shared behavior

The two purchased-state application commands MUST identify the affected Feeds Fun user with the required `--user-id UUID` option and the configured benefit package template with the required `--benefit-id TEXT` option.
All commands MUST submit changes as an administrator-owned benefit source and identify the audit actor as an administrator.

The optional `--actor-id TEXT` MUST select the canonical administrator audit identifier and MUST default to `cli-admin`.
For purchased-state application commands, the optional `--source-transaction-id UUID` MUST select the durable benefit source transaction identity.
When omitted, the command MUST generate a new source transaction UUID.
Supplying the same source transaction identifier again MUST use the benefits domain's idempotency behavior.

The repeatable `--parameter NAME=INTEGER` option of `apply-one-time-purchase` MUST provide benefit parameters separately from the purchase snapshot.
Parameter names MUST be stripped of surrounding whitespace, remain non-empty, and be unique after stripping.
Parameter values MUST parse as integers.
Malformed values and duplicate normalized names MUST fail before invoking the benefits workflow.
Omitting the option MUST supply an empty parameter collection.
Template-specific parameter presence, bounds, and compatibility MUST be validated by the benefits domain.
Subscription application and refresh MUST NOT expose a benefit-parameter option.

Each command MUST capture one operation time.
That time MUST be the benefit transaction's effective time and MUST provide every documented creation default based on the current time.

On success, each purchased-state application command MUST print one JSON object followed by a newline.
The object MUST contain:

- `transaction_id` — accepted internal benefit transaction identifier serialized as a UUID string.
- `transaction_created` — whether this invocation created the transaction instead of returning an accepted idempotent result.
- `target_id` — selected or generated internal subscription or one-time purchase identifier serialized as a UUID string.
- `source_transaction_id` — supplied or generated source transaction identifier serialized as a UUID string.

A project-owned domain error MUST be written to standard error and exit with status `1`.
Invalid CLI input MUST use the CLI framework's nonzero parameter-error behavior.

## Commands

### `ffun benefits apply-subscription`

Applies one complete subscription snapshot through the benefits domain workflow.
The selected benefit template MUST be parameterless; selecting a template that declares parameters MUST fail without accepting a transaction.

Parameters:

- `--user-id UUID` — required affected-user identifier.
- `--benefit-id TEXT` — required configured benefit package template identifier.
- `--subscription-id UUID` — optional existing internal subscription identifier; when omitted, the workflow creates a new subscription.
- `--status NAME` — normalized subscription status name.
- `--provider-status TEXT` — provider-supplied subscription status.
- `--started-at TIMESTAMP` — subscription start time.
- `--period-starts-at TIMESTAMP` — current subscription-period start.
- `--period-ends-at TIMESTAMP` — current subscription-period end.
- `--expected-renewal-at TIMESTAMP` — optional externally reported expected renewal.
- `--ends-at TIMESTAMP` — optional subscription end.
- `--provider-updated-at TIMESTAMP` — provider snapshot freshness time.
- `--source-transaction-id UUID` — optional durable source transaction identifier.
- `--actor-id TEXT` — optional administrator audit identifier.

Subscription status names MUST be the normalized names defined by the subscriptions module.

When `--subscription-id` is supplied, the following options MUST also be supplied:

- `--status`.
- `--provider-status`.
- `--started-at`.
- `--period-starts-at`.
- `--period-ends-at`.
- `--provider-updated-at`.

This requirement prevents the command from synthesizing lifecycle state for an existing subscription.
The optional expected-renewal and end timestamps MAY remain absent.

When `--subscription-id` is omitted, absent snapshot options MUST use these creation defaults:

- status is `active`.
- provider status is the selected normalized status name.
- subscription start, period start, and provider update are the captured operation time.
- period end is 31 days after the captured operation time.
- expected renewal and subscription end are absent.

### `ffun benefits refresh-subscriptions`

Conditionally refreshes current or future subscription entitlements for one configured benefit.

Parameters:

- `--benefit-id TEXT` — required configured benefit package template identifier and subscription filter.
- `--actor-id TEXT` — optional administrator audit identifier.

The command MUST discover every subscription identity associated with the requested benefit and process those identities in subscription-domain order.
For each identity, it MUST load the current subscription within its independent atomic operation.
A subscription is eligible only when its normalized status grants benefits, its subscription period ends after the captured operation time, and its optional subscription end is absent or later than that time.
A period that starts after the operation time MUST remain eligible.
Subscriptions with any of the following statuses MUST be reported as ineligible and MUST NOT be updated:

- `ended`.
- `paused`.
- `pending`.
- `expired`.

For every eligible subscription, the benefits domain MUST materialize the parameterless current package and compare it with the subscription-owned, unrevoked source entitlements that can affect the operation time or a later time.
A parameterized template MUST fail refresh without accepting a transaction.
The comparison MUST cover:

- entitlement source.
- entitlement kind.
- entitlement value.
- future interval projection.

Expired and revoked source-entitlement history MUST NOT require a refresh.
The command MUST NOT use the user's merged effective entitlement for this comparison.

When the current and desired source entitlements match, the command MUST leave all of the following unchanged:

- subscription.
- benefit-transaction ledger.
- source entitlements.
- effective entitlements.
- audit history.
- business events.

When they differ, the command MUST create one new benefit transaction and atomically replace that subscription's owned entitlements with the materialized package.
The subscription snapshot and its causal state transaction MUST remain unchanged.

Each selected subscription MUST be processed as an independent atomic operation.
The final eligibility and entitlement comparison MUST occur within that operation so a concurrent subscription change cannot authorize an obsolete refresh.
Repeating the command MUST reevaluate every candidate against the current package and current source entitlements.
A previously updated subscription whose desired state still matches MUST be reported as unchanged; a subscription whose desired or owned state changed MUST be updated again.

On success, the command MUST print one JSON object followed by a newline containing:

- `benefit_id` — selected benefit identifier.
- `candidates` — number of discovered subscription identities processed.
- `updated` — number of subscriptions whose required entitlements differed and were updated.
- `unchanged` — number of matching subscriptions left unchanged.
- `ineligible` — number of candidates that were ineligible when loaded within their atomic operation.
- `results` — one record per candidate in subscription-domain order, containing `subscription_id`, `outcome`, and nullable `transaction_id`.

### `ffun benefits apply-one-time-purchase`

Applies one complete purchase snapshot and its benefit parameters through the benefits domain workflow.

Parameters:

- `--user-id UUID` — required affected-user identifier.
- `--benefit-id TEXT` — required configured benefit package template identifier.
- `--one-time-purchase-id UUID` — optional existing internal one-time purchase identifier; when omitted, the workflow creates a new purchase.
- `--status NAME` — normalized one-time-purchase status name.
- `--provider-status TEXT` — provider-supplied purchase status.
- `--purchased-at TIMESTAMP` — provider-reported purchase time.
- `--provider-updated-at TIMESTAMP` — provider snapshot freshness time.
- `--parameter NAME=INTEGER` — optional repeatable benefit parameter.
- `--source-transaction-id UUID` — optional durable source transaction identifier.
- `--actor-id TEXT` — optional administrator audit identifier.

Purchase status names MUST be the normalized names defined by the one-time-purchases module.

When `--one-time-purchase-id` is supplied, the following options MUST also be supplied:

- `--status`.
- `--provider-status`.
- `--purchased-at`.
- `--provider-updated-at`.

This requirement prevents the command from synthesizing lifecycle state for an existing purchase.

When `--one-time-purchase-id` is omitted, absent snapshot options MUST use these creation defaults:

- status is `completed`.
- provider status is the selected normalized status name.
- purchase time and provider update are the captured operation time.

## Integration boundary

All commands MUST use the benefits module's public domain boundary for purchased-state application or conditional entitlement refresh.
They MUST NOT:

- persist purchased states directly.
- persist entitlement changes directly.
- reproduce benefit-template materialization.
- reproduce transaction idempotency.
- reproduce stale-snapshot handling.
- reproduce audit behavior.
- reproduce business-event behavior.
