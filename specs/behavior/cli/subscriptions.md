# Subscriptions CLI

## Goal of the document

This document describes the Feeds Fun CLI command family for managing and inspecting locally persisted purchased-subscription snapshots.

## Scope

This specification covers the public `ffun subscriptions` command family and its administration and debugging behavior.

Subscription domain rules, provider communication, entitlement behavior, and other CLI command families are out of scope.

## Command group

The root CLI MUST expose `subscriptions` as a command group.

The command group MUST provide commands that list one user's subscriptions, save one complete subscription snapshot, and partially update one existing subscription snapshot.

## Shared behavior

Every command MUST identify the affected Feeds Fun user with the required `--user-id UUID` option.

Subscription status parameters MUST accept a `SubscriptionStatusId` enum member name and resolve it to the corresponding enum member before invoking the subscription domain.
Valid names MUST be derived from the enum rather than duplicated in the CLI specification or implementation.

Timestamp parameters MUST use ISO 8601 format with an explicit UTC offset.
Every command that changes subscription state MUST capture one current timestamp and use it as `provider_updated_at` when `--provider-updated-at` is omitted.

Change commands MUST accept `--actor-kind {user|admin|psp|system}` and `--actor-id ID` options for the audit actor.
The actor kind and actor id MUST default to `admin`.

## Commands

### `ffun subscriptions list`

Lists current subscription snapshots associated with one user.
By default the command includes subscriptions in every status, including ended subscriptions.

Parameters:

- `--user-id UUID` — required affected-user identifier.
- `--status NAME` — optional normalized subscription-status filter; MAY be supplied multiple times.
- `--alive` — returns only subscriptions that are alive at the query evaluation time by using the subscription domain's alive-subscription query.
- `--json` — prints JSON Lines instead of the default human-readable table.

When `--status` is omitted and `--alive` is not supplied, the command MUST return subscriptions in every status.
When one or more `--status` options are supplied, the command MUST return only subscriptions whose normalized status matches one of the selected values.
The `--alive` option MUST NOT be combined with `--status`.

By default, the command MUST print a human-readable grid table with one row for every returned subscription in subscription-domain order.
The table MUST contain provider, merchant, subscription, and customer identifiers; normalized and provider statuses; and subscription start, current-period start, current-period end, expected-renewal, end, and provider-update timestamps.
Missing expected-renewal and end timestamps MUST be rendered as `-`.

When `--json` is supplied, the command MUST print one JSON object on its own line for every returned subscription in subscription-domain order.
Every JSON object MUST contain these fields:

- `provider_id` — subscription provider identifier.
- `provider_merchant_id` — provider merchant identifier.
- `provider_subscription_id` — provider subscription identifier.
- `user_id` — affected user id serialized as a UUID string.
- `provider_customer_id` — provider customer identifier.
- `status` — normalized subscription status enum member name.
- `status_id` — stable integer value of the normalized subscription status.
- `provider_status` — provider-supplied status.
- `started_at` — subscription start as an ISO 8601 timestamp with an explicit UTC offset.
- `period_starts_at` — current subscription-period start as an ISO 8601 timestamp with an explicit UTC offset.
- `period_ends_at` — current subscription-period end as an ISO 8601 timestamp with an explicit UTC offset.
- `expected_renewal_at` — externally reported expected renewal as an ISO 8601 timestamp with an explicit UTC offset, or `null`.
- `ends_at` — subscription end as an ISO 8601 timestamp with an explicit UTC offset, or `null`.
- `provider_updated_at` — provider update time as an ISO 8601 timestamp with an explicit UTC offset.

### `ffun subscriptions set`

Saves one complete subscription snapshot and MAY create a missing subscription or replace an existing snapshot with a newer one according to subscription-domain rules.

Parameters:

