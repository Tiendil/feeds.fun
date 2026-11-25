# Project dictionaries

## Goal of the document

This document describes conventions for project-level dictionaries and shared project terminology.

## Scope

This specification applies to project-level dictionaries and the placement and use of shared project terminology in repositories that maintain them.
The abbreviation entry format also applies to local dictionaries in specifications.

## Dictionary

- `project-maintained specification` — a specification authored and maintained by the repository rather than imported for reuse.

## Dictionary availability

A repository MAY maintain a project-level dictionary.
When present, the project-level dictionary MUST be located at `./specs/dictionary.md`.

## Definition placement

When a repository maintains a project-level dictionary, it SHOULD define a project-specific term used by multiple project-maintained specifications if readers cannot reliably infer its meaning from context and need that meaning to interpret or apply a requirement.
A project-maintained specification's local `Dictionary` section SHOULD contain only terms specific to that specification.

## Abbreviation entries

An abbreviation entry MUST put the abbreviation in inline code and use spaced em dashes to separate the abbreviation, its expansion, and its definition.

```markdown
- `DTO` — Data Transfer Object — a typed object that carries structured application data or parsed intent.
```

## Terminology use

Project artifacts MUST use dictionary terms with their defined spelling and meaning when referring to the corresponding project concepts.

**Example:** A project dictionary may define `rule` as a user-defined scoring expression.
That definition does not change the meaning of a general formatting rule in an imported specification.
