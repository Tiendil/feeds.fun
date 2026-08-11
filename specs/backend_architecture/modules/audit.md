# Audit module

## Goal of the document

This document describes the public contract and observable behavior of the `ffun.audit` backend module.

## Scope

This specification covers durable audit records, actor and subject references, append-only behavior, transactional record creation, and subject-based record loading.

General audit search, pagination, retention and archival policy, administrative presentation, business-event definitions owned by calling modules, and event sourcing are out of scope.

## Dictionary

- `actor entity` - the entity that caused or initiated the audited event.
- `subject entity` - the primary entity affected by or described by the audited event.
- `related entity` - an additional entity associated with the event but not acting as its actor or primary subject.
- `audit entity kind` - a stable category that determines how an audit entity id is interpreted.

## Module responsibility

The module MUST own the common audit-record contract, stable audit entity kinds, append-only persistence, unique audit-record identifiers, and subject-based record loading.

Calling modules MUST own the decision to create an audit record, event-specific validation, event names, event attributes, and the business meaning of the actor and subject.

`ffun.audit` is an approved transaction participant under the backend database architecture.
Calling modules MAY use its public domain interface for audit persistence in their transactions without workflow-specific transaction-sharing approval.
This participation MUST NOT transfer ownership of the calling workflow or its database operations to `ffun.audit`.

Audit records MUST be durable business evidence.
They MUST NOT be replaced by ordinary logs or business events, and they MUST NOT be used as the source of truth for rebuilding application state.

## Domain behavior

### Entity references

Every audit record MUST contain exactly one actor reference and one subject reference.
Each reference MUST contain an audit entity kind and a canonical non-empty string identifier.

The supported audit entity kinds MUST include regular users, administrators acting in an administrative capacity, payment service providers, and internal automated components.
The meaning of a kind MUST remain stable after records use it.

Actor and subject references MAY have the same kind or identifier, but their roles MUST remain distinct.

Additional related entities MAY be included in event attributes.
Each related-entity attribute MUST identify the related entity's kind and id and MAY describe its role.

### Audit record contract

An audit record MUST contain:

- a unique record identifier.
- its creation time.
- a stable event name.
- the actor kind and identifier.
- the subject kind and identifier.
- event-specific structured attributes.

Event names MUST be non-empty `snake_case` values.
They SHOULD describe the audited business change rather than the operation or endpoint that produced it.

Attributes MUST be a structured object.
They SHOULD contain only information required to understand the audited change, such as previous and new values, provider references, or related entities.

Record identifiers MUST be unique.
Creation time MUST represent when the record becomes durable.

### Append-only behavior

Normal runtime behavior MUST only append audit records.
The module MUST NOT provide public behavior that updates or deletes an individual record.

An existing record MUST NOT be changed to correct or reinterpret it.
A correction MUST be represented by a new event whose meaning and attributes explain the correction.

Creating a record MUST NOT replace an existing record with the same identifier.

### Subject-based loading

The module MUST allow callers to load records for one exact subject kind and identifier.
The result MUST contain every matching record ordered by creation time and then record identifier, both ascending.
It MUST be empty when no record matches.

Loading records MUST be read-only and MUST NOT generate audit records, business events, or ordinary business logs.

## Public interface

The public interface MUST provide these operations:

- `new_audit_record_id` returns a new unique audit-record identifier.
- `record` appends one audit record and returns its identifier.
- `load_records_for_subject` returns the ordered records for one subject identity.

`record` MUST accept a caller-provided transaction execution context, event name, actor kind and identifier, subject kind and identifier, and optional attributes.
The attributes MUST default to an empty object.
The caller MUST provide already validated and canonically serialized values.

`record` MUST participate in the caller's transaction.
It MUST NOT independently open, commit, or roll back a transaction.
A record required for a state change MUST be appended through the same transaction context as that state change.
Failure to append it MUST fail the caller-owned transaction, and rollback MUST leave no record.

Callers SHOULD invoke `record` only for changes that actually occurred.
An idempotent no-op SHOULD NOT create a duplicate record unless the request itself is explicitly defined as auditable.

`load_records_for_subject` MUST accept a caller-provided transaction execution context and one subject identity.
It MUST use that context without independently managing a transaction.

## Audit records

Module does not define concrete audit events because calling modules own their event contracts.

## Business events

Module does not produce business events.
