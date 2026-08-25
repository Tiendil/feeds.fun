# Benefits CLI

## Goal of the document

This document describes the Feeds Fun CLI command family for applying administrator-authorized benefit transactions to subscriptions and one-time purchases.

## Scope

This specification covers the public `ffun benefits` command family and its administrative purchased-state application behavior.

The following concerns are out of scope:

- benefit template configuration.
- provider communication.
- direct entitlement management.
- purchased-state inspection.
- other CLI command families.

## Command group

The root CLI MUST expose `benefits` as a command group.

The command group MUST provide commands that apply one complete subscription or one-time-purchase snapshot through the benefits domain workflow.

## Shared behavior

Both commands MUST identify the affected Feeds Fun user with the required `--user-id UUID` option and the configured benefit package template with the required `--benefit-id TEXT` option.
They MUST submit the operation as an administrator-owned benefit source and identify the audit actor as an administrator.

The optional `--actor-id TEXT` MUST select the canonical administrator audit identifier and MUST default to `cli-admin`.
The optional `--source-transaction-id UUID` MUST select the durable benefit source transaction identity.
When omitted, the command MUST generate a new source transaction UUID.
Supplying the same source transaction identifier again MUST use the benefits domain's idempotency behavior.

The repeatable `--parameter NAME=INTEGER` option MUST provide benefit parameters separately from the purchased-state snapshot.
Parameter names MUST be stripped of surrounding whitespace, remain non-empty, and be unique after stripping.
Parameter values MUST parse as integers.
Malformed values and duplicate normalized names MUST fail before invoking the benefits workflow.
Omitting the option MUST supply an empty parameter collection.
Template-specific parameter presence, bounds, and compatibility MUST be validated by the benefits domain.

Each command MUST capture one operation time.
That time MUST be the benefit transaction's effective time and MUST provide every documented creation default based on the current time.

On success, each command MUST print one JSON object followed by a newline.
The object MUST contain:

- `transaction_id` — accepted internal benefit transaction identifier serialized as a UUID string.
- `transaction_created` — whether this invocation created the transaction instead of returning an accepted idempotent result.
- `target_id` — selected or generated internal subscription or one-time purchase identifier serialized as a UUID string.
- `source_transaction_id` — supplied or generated source transaction identifier serialized as a UUID string.

A project-owned domain error MUST be written to standard error and exit with status `1`.
Invalid CLI input MUST use the CLI framework's nonzero parameter-error behavior.

## Commands

### `ffun benefits apply-subscription`

Applies one complete subscription snapshot and its benefit parameters through the benefits domain workflow.

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
- `--parameter NAME=INTEGER` — optional repeatable benefit parameter.
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

Both commands MUST use the benefits module's public domain boundary for purchased-state application.
They MUST NOT:

- persist purchased states directly.
- persist entitlement changes directly.
- reproduce benefit-template materialization.
- reproduce transaction idempotency.
- reproduce stale-snapshot handling.
- reproduce audit behavior.
- reproduce business-event behavior.
