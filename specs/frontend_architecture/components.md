# Frontend component architecture

## Goal of the document

This document describes the architecture, registration, naming, and composition conventions for Feeds Fun frontend components.

## Scope

This specification applies to Vue components intended for use in application templates under `site/src`.
Route resolution, component-specific behavior, styling, state-management design, and frontend test organization are out of scope.

## Dictionary

- `application component` - a first-party or third-party Vue component intended for use in an application template.
- `global component registry` - the component registrations performed on the Vue application in `site/src/main.ts`.
- `route view` - a page-level Vue component loaded directly by Vue Router.
- `local component import` - importing a Vue component into another Vue component source file for use in that file's template.

## Component contracts

Components SHOULD expose data through typed properties and interactions through typed events.
Components SHOULD keep their public contract independent of the identity of their parent component.
Reusable components MUST NOT depend on page-level views.

## Global component registration

`site/src/main.ts` MUST be the single global component registry.
Every application component used in a Vue template MUST be imported by `site/src/main.ts` and registered with `app.component` before the application is mounted.
A Vue component source file MUST NOT import another Vue component for use in its template.
Templates MUST reference child components through their global registration names.
Central registration is an intentional architectural constraint because it provides one auditable inventory of template components, prevents divergent local aliases, and keeps component availability consistent throughout the application.

## Registration names

Every global component registration name MUST be unique.
Registration names MUST use PascalCase.
Components stored in feature-specific submodules SHOULD include a feature prefix when the unqualified filename would be ambiguous, such as `FeedListColumns` for `components/feed_list/Columns.vue`.
Templates MAY use the kebab-case equivalent of a registered PascalCase name.

## Exceptions

`App.vue` MAY be imported directly by `site/src/main.ts` as the application root and does not need a global registration.
Route views MAY be imported directly by the router when they are used only as route targets.
Tests MAY import components directly when mounting or inspecting the component under test.
A route view used inside another component's template becomes an application component and MUST follow the global registration requirements.
