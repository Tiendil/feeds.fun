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

- `frontend module` - a directory under `site/src` that owns a coherent area of frontend functionality.
- `frontend submodule` - a directory inside a frontend module that owns a narrower part of its parent module's functionality.
- `test submodule` - a directory or file containing tests for a corresponding frontend module or submodule.

## Submodules

Frontend modules can have submodules that are responsible for more specific parts of the parent module's functionality.

When a module contains a small closed family of components or helpers, and each component or helper has meaningful component-specific behavior, the module SHOULD prefer one implementation submodule per family.

Shared package-level code for such component families SHOULD be limited to common types, shared presentation helpers, selection helpers, and iteration glue.

Some submodules have specific names that reflect their responsibilities and SHOULD be similar across different frontend modules.

List of specific submodules:

- `tests` - submodule containing module tests.
- feature-specific component submodules - submodules grouping reusable components for one frontend feature or presentation area.

Test submodules MUST follow the frontend test architecture specification when they are present.

## Dependency direction

Views SHOULD compose layouts, components, inputs, values, stores, and logic.

Reusable components SHOULD avoid depending on page-level views.

Shared logic SHOULD avoid depending on Vue components unless the dependency is explicitly UI-specific.

## Navigation fragment ownership

Section identifiers used to build URL fragments MUST have a single source of truth in `site/src/logic/navigation.ts`.
Destination views and navigation callers MUST derive element `id`, link `href`, and router `hash` values from those shared definitions instead of repeating fragment identifier string literals.
Shared section identifiers MUST omit the leading `#`; navigation code MUST derive URL hash values from the identifier.
