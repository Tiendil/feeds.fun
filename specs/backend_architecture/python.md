# Backend Python architecture

## Goal of the document

This document describes language-level implementation conventions for Python code in the Feeds Fun backend.

## Scope

This specification applies to Python code under `ffun/ffun` and covers project-wide conventions for using Python language features and runtime constructs.

Module ownership, domain behavior, entity modeling, error behavior, test organization, formatting, and third-party implementation details are out of scope.

## Dictionary

- `project-controlled class` — a class whose instance layout is defined by Feeds Fun code rather than generated or prescribed by a framework, library, standard-library protocol, metaclass, or inherited implementation contract.
- `test class` — a class defined only to organize or support automated tests.
- `instance dictionary` — the per-instance `__dict__` used to store dynamically named attributes.

## Runtime type validation

Functions called through project-controlled typed interfaces SHOULD treat annotated parameter types as caller contracts. They SHOULD NOT perform runtime checks solely to verify that arguments match their declared types.

Runtime validation remains appropriate at untyped or external boundaries, including HTTP input, CLI input, configuration, deserialized database rows, third-party responses, and plugin data.

Code MUST still validate semantic constraints that type annotations cannot express, such as non-empty identifiers, timezone awareness, numeric ranges, configured values, and valid cross-field combinations.

Code that constructs a semantically specific typed value from raw or untyped data MUST validate the semantic invariants of that type at the construction boundary.
Functions and methods that receive the constructed typed value MUST assume those invariants hold and MUST NOT repeat their validation.

## Temporary implementation code

Production code intentionally introduced as a temporary bridge MUST include an adjacent `TODO` comment.
Keeping the explanation next to the bridge makes the exception discoverable during maintenance and review and couples its removal to the code it qualifies; a separate tracked work item alone does not preserve that local context.
The comment MUST explain why the temporary code is currently necessary and identify the concrete condition, milestone, or tracked work item after which it MUST be removed.
Vague comments such as "remove later" are insufficient.
The comment MUST be removed together with the temporary code.

## Closed value sets

Project-owned closed sets of named values SHOULD use enums instead of `typing.Literal`.
`Literal` MAY be used when exact literal values are required by an external or framework-defined interface, as discriminators for typed unions, or when the values do not represent independently named project concepts.
Enums give project concepts one nominal runtime type with discoverable members, reducing duplicated literal unions and raw constants across typed interfaces.

Explicit values keep member identities independent from declaration order or generated naming rules.
Project-owned enum members MUST use explicit values and MUST NOT use `enum.auto()`.
Project-owned enum values persisted in application-owned storage MUST be fixed integers.
Fixed integers decouple persisted identities from human-readable names, align with the project's categorical persistence conventions, and allow names to change without changing stored values.
Assigned persisted integer values MUST NOT be changed or reused.

Project-owned enum values that are not persisted MAY use another explicit representation when it makes their runtime semantics clearer or represents an intentional boundary protocol token.
API-boundary enums MAY use explicit string values when human-readable wire values are an intentional part of the API contract.
Such string values MUST be treated as stable compatibility identifiers and MUST NOT be changed or reused without an explicit compatibility transition.
Non-persisted enum values that participate in serialization, configuration, an external-system protocol, or another compatibility contract MUST use an explicit stable representation appropriate to that boundary.
When internal and boundary representations have independent compatibility lifecycles, code SHOULD convert between them explicitly instead of relying on shared underlying values.

Code that exhaustively branches over an enum or another statically closed union SHOULD pass the unreachable value to `typing.assert_never()` instead of raising `AssertionError` directly.
This makes the exhaustiveness requirement visible to static type checkers and causes newly added unhandled variants to fail type checking.
Ordinary domain or validation exceptions remain appropriate when an unsupported value can legitimately arrive through an untyped or external boundary.

## Validation and resolution

Validation functions and methods MUST only verify invariants.
They MUST return `None` on success and raise an appropriate exception on failure.

Validation functions and methods MUST NOT return information merely retrieved, resolved, transformed, or extracted as a by-product of validation.
They MAY perform such operations internally when required to verify invariants.
Callers that need the resulting information MUST obtain it separately, unless the operation explicitly acts as a validating constructor.

Predicates named `is_*`, `has_*`, or `can_*` SHOULD return `bool` and MUST NOT raise an exception for an ordinary negative result.

A validation function or method MAY return a constructed object when it intentionally serves as a constructor paired with validation.
Constructing and returning that object MUST be part of the operation's explicit contract; this exception does not permit returning dependencies resolved or information incidentally extracted during validation.

Framework validator hooks whose protocols require returning the validated value or instance, such as Pydantic validators, are exempt from the `None` return requirement.

## Function extraction

A trivial update to a list, set, mapping, or similar data structure that is used at only one call site MUST remain inline at that call site and MUST NOT be extracted into a separate function merely to isolate the mutation.
An update is trivial for this rule when its intent is clear from the data-structure operations and it does not enforce a separate invariant or contain non-obvious control flow.
A separate function MAY be introduced when it represents a meaningful domain operation, centralizes an invariant, supports reuse, or materially simplifies non-trivial control flow.

## Class instance layout

Explicit instance layouts prevent unintended instance dictionaries and dynamically named state, and they keep attribute ownership predictable across inheritance. `__slots__` is required for covered classes because it enforces this layout constraint at the Python class boundary.

New or substantially changed project-controlled classes other than test classes MUST define `__slots__` explicitly. Test classes are excluded from this convention and MAY omit `__slots__` without an explanatory comment.

A class that introduces instance attributes MUST list every attribute it introduces in `__slots__`. A class that introduces no instance attributes MUST use `__slots__ = ()`.

Every project-controlled subclass covered by this convention MUST define its own `__slots__`, including an empty declaration when it introduces no attributes. A subclass MUST NOT repeat slot names owned by a base class.

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
