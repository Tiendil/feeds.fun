# Audit module

## Goal of the document

This document describes the responsibility and observable audit behavior of the `ffun.audit` backend module.

## Scope

This specification applies to durable audit evidence managed by `ffun.audit` for backend domain changes.
Business decisions about which changes require evidence, business-event notification, and reconstructing domain state from audit history are outside the module's responsibility.

## Dictionary

- `actor entity` - the entity that caused or initiated an audited occurrence.
- `subject entity` - the primary entity affected by or described by an audited occurrence.
- `audit entity kind` - a stable category that determines how an audited entity's identity is interpreted.

## Module responsibility

The module owns durable audit records, the validity and stable interpretation of audited entity references, append-only audit history, and the semantics of retrieving records for an exact subject.
Calling modules own the decision to create an audit record, event-specific validity and meaning, event details, and the business meaning of the actor and subject roles.

Audit records are durable business evidence.
Ordinary logs and business events MUST NOT replace required audit records, and audit history MUST NOT become the source of truth for rebuilding application state.

## Special module rules

`ffun.audit` is intentionally available to other top-level backend modules as an approved participant in their database transactions.
Its participation MUST remain limited to adding and retrieving audit records required by the calling workflow.
Participation MUST NOT transfer ownership of the workflow, its domain decisions, or its other state changes to `ffun.audit`.

## Domain model

An audit record is immutable, durable evidence of one audited occurrence.
It MUST have a unique and stable identity, identify when the evidence was created, preserve one stable event meaning and its event-specific details, and refer to exactly one actor entity and one subject entity.

Each actor and subject reference MUST combine one audit entity kind with a non-empty, unambiguous identity whose interpretation is stable within that kind.
The actor and subject MAY identify the same entity, but their roles in the audited occurrence MUST remain distinct.

The supported audit entity kinds are:

- a regular user.
- an administrator acting in an administrative capacity.
- a payment service provider.
- an internal automated component.

The meaning of an audit entity kind MUST remain stable after an audit record uses it.

## Domain behavior

### Recording and immutability

The module MUST allow a valid audit record owned by a calling workflow to be added to audit history.
Adding a record MUST NOT replace an existing record with the same identity.

Normal runtime behavior MUST NOT alter or remove an existing audit record.
A correction or reinterpretation MUST be represented by a new record whose meaning and details explain the correction.

### Subject history

The module MUST allow callers to retrieve every audit record for one exact subject kind and identity.
Matching records MUST be ordered by creation time and then by record identity, both ascending, and the result MUST be empty when no record matches.

Retrieving audit history MUST have no domain effects.

### Transaction participation

The module MUST support adding and retrieving audit records as part of an existing caller-owned database transaction.
When the transaction is caller-owned, its outcome remains under the calling workflow's authority and every audit effect MUST remain bound to that outcome.

Committing the transaction MUST make an added audit record durable, while rolling it back MUST leave no audit record from that addition.
Retrieval within the transaction MUST reflect the audit history visible to that transaction.

## Audit records

Each calling module owns the rule that determines whether one of its domain changes or requests requires an audit record and the semantic purpose of that record.
When audit evidence is required for a state change, the state change and its audit record MUST succeed or fail together.
An idempotent no-op SHOULD NOT produce an additional audit record unless the calling module defines the request itself as independently auditable.

## Business events

This module produces no business events.
