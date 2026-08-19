# CLI behavior

## Goal of the document

This document describes the stable shared behavior of the Feeds Fun backend command-line interface.

## Scope

This specification covers the root backend command and behavior shared by its specified command families.

Domain behavior, command-family-specific contracts, and frontend interfaces are out of scope.

## Root command

The backend CLI MUST be invoked as `ffun` and MUST use a root command group.

Public command families and standalone commands MUST be exposed as root subcommands. A command family MAY define nested commands for its operations.

Command names, arguments, options, output, and errors defined by command-family specifications are stable public contracts.

## Root subcommands

The root command MUST expose the following command groups:

- `cleaner` — Cleans orphaned data and expired effective entitlements, and runs tag and feed normalization operations.
- `debug` — Loads and inspects feeds through the available parsing paths.
- [`entitlements`](cli/entitlements.md) — Manages source entitlements and lists effective entitlements.
- `estimates` — Estimates entry publication rates for feeds and collections.
- `experiments` — Runs ad hoc backend data experiments.
- `feeds` — Performs administrative operations on feeds and their user links.
- `fixtures` — Populates the database with development fixture data.
- `metrics` — Reports system-level and per-user operational metrics.
- `processors-quality` — Evaluates processor output and maintains processor quality reference data.
- `profile` — Runs ad hoc backend profiling scenarios.
- `queues` — Cleans all or selected processing queues.
- [`subscriptions`](cli/subscriptions.md) — Lists purchased-subscription snapshots.
- `user-settings` — Performs maintenance of persisted user settings.
- `users` — Performs user administration and identity-provider imports.

The root command MUST expose the following standalone commands:

- `dispatcher-failed-entries-count` — Reports failed entry counts for each processor.
- `dispatcher-failed-entries-move-to-queue` — Moves failed entries back to a selected processor queue.
- `migrate` — Applies pending database migrations.
- `normalize-entries` — Detects and optionally applies entry normalization changes.
- `print-configs` — Prints the settings discovered for backend components.
- `workers` — Runs selected background workers until stopped.
