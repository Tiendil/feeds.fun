# Pydantic conventions

## Goal of the document

This document describes conventions for defining and using Pydantic models.

## Scope

This specification applies to Python code that uses Pydantic v2 for data modeling and to tests of that code.

## Validators

Pydantic validators MUST NOT themselves read the filesystem.

## Validation errors

Code that uses Pydantic to construct or validate application values MUST catch `pydantic.ValidationError` and translate it into the appropriate domain error before it propagates, unless the application's error contract explicitly permits propagation.
The translation MUST follow the application's error contract and include useful context.

## Serialization

Boundary code that needs a model dump or JSON SHOULD use Pydantic serialization methods explicitly.

## Testing

Tests that exercise Pydantic validation directly MAY assert `pydantic.ValidationError`.
