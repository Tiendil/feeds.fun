# Python code conventions

## Goal of the document

This document describes language-level implementation conventions for Python source code.

## Scope

This specification applies to Python source code and covers conventions specific to Python.
Project-specific architectural requirements are out of scope.

## Dictionary

- `project-controlled class` — a class whose instance layout is defined by project code rather than generated or prescribed by a framework, library, standard-library protocol, metaclass, or inherited implementation contract.
- `test class` — a class defined only to organize or support automated tests.

## Enumeration types

String-valued enums SHOULD use `enum.StrEnum`.
Integer-valued enums SHOULD use `enum.IntEnum`.
These classes provide standard string and integer behavior for enum members used as primitive values.

## Exhaustiveness checking

Code that exhaustively branches over an enum or another statically closed union SHOULD pass the unreachable value to `typing.assert_never()` instead of raising `AssertionError` directly.

**Rationale:** Unlike directly raising `AssertionError`, `typing.assert_never()` requires static confirmation that no possible value remains.

Ordinary domain or validation exceptions remain appropriate when an unsupported value can legitimately arrive through an untyped or external boundary.

## Semantic primitive types

Mappings keyed by semantic ids SHOULD use the semantic id type when possible.

Semantic primitive types SHOULD use `typing.NewType` when runtime behavior is identical to the underlying primitive.
This lets a type checker distinguish values with different meanings that share the same runtime type.
For example, a type checker can reject a `CustomerId` argument to a function expecting an `OrderId` when both types are defined over `int`.

Semantic primitive types SHOULD be owned by the module that owns the corresponding concept.

## Optional values

Optional values in internal Python code MUST be represented with `None` instead of sentinel strings.

## Class instance layout

Explicit instance layouts prevent unintended instance `__dict__` storage and dynamically named state, and they keep attribute ownership predictable across inheritance.
`__slots__` is required for covered classes because it enforces this layout constraint at the Python class boundary.

New or substantially changed project-controlled classes other than test classes MUST define `__slots__` explicitly.
Test classes are excluded from this convention and MAY omit `__slots__` without an explanatory comment.

A class that introduces instance attributes MUST list every attribute it introduces in `__slots__`.
A class that introduces no instance attributes MUST use `__slots__ = ()`.

Every project-controlled subclass covered by this convention MUST define its own `__slots__`, including an empty declaration when it introduces no attributes.
A subclass MUST NOT repeat slot names owned by a base class.

Classes MUST NOT include `__dict__` in `__slots__` unless dynamically named instance attributes are an intentional part of the class contract.
Classes MUST include `__weakref__` only when instances need weak-reference support and no base class already provides it.

Existing classes MUST adopt this convention when their instance layout or implementation is substantially changed, unless an exception below applies.

### Exceptions

A class MAY omit an explicit `__slots__` declaration when one or more of the following conditions apply:

- a base class already provides `__dict__` for instances and preserving that inherited layout is required, so a subclass declaration would not provide the intended restriction.
- a framework, library, standard-library protocol, metaclass, or generated implementation owns the instance layout or requires dynamic attributes.
- dynamically named instance attributes are intentional behavior of the class.
- a concrete serialization, proxying, instrumentation, pickling, or interoperability requirement is incompatible with a slotted instance layout.

Common examples include Pydantic models, enum classes, exception classes, protocols, and framework-defined subclasses whose parent implementation controls instance storage.

When the reason for omitting `__slots__` is not evident from the base class or implemented protocol, the class MUST have an adjacent comment that states the concrete reason.
