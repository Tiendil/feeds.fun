# Errors role

## Goal of the document

This document describes requirements for Python code with the Errors role (`errors.py`) and for error definitions elsewhere in the Feeds Fun backend.

## Scope

This specification applies to backend error definitions in Python source files under `ffun/ffun`, including test-only error classes.

## Dictionary

- `module root error` - the `Error` exception class in a top-level module's `errors` Python module that serves as the root for fatal errors owned by that module and its nested modules.

The [backend error architecture](../errors.md) defines fatal errors and how the backend handles them.

## Error definitions

Errors SHOULD express failures in terms of the module's responsibilities so callers can decide how to respond.

Production errors MUST be defined in production files.
Test files MAY define test-only error classes when they need them to verify error handling.

## Error hierarchy

The backend MUST define a single project root exception type for all expected fatal project errors.

The project root exception MUST be named `Error`.

The project root exception MUST inherit from `Exception`.

The project root exception MUST be owned by `ffun.core.errors`.

Each top-level module that owns fatal errors directly or through a nested module SHOULD define one module root error class.

A module root error class MUST be named `Error`.

The project root exception also serves as the `ffun.core` module root error.
Every other module root error class MUST inherit from the project root exception.

Concrete fatal error classes MUST inherit from the root error class of their top-level module.

Module root error classes SHOULD be abstract classification classes and SHOULD NOT be raised directly when a more specific concrete error is available.

Intermediate abstract error classes MAY exist under a module root when a top-level or nested module needs a narrower ownership boundary.
