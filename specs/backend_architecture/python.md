# Backend Python architecture

## Goal of the document

This document describes language-level implementation conventions for Python code in the Feeds Fun backend.

## Scope

This specification applies to Python code under `ffun/ffun` and covers project-wide conventions for using Python language features and runtime constructs.

Module ownership, domain behavior, entity modeling, error behavior, test organization, formatting, and third-party implementation details are out of scope.

## Dictionary

- `project-controlled class` — a class whose instance layout is defined by Feeds Fun code rather than generated or prescribed by a framework, library, standard-library protocol, metaclass, or inherited implementation contract.
- `instance dictionary` — the per-instance `__dict__` used to store dynamically named attributes.

## Runtime type validation

Functions called through project-controlled typed interfaces SHOULD treat annotated parameter types as caller contracts. They SHOULD NOT perform runtime checks solely to verify that arguments match their declared types.

Runtime validation remains appropriate at untyped or external boundaries, including HTTP input, CLI input, configuration, deserialized database rows, third-party responses, and plugin data.

Code MUST still validate semantic constraints that type annotations cannot express, such as non-empty identifiers, timezone awareness, numeric ranges, configured values, and valid cross-field combinations.

## Class instance layout

New or substantially changed project-controlled classes MUST define `__slots__` explicitly.

A class that introduces instance attributes MUST list every attribute it introduces in `__slots__`. A class that introduces no instance attributes MUST use `__slots__ = ()`.

Every project-controlled subclass MUST define its own `__slots__`, including an empty declaration when it introduces no attributes. A subclass MUST NOT repeat slot names owned by a base class.

Classes MUST NOT include `__dict__` in `__slots__` unless dynamically named instance attributes are an intentional part of the class contract. Classes MUST include `__weakref__` only when instances need weak-reference support and no base class already provides it.

Existing classes SHOULD NOT be changed solely to adopt `__slots__`. They MUST adopt this convention when their instance layout or implementation is substantially changed, unless an exception below applies.

### Exceptions

A class MAY omit an explicit `__slots__` declaration when one or more of the following conditions apply:

- a base class already provides an instance dictionary and preserving that inherited layout is required, so a subclass declaration would not provide the intended restriction.
- a framework, library, standard-library protocol, metaclass, or generated implementation owns the instance layout or requires dynamic attributes.
- dynamically named instance attributes are intentional behavior of the class.
- a concrete serialization, proxying, instrumentation, pickling, or interoperability requirement is incompatible with a slotted instance layout.

Common examples include Pydantic models, enum classes, exception classes, protocols, and framework-defined subclasses whose parent implementation controls instance storage.

When the reason for omitting `__slots__` is not evident from the base class or implemented protocol, the class MUST have an adjacent comment that states the concrete reason.

### Verification

Static analysis or backend architecture tests SHOULD enforce this convention. Ordinary behavioral tests SHOULD NOT inspect `__slots__` merely to restate a class declaration.