- `--user-id UUID` — required affected-user identifier.
- `--provider-id ID` — subscription provider identifier; defaults to `feeds-fun-cli`.
- `--provider-merchant-id ID` — provider merchant identifier; defaults to `feeds-fun` for the default provider.
- `--provider-subscription-id ID` — provider subscription identifier; defaults to `feeds-fun-subscription-<user-id>` for the default provider.
- `--provider-customer-id ID` — provider customer identifier; defaults to `feeds-fun-user-<user-id>` for the default provider.
- `--status NAME` — normalized subscription status name; defaults to `active`.
- `--provider-status STATUS` — provider-supplied status; defaults to the resolved normalized status name.
- `--started-at TIMESTAMP` — subscription start time; defaults to the captured current timestamp.
- `--period-starts-at TIMESTAMP` — current subscription-period start; defaults to the resolved subscription start time.
- `--period-ends-at TIMESTAMP` — current subscription-period end; defaults to 31 days after the resolved period start.
- `--expected-renewal-at TIMESTAMP` — externally reported expected renewal time; defaults to no expected renewal.
- `--ends-at TIMESTAMP` — subscription end time; defaults to 31 days after the resolved subscription start time.
- `--provider-updated-at TIMESTAMP` — provider update time; defaults to the captured current timestamp.
- `--json` — prints structured JSON instead of the default human-readable result.
- `--actor-kind {user|admin|psp|system}` — audit actor kind; defaults to `admin`.
- `--actor-id ID` — audit actor identifier; defaults to `admin`.

When `--provider-id` differs from `feeds-fun-cli`, the command MUST require explicit `--provider-merchant-id`, `--provider-subscription-id`, and `--provider-customer-id` values and MUST NOT derive the default-provider identifiers.

### `ffun subscriptions update`

Loads one existing subscription by its provider identity, verifies that it belongs to the specified user, and saves a complete snapshot with selected mutable fields replaced.

Parameters:

- `--user-id UUID` — required affected-user identifier.
- `--provider-id ID` — required subscription provider identifier.
- `--provider-merchant-id ID` — required provider merchant identifier.
- `--provider-subscription-id ID` — required provider subscription identifier.
- `--status NAME` — optional replacement normalized subscription status name.
- `--provider-status STATUS` — optional replacement provider-supplied status.
- `--started-at TIMESTAMP` — optional replacement subscription start time.
- `--period-starts-at TIMESTAMP` — optional replacement current subscription-period start.
- `--period-ends-at TIMESTAMP` — optional replacement current subscription-period end.
- `--expected-renewal-at TIMESTAMP` — optional replacement externally reported expected renewal time.
- `--clear-expected-renewal-at` — clears the expected renewal time and MUST NOT be combined with `--expected-renewal-at`.
- `--ends-at TIMESTAMP` — optional replacement subscription end time.
- `--clear-ends-at` — clears the subscription end time and MUST NOT be combined with `--ends-at`.
- `--provider-updated-at TIMESTAMP` — optional provider update time.
- `--json` — prints structured JSON instead of the default human-readable result.
- `--actor-kind {user|admin|psp|system}` — optional audit actor kind.
- `--actor-id ID` — optional audit actor identifier.

The command MUST require at least one mutable-field replacement or clear option.
Omitted mutable fields MUST preserve their stored values.
The command MUST fail when the exact subscription identity is unknown or belongs to a different user.

## Change output

By default, the `set` and `update` commands MUST print the save outcome as a human-readable heading followed by a one-row subscription table with the same columns and timestamp rendering as the `list` command.

When `--json` is supplied, the command MUST print one JSON object containing these fields after the subscription domain returns:

- `outcome` — save outcome enum member name.
- `outcome_id` — stable integer value of the save outcome.
- `subscription` — complete resolved subscription snapshot using the JSON field contract of one `list --json` record.

## Integration boundary

Subscription commands MUST invoke the public `ffun.subscriptions.domain` interface.
They MUST NOT reproduce subscription identity, validation, freshness, replacement, audit, or business-event behavior.
