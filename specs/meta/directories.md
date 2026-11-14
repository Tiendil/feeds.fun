# Specification directories

## Goal of the document

This document describes conventions for organizing specification files into subject areas.

## Scope

This specification applies to the file system organization of specification documents under `./specs/`.
The internal structure of individual specification documents is out of scope.

## Subject areas

An area groups specifications by the subject matter they govern.
Area directories MUST be direct children of `./specs/`.
An area MAY contain subdirectories that group its specifications by stable concerns.

**Example:** In a path such as `./specs/python/libs/pydantic.md`, `python` is the area, `libs` groups library specifications, and `pydantic.md` is a specification within that area.

An area directory's name MUST identify durable subject matter shared by its specifications.
Subject areas MAY overlap; directory boundaries MUST NOT imply that a subject belongs exclusively to one area.

Requirements specific to one subject area MUST be placed in that area's directory, including requirements for specifications about that subject.

### Area catalog

The area catalog is extensible.
The area catalog MUST NOT be extended without prior explicit permission from the developer.
New areas MUST be recorded in the catalog with descriptions of their subject matter.

- `meta` — General requirements governing specification documents across subject areas.
- `programming` — Program implementations and specifications about them.

## Specification placement

A specification MUST have one canonical location.
Placement in an area directory MUST follow the specification's primary subject matter.
When several areas use a specification, they MUST reference the canonical file rather than maintain copies of it.

**Example:** A specification about statistical validation may be placed in `statistics` and referenced by a programming task that needs the same requirements.
It does not need a duplicate under `programming`.

## Applicability

The applicability of a specification MUST be stated explicitly.
Directory membership alone MUST NOT establish applicability, inheritance, or precedence.
