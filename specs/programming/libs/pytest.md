# Pytest conventions

## Goal of the document

This document describes conventions for writing Python tests with pytest.

## Scope

This specification applies to Python tests written with pytest and their supporting test code.

## Dictionary

- `autouse fixture` - a fixture that pytest applies automatically to tests that can access it.

## General principles

The [automated test conventions](../tests.md) also apply to tests written with pytest.

## Fixtures

Tests SHOULD prefer an autouse fixture at the test class or test module level for preparing additional data needed by the relevant tests.

Keeping automatic setup close to the tests that depend on it makes their preconditions easier to find.

## Assertions

Tests MAY use `assert value is None` and `assert value is not None` when checking for `None`.

Tests MAY use `assert <value> is <other_value>` or `assert <value> is not <other_value>` for non-`None` values only when object identity is the explicit behavior under test, such as checking singleton values, module re-exports or aliases, or registry/cache/container APIs that promise to return the exact registered or stored object instance.

Tests with non-`None` identity assertions SHOULD make the identity contract clear through the test name, setup, or surrounding assertion context.

Tests MUST NOT use identity assertions for boolean values.
Use `assert condition` instead of `assert condition is True`, and `assert not condition` instead of `assert condition is False`.

## Mocking

Tests SHOULD use monkeypatching as little as possible.

Tests MAY use specialized test tools for their own domain boundaries, for example `respx_mock` for HTTP client behavior.

### pytest-mock

This section applies to projects that use `pytest-mock`.

When a test must replace a Python collaborator, setting, method, or attribute, it SHOULD use the `pytest-mock` `MockerFixture`.

Use `mocker.patch("<import.path>", ...)` for imported module-level collaborators and settings.

Use `mocker.patch.object(...)` when replacing an attribute on an object or class already available in the test.

Use direct `unittest.mock.MagicMock` or `unittest.mock.AsyncMock` only for local fake objects or callables that are passed into the code under test.

Tests SHOULD NOT use pytest `monkeypatch` for ordinary Python attribute replacement.
Use `MockerFixture` for consistent cleanup and call assertions.
