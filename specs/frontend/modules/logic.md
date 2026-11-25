# Frontend logic module

## Goal of the document

This document describes requirements for the Feeds Fun frontend logic module.

## Scope

This specification applies to the navigation fragment identifiers owned by `site/src/logic` and the frontend code that defines or uses them.

## Navigation fragment ownership

Section identifiers used to build URL fragments MUST have a single source of truth in `site/src/logic/navigation.ts`.
Destination views and navigation callers MUST derive element `id`, link `href`, and router `hash` values from those shared definitions instead of repeating fragment identifier string literals.
Shared section identifiers MUST omit the leading `#`; navigation code MUST derive URL hash values from the identifier.
