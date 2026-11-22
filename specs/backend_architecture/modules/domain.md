# Domain module

## Goal of the document

This document describes requirements for shared semantic identifier ownership in the `ffun.domain` backend module.

## Scope

This specification applies to semantic identifiers owned by `ffun.domain` and to ownership decisions for semantic identifiers shared by independent domain-level modules.

## Module responsibility

Semantic identifiers owned by `ffun.domain` MUST be dependency-neutral and shared across independent domain modules.

A semantic identifier shared by independent domain-level modules SHOULD belong to `ffun.domain` when placing it in a narrower owning module would reverse the intended dependency direction or create a cycle.
