# Frontend module structure

## Goal of the document

This document describes the frontend module structure of Feeds Fun.

## Scope

The scope of this specification is limited to the list of frontend modules and their intended responsibilities.

The following topics are out of scope:

- detailed implementation design.
- backend API implementation.
- Docker configuration.
- generated frontend build artifacts.
- runtime behavior.
- component styling conventions.
- entity and test conventions beyond module placement.

## Dictionary

- `test submodule` - a directory or file containing tests for a corresponding frontend module or submodule.

## Submodules

Some submodules have specific names that reflect their responsibilities and SHOULD be similar across different frontend modules.

List of specific submodules:

- `tests` - submodule containing module tests.

Test submodules MUST follow the frontend test architecture specification when they are present.

## Dependency direction

Views SHOULD compose layouts, components, inputs, values, stores, and logic.

Reusable components SHOULD avoid depending on page-level views.

Shared logic SHOULD avoid depending on Vue components unless the dependency is explicitly UI-specific.
