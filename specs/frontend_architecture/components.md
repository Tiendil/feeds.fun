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
Typed contracts make component integration statically checkable, while parent-independent boundaries reduce coupling so components remain safe to compose and refactor.

## Screen-reader support

Screen-reader compatibility is not currently a supported frontend target.
Components SHOULD keep visible markup self-explanatory and MAY use native semantic HTML where it naturally matches the visible content.
Components SHOULD NOT introduce screen-reader-only copy, hidden accessibility-only structure, or custom ARIA interaction behavior unless a governing specification explicitly requires it.
Compact read-only displays SHOULD use the simplest markup that accurately represents their visible presentation.
They SHOULD NOT use additional semantic structures solely to provide an alternative screen-reader representation.
This limitation does not prohibit low-cost accessibility metadata, such as an accessible label for an otherwise unlabeled icon button.

## Tooltips

New application tooltip implementations MUST use the globally registered `AppTooltip` component.
Centralized tooltip ownership is an intentional architectural constraint because it keeps interaction and positioning behavior consistent, applies fixes through one implementation, and prevents feature-specific tooltip behavior from diverging.
Native `title` attributes MUST NOT be introduced for new application tooltips.
Existing `title`-based tooltips MAY remain unchanged until they are deliberately migrated.
Semantic uses of a `title` attribute, such as naming an embedded document, are not application tooltips and MAY remain native attributes.
`AppTooltip` MUST support concise plain-text content through its `text` property and structured content with intentional line breaks through its `content` slot.
`AppTooltip` MUST receive exactly one rendered element in its default trigger slot.
`AppTooltip` MUST display on pointer hover and keyboard focus, MUST be dismissible with the Escape key, and MUST support touch activation.
`AppTooltip` MUST keep its rendered content within the viewport and MUST NOT change the layout of its trigger.
Tooltip content MUST remain supplementary; information required to understand or complete an action MUST remain visible outside the tooltip.

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
A Vue component MAY locally import component definitions that it treats as values and renders through a dynamic `<component :is>` binding.
Such implementation components do not require global registration when the wrapper component is globally registered and its template does not reference them by component name.
