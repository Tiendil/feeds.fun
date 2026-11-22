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

Paths in role placement rules are relative to the source directory of the file's most specific declared module.

Files that match no specific role placement rule have the Public or Private role permitted by their owning module.

- **Tests** — Source files under directories named `tests` at any depth contain their module's tests and test support code.
  Files with the Tests role MUST follow the [frontend Tests role specification](roles/tests.md).
- **Public** — Files with this role contain public interfaces specific to their module.
- **Private** — Files with this role contain implementation code specific to their module.

## Permitted module and role pairs

Every declared module MAY contain files with the Tests role.

The application module MAY contain files with the Private role.
Every other declared frontend module MAY contain files with the Public role.
