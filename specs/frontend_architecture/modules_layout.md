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

## Project layout

The frontend MUST be implemented as a Vue 3 project under `site`.

Application source code MUST live under `site/src`.

Frontend tests SHOULD live near the logic they verify when the existing Vitest layout supports it.

## Modules

- `site/src/assets` owns static assets such as icons, images, and similar frontend media.
- `site/src/components` owns reusable Vue components.
- `site/src/components/body_list` owns components for rendering entry body content and reference lists.
- `site/src/components/collections` owns components for collection browsing and subscription workflows.
- `site/src/components/main` owns shared main-content presentation components.
- `site/src/components/notifications` owns notification components.
- `site/src/components/page_footer` owns footer components.
- `site/src/components/page_header` owns header components.
- `site/src/components/side_pannel` owns side-panel controls. The existing directory spelling is part of the current project layout.
- `site/src/components/tags` owns tag display and tag-filter components.
- `site/src/css` owns Tailwind-backed shared CSS.
- `site/src/inputs` owns small user-input components.
- `site/src/integrations` owns integration-specific frontend views or widgets.
- `site/src/layouts` owns top-level page layout components.
- `site/src/logic` owns shared frontend logic, API clients, constants, settings, and utilities.
- `site/src/plugins` owns Vue plugins.
- `site/src/router` owns Vue Router configuration.
- `site/src/stores` owns Pinia stores.
- `site/src/values` owns small display components for simple values.
- `site/src/views` owns page-level Vue views.

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
