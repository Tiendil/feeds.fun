# Python test conventions

## Goal of the document

This document describes conventions for writing and organizing Python tests.

## Scope

This specification applies to Python test code and its supporting modules.

## General principles

The [automated test conventions](../programming/tests.md) also apply to Python tests.

## Test file naming

Python test files MUST use the `test_` prefix and the `.py` extension, as in `tests/test_<module>.py`.

## Test classes and methods

Each production module-level function MUST have a corresponding test class.

Tests for a class MUST group method tests inside the class's test class.

Test classes MUST use `Test<SubjectName>` naming, where `<SubjectName>` is the tested function or class name converted to PascalCase.

**Example:** Tests for the function `normalize_url` belong in `class TestNormalizeUrl`.
Tests for the class `FeedLoader` belong in `class TestFeedLoader`.
Tests for the class `Resource` belong in `class TestResource`.

Tests for a class method MUST use this method name format:

```text
test_<method_name>__<test_name>
```

`<method_name>` MUST be the tested method name in snake case.

`<test_name>` MUST describe the execution path or behavior being verified in snake case.

**Example:** Test method names include `test_normalize__empty_value`, `test_process__provider_returns_error`, and `test_replace_tags__circular_replacement`.

When a test class tests one module-level function, test methods MAY omit the function name and use this format:

```text
test_<test_name>
```

**Example:** `TestNormalizeUrl.test_success`, `TestNormalizeUrl.test_invalid_scheme`, and `TestNormalizeUrl.test_trailing_slash` use this format.

## Test support modules

Test data constructors reused by multiple test modules in the same package SHOULD live in `make.py` within that package's test directory.

`make.py` SHOULD contain small factory functions that create valid entities, value objects, queue items, and other domain data for tests.

`make.py` MUST NOT contain assertions or behavior-verification helpers.

Test helper functions reused by multiple test modules in the same package SHOULD live in `helpers.py` within that package's test directory.

`helpers.py` SHOULD contain assertion helpers, cleanup helpers, and test workflow utilities.

`helpers.py` MUST NOT contain ordinary domain data constructors when those constructors fit `make.py`.

## Entity tests

Entity tests MUST NOT verify plain `NewType`, enum member existence, or passive data-container fields unless the module owns non-trivial conversion, validation, serialization, persistence compatibility, API compatibility, or external-input compatibility behavior for them.

## Assertions

Tests MAY use `assert value is None` and `assert value is not None` when checking for `None`.

Tests MAY use `assert <value> is <other_value>` or `assert <value> is not <other_value>` for non-`None` values only when object identity is the explicit behavior under test, such as checking singleton values, module re-exports or aliases, or registry/cache/container APIs that promise to return the exact registered or stored object instance.

Tests with non-`None` identity assertions SHOULD make the identity contract clear through the test name, setup, or surrounding assertion context.

Tests MUST NOT use identity assertions for boolean values.
Use `assert condition` instead of `assert condition is True`, and `assert not condition` instead of `assert condition is False`.
