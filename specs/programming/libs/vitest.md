# Vitest conventions

## Goal of the document

This document describes conventions for writing tests with Vitest.

## Scope

This specification applies to tests written with Vitest and their test environment.

## Dictionary

- `DOM test` - a test that uses the Vitest `jsdom` environment to verify browser-facing behavior.

## General principles

The [automated test conventions](../tests.md) also apply to tests written with Vitest.
Tests written in TypeScript also follow the [TypeScript test conventions](../typescript.tests.md).

## Test groups

Tests for one exported function, component, or store SHOULD be grouped in one `describe` block.

Grouping tests by subject keeps their cases and shared setup together.

## Browser environment

Tests SHOULD prefer the configured `jsdom` environment over mocked collaborators.

Logic tests that inspect HTML or browser APIs MUST use the configured `jsdom` environment.

The configured environment gives tests a consistent DOM and browser APIs.
