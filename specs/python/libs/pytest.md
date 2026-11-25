# Pytest conventions

## Goal of the document

This document describes conventions for writing Python tests with pytest.

## Scope

This specification applies to Python tests written with pytest and their supporting test code.

## Dictionary

- `autouse fixture` - a fixture that pytest applies automatically to tests that can access it.

## General principles

The [automated test conventions](../../programming/tests.md) and [Python test conventions](../tests.md) also apply to tests written with pytest.

## Fixtures

Tests SHOULD prefer an autouse fixture at the test class or test module level for preparing additional data needed by the relevant tests.

Keeping automatic setup close to the tests that depend on it makes their preconditions easier to find.

## Mocking

Tests SHOULD use monkeypatching as little as possible.

Tests MAY use specialized test tools for their own domain boundaries, for example `respx_mock` for HTTP client behavior.

### pytest-mock

This section applies to projects that use `pytest-mock`.

A test SHOULD use the `pytest-mock` `MockerFixture` when it must replace any of the following.

- a Python collaborator.
- a setting.
- a method.
- an attribute.

Use `mocker.patch("<import.path>", ...)` for imported module-level collaborators and settings.

Use `mocker.patch.object(...)` when replacing an attribute on an object or class already available in the test.

Use direct `unittest.mock.MagicMock` or `unittest.mock.AsyncMock` only for local fake objects or callables that are passed into the code under test.

Tests SHOULD NOT use pytest `monkeypatch` for ordinary Python attribute replacement.
Use `MockerFixture` for consistent cleanup and call assertions.
