# Entitlements CLI

## Goal of the document

This document describes the Feeds Fun CLI command family for managing and inspecting user entitlements.

## Scope

This specification covers the public `ffun entitlements` command family and the entitlement capabilities it exposes.

Entitlement domain rules, persistence, audit records, business events, and other CLI command families are out of scope. Exact output formats are not yet specified.

## Command group

The root CLI MUST expose `entitlements` as a command group.

The command group MUST provide CLI access to source entitlement changes, batch effective-entitlement checks, and expired effective-interval cleanup.

## Commands

The `grant` and `revoke` commands MUST capture one current timestamp and use it consistently to resolve omitted timestamp parameters.

Kind parameters MUST accept an `EntitlementKindId` enum member name and resolve it to the corresponding enum member before invoking the entitlement domain. Valid names MUST be derived from the enum rather than duplicated in the CLI specification or implementation.

### `ffun entitlements grant`

Stores a granted entitlement state for one source, user, and entitlement kind.

Parameters:

- `--user-id UUID` — required id of the affected user.
- `--kind NAME` — required registered entitlement kind name.
- `--source ID` — semantic id of the source that owns the state; defaults to `system`.
- `--value INTEGER` — required entitlement value.
- `--starts-at TIMESTAMP` — inclusive activation time in ISO 8601 format with an explicit UTC offset; defaults to the captured current timestamp.
- `--expires-at TIMESTAMP` — exclusive expiration time in ISO 8601 format with an explicit UTC offset; defaults to the captured current timestamp plus 31 days.
- `--actor-kind {user|admin|psp|system}` — kind of the actor initiating the change; defaults to `admin`.
- `--actor-id ID` — stable id of the actor initiating the change; defaults to `admin`.

### `ffun entitlements revoke`

Stores a revoked entitlement state for one source, user, and entitlement kind.

Parameters:

- `--user-id UUID` — required id of the affected user.
- `--kind NAME` — required registered entitlement kind name.
- `--source ID` — semantic id of the source that owns the state; defaults to `system`.
- `--starts-at TIMESTAMP` — inclusive activation time in ISO 8601 format with an explicit UTC offset; defaults to the captured current timestamp.
- `--expires-at TIMESTAMP` — exclusive expiration time in ISO 8601 format with an explicit UTC offset; defaults to the captured current timestamp plus 31 days.
- `--actor-kind {user|admin|psp|system}` — kind of the actor initiating the change; defaults to `admin`.
- `--actor-id ID` — stable id of the actor initiating the change; defaults to `admin`.

### `ffun entitlements check`

Checks effective entitlements at one evaluation time and prints a boolean result for every requested user and selected entitlement kind, including pairs whose result is false.

Parameters:

- `--user-id UUID` — required affected-user filter; MAY be supplied multiple times.
- `--kind NAME` — optional entitlement-kind filter; MAY be supplied multiple times. When omitted, the command returns all registered entitlement kinds for every requested user.

### `ffun entitlements cleanup`

Invokes the entitlement domain cleanup operation to delete expired effective entitlement intervals. It MUST NOT delete source entitlement rows.

The command has no parameters.

## Integration boundary

Entitlement commands MUST invoke the public `ffun.entitlements.domain` interface. They MUST NOT reproduce entitlement validation, merging, timeline materialization, audit, or business-event behavior.
