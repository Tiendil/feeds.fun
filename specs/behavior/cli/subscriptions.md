# Subscriptions CLI

## Goal of the document

This document describes the Feeds Fun CLI command family for inspecting locally persisted purchased-subscription snapshots.

## Scope

This specification covers the public `ffun subscriptions` command family and its inspection and debugging behavior.

Subscription domain rules, provider communication, entitlement behavior, and other CLI command families are out of scope.

## Command group

The root CLI MUST expose `subscriptions` as a command group.

The command group MUST provide a command that lists one user's subscriptions.

## Shared behavior

Every command MUST identify the affected Feeds Fun user with the required `--user-id UUID` option.

Subscription status parameters MUST accept the normalized subscription-status names defined by the subscriptions module.

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
The table MUST contain the internal subscription identifier, benefit identifier, normalized and provider statuses, subscription start, current-period start, current-period end, expected-renewal, end, and provider-update timestamps.
Missing expected-renewal and end timestamps MUST be rendered as `-`.

When `--json` is supplied, the command MUST print one JSON object on its own line for every returned subscription in subscription-domain order.
Every JSON object MUST contain these fields:

- `id` — internal subscription identifier serialized as a UUID string.
- `state_transaction_id` — causal benefit transaction identifier serialized as a UUID string.
- `user_id` — affected user id serialized as a UUID string.
- `benefit_id` — configured benefit identifier.
- `status` — normalized subscription status enum member name.
- `status_id` — stable integer value of the normalized subscription status.
- `provider_status` — provider-supplied status.
- `started_at` — subscription start as an ISO 8601 timestamp with an explicit UTC offset.
- `period_starts_at` — current subscription-period start as an ISO 8601 timestamp with an explicit UTC offset.
- `period_ends_at` — current subscription-period end as an ISO 8601 timestamp with an explicit UTC offset.
- `expected_renewal_at` — externally reported expected renewal as an ISO 8601 timestamp with an explicit UTC offset, or `null`.
- `ends_at` — subscription end as an ISO 8601 timestamp with an explicit UTC offset, or `null`.
- `provider_updated_at` — provider update time as an ISO 8601 timestamp with an explicit UTC offset.

## Integration boundary

Subscription commands MUST invoke the public `ffun.subscriptions.domain` interface.
They MUST NOT reproduce subscription identity, validation, freshness, replacement, audit, or business-event behavior.
