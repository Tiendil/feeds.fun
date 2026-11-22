# Frontend modules and roles

## Goal of the document

This document describes the Feeds Fun frontend layout by module and role.

## Scope

This specification applies to frontend source files under `site/src`.

## File and package layout

The frontend layout follows `specs/programming/modules_and_roles.md`.

The frontend MUST be implemented as a Vue 3 project under `site`.

Application source code MUST live under `site/src`.

## Modules

- `site/src` owns frontend application construction and cross-cutting frontend architecture tests.
- `site/src/assets` owns static assets such as icons, images, and similar frontend media.
- `site/src/components` owns reusable Vue components.
- `site/src/components/body_list` owns components for rendering entry body content and reference lists.
- `site/src/components/collections` owns components for collection browsing and subscription workflows.
- `site/src/components/main` owns shared main-content presentation components.
- `site/src/components/notifications` owns notification components.
- `site/src/components/page_footer` owns footer components.
- `site/src/components/page_header` owns header components.
- `site/src/components/side_pannel` owns side-panel controls.
- `site/src/components/tags` owns tag display and tag-filter components.
- `site/src/components/toolbar` owns reusable actions displayed in top content toolbars.
- `site/src/css` owns Tailwind-backed shared CSS.
- `site/src/inputs` owns small user-input components.
- `site/src/integrations` owns integration-specific frontend views or widgets.
- `site/src/layouts` owns top-level page layout components.
- `site/src/logic` owns shared frontend logic, API clients, constants, settings, and utilities.
  See the [frontend logic module specification](modules/logic.md).
- `site/src/plugins` owns Vue plugins.
- `site/src/router` owns Vue Router configuration.
- `site/src/stores` owns Pinia stores.
- `site/src/values` owns small display components for simple values.
- `site/src/views` owns page-level Vue views.

## Roles

Files that match no specific role placement rule have the Public or Private role permitted by their owning module.

- **Tests** — Source files under directories named `tests` at any depth contain their module's tests and test support code.
  Files with the Tests role MUST follow the [frontend Tests role specification](roles/tests.md).
- **Public** — Files with this role contain public interfaces specific to their module.
- **Private** — Files with this role contain implementation code specific to their module.

## Permitted module and role pairs

Every declared module MAY contain files with the Tests role.

The application module MAY contain files with the Private role.
Every other declared frontend module MAY contain files with the Public role.

## Dependencies and public interfaces

Dependency rules govern direct imports and named references to registered Vue components in templates.
They apply between governed frontend source files when the files have different roles or owning modules.
Direct imports include type-only imports, dynamic imports, and re-exports from another file.
The target of a template reference is the file that defines the registered component.

### Public interfaces

Files with the Public role are public import interfaces for their modules.
Registered Vue components defined in files with the Public role are public template interfaces for their modules.
Vue component imports and template references MUST follow the [frontend component architecture](components.md).

### Role dependencies

Role dependency rules apply when files with different roles belong directly to the same module.
Within that scope, the only permitted direction is from a file with the Tests role to a file with the Public or Private role.

### Module kinds

#### Definitions

- **Foundational modules** provide shared styles and static assets.
- **Shared-service modules** provide shared frontend logic, state, or Vue plugins.
- **Presentation modules** provide reusable frontend components.
- **View modules** compose the frontend content for individual pages.
- **Edge modules** own application construction or route selection.

#### Membership

- Foundational — `site/src/assets` and `site/src/css`.
- Shared-service — `site/src/logic`, `site/src/plugins`, and `site/src/stores`.
- Presentation — `site/src/components` and its declared nested modules, `site/src/inputs`, `site/src/integrations`, `site/src/layouts`, and `site/src/values`.
- View — `site/src/views`.
- Edge — the application module at `site/src` and `site/src/router`.

### Module dependencies

A dependency between modules is allowed only when this specification permits its direction.

- Foundational — Foundational.
- Shared-service — Foundational and Shared-service.
- Presentation — Foundational, Shared-service, and Presentation.
- View — Foundational, Shared-service, and Presentation.
- Edge — Foundational, Shared-service, Presentation, View, and Edge.

The `site/src/logic` module MAY depend on Vue components defined in files with the Public role in Presentation modules.

Views SHOULD compose layouts, components, inputs, values, stores, and logic.
Composition lets views coordinate pages using shared presentation and logic.

Shared logic SHOULD avoid depending on Vue components unless the dependency is explicitly UI-specific.
Limiting component dependencies keeps shared logic usable outside component rendering.
