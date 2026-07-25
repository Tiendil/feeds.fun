# Entitlements CLI

## Goal of the document

This document describes the Feeds Fun CLI command family for managing and inspecting user entitlements.

## Scope

This specification covers the public `ffun entitlements` command family and the entitlement capabilities it exposes.

Entitlement domain rules, persistence, audit records, business events, and other CLI command families are out of scope. Output formats for `grant` and `revoke` are not yet specified.

## Command group

The root CLI MUST expose `entitlements` as a command group.

The command group MUST provide CLI access to source entitlement changes and batch effective-entitlement listings.

## Commands

The `grant` command MUST capture one current timestamp and use it consistently to resolve omitted timestamp parameters.

Kind parameters MUST accept an `EntitlementKindId` enum member name and resolve it to the corresponding enum member before invoking the entitlement domain. Valid names MUST be derived from the enum rather than duplicated in the CLI specification or implementation.

### `ffun entitlements grant`

Creates one durable entitlement grant for a source transaction, user, and entitlement kind.

Parameters:

- `--user-id UUID` — required id of the affected user.
- `--kind NAME` — required registered entitlement kind name.
- `--source ID` — semantic id of the source that owns the state; defaults to `system`.
- `--transaction-id ID` — required stable source-supplied id of the grant.
- `--value INTEGER` — required entitlement value.
- `--starts-at TIMESTAMP` — inclusive activation time in ISO 8601 format with an explicit UTC offset; defaults to the captured current timestamp.
- `--expires-at TIMESTAMP` — exclusive expiration time in ISO 8601 format with an explicit UTC offset; defaults to the shared lifetime interval end marker for a lifetime kind and to the captured current timestamp plus 31 days for every other kind.
- `--actor-kind {user|admin|psp|system}` — kind of the actor initiating the change; defaults to `admin`.
- `--actor-id ID` — stable id of the actor initiating the change; defaults to `admin`.

### `ffun entitlements revoke`

Revokes one existing source entitlement grant.

Parameters:

- `--user-id UUID` — required id of the affected user.
- `--kind NAME` — required registered entitlement kind name.
- `--source ID` — semantic id of the source that owns the state; defaults to `system`.
- `--transaction-id ID` — required stable source-supplied id of the grant to revoke.
- `--actor-kind {user|admin|psp|system}` — kind of the actor initiating the change; defaults to `admin`.
- `--actor-id ID` — stable id of the actor initiating the change; defaults to `admin`.

### `ffun entitlements list`

Lists effective entitlements at one evaluation time and prints one JSON object on its own line for every requested user and selected entitlement kind, including pairs whose entitlement is not granted.

Parameters:

- `--user-id UUID` — required affected-user filter; MAY be supplied multiple times.
- `--kind NAME` — optional entitlement-kind filter; MAY be supplied multiple times. When omitted, the command returns all registered entitlement kinds for every requested user.

Every output object MUST contain these fields:

- `user_id` — requested user id serialized as a UUID string.
- `kind` — entitlement kind enum member name.
- `kind_id` — stable integer value of the entitlement kind enum member.
- `granted` — whether an effective interval covers the command's evaluation time.
- `value` — effective integer value when granted, otherwise `null`.
- `starts_at` — inclusive start of the active effective interval as an ISO 8601 timestamp with an explicit UTC offset when granted, otherwise `null`.
- `expires_at` — exclusive end of the active effective interval as an ISO 8601 timestamp with an explicit UTC offset when granted, otherwise `null`.

All fields MUST be present in every output object. Records MUST preserve the first occurrence order of requested users. Kind records MUST preserve the first occurrence order of explicit kind filters, or entitlement registry order when the kind filter is omitted.

## Integration boundary

Entitlement commands MUST invoke the public `ffun.entitlements.domain` interface. They MUST NOT reproduce entitlement validation, merging, timeline materialization, audit, or business-event behavior.
