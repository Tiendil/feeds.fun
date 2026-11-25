# TypeScript test conventions

## Goal of the document

This document describes naming conventions for TypeScript tests.

## Scope

This specification applies to tests written in TypeScript.

## General principles

The [automated test conventions](../programming/tests.md) also apply to TypeScript tests.

## Test file naming

TypeScript test files MUST use the `.test.ts` suffix, as in `tests/<module>.test.ts`.

## Test group naming

Test groups for a single exported function, component, or store SHOULD use the name of that subject.

Matching names make the tests for a subject easier to find.
