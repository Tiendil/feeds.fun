# Programming code conventions

## Goal of the document

This document describes conventions for program implementations.

## Scope

This specification applies to program source code in all programming languages.
It also covers retroactive application of programming specifications to existing implementations and artifacts.
The content of programming specifications is out of scope.

## Applying specifications to code

Programming specifications MUST be applied to newly written code.
Existing implementations and artifacts MUST NOT be changed retroactively to conform to a programming specification unless the developer explicitly requests the change.
This restriction applies regardless of how the change is made, including when it is carried out by newly written code.

## Prefer enums over primitive values

Project-owned closed sets of named values SHOULD use enums instead of primitive values or constants.
Primitive values or constants MAY be used when exact literal values are required by a third-party interface or when the values do not represent independently named project concepts.

**Rationale:** Enums make allowed values discoverable and help tools detect invalid member references.
They also simplify refactoring.

### Enum values

Enums MAY omit underlying values only when the language supports enums without them and architectural contracts explicitly require that approach.

Unless an established contract explicitly requires value generation, project-owned enum members with underlying values MUST define those values explicitly and MUST NOT use value generators, such as `enum.auto()` in Python.

**Rationale:** Explicit values keep member identities independent from declaration order or generated naming rules.
They also allow names to change without changing stored or externally exchanged values.

Assigned persisted values MUST NOT be changed or reused for a different enum member.

Enum values used in external compatibility contracts MUST NOT be changed or reused without an explicit compatibility transition.

Deprecated enum members SHOULD be marked using the language's native deprecation mechanism or a `DEPRECATED` comment in the language's comment syntax, including the reason for deprecation.

When choosing types for enum values, consider the layer that owns the enum:

- API-boundary enums SHOULD use values required by the API contract.
- Storage-bound enums SHOULD use values that provide performance and storage efficiency.
- Domain-bound enums SHOULD use values that make runtime semantics clearer, simplify conversion to other representations, and avoid degrading performance.

All other things being equal:

- API-boundary enums SHOULD use human-readable representations, for example, strings.
- Storage-bound enums SHOULD use compact representations, for example, integers.

When converting between enum representations, such as between domain logic and an API boundary, code SHOULD use explicit conversion instead of relying on shared underlying values.

### Enum processing

Code that branches over an enum SHOULD prefer `match` or `switch` statements over `if`/`elif`/`else` chains when the language supports them, to make case handling easier to read and review.

Code that dispatches on an enum MUST handle every member permitted at that point by the operation's contract.
Code SHOULD use static exhaustiveness checking to verify that coverage when supported by the language or type checker.

## Runtime type validation

Functions called through project-controlled typed interfaces SHOULD treat declared parameter types as caller contracts.
They SHOULD NOT perform runtime checks solely to verify that arguments match their declared types.

Runtime validation remains appropriate at untyped or external boundaries, including HTTP input, CLI input, configuration, deserialized database rows, third-party responses, and plugin data.

Code MUST still validate semantic constraints that are not guaranteed by the contracts of the declared types, such as non-empty identifiers, timezone awareness, numeric ranges, configured values, and valid cross-field combinations.

Code that constructs a semantically specific typed value from raw or untyped data MUST validate the semantic invariants of that type at the construction boundary.
Functions and methods that receive the constructed typed value MUST assume those invariants hold and MUST NOT repeat their validation.

## Validation and resolution

Validation functions and methods MUST only verify invariants.
They MUST return no data on success, apart from any validation status required by their contract, and MUST signal failure through the error mechanism defined by their contract.

Validation functions and methods MUST NOT return information merely retrieved, resolved, transformed, or extracted as a by-product of validation.
They MAY perform such operations internally when required to verify invariants.
Callers that need the resulting information MUST obtain it separately, unless the operation explicitly acts as a validating constructor.

Functions and methods that return whether a condition holds SHOULD use predicate-based names, such as names with `is`, `has`, or `can` prefixes in the implementation language's naming style, to make their boolean result clear to callers.
Functions and methods whose names express predicates SHOULD return boolean results and MUST NOT signal an error for an ordinary negative result.

A validation function or method MAY return a constructed value when it intentionally serves as a constructor paired with validation.
Constructing and returning that value MUST be part of the operation's explicit contract; this exception does not permit returning dependencies resolved or information incidentally extracted during validation.

Framework validation hooks whose protocols require returning the validated value or instance are exempt from the success-result restriction.

## Function boundaries

A separate function or method MAY be introduced, including at a single call site, when it provides a meaningful boundary, for example by:

- representing a meaningful domain operation.
- centralizing an invariant.
- sharing logic between call sites.
- materially simplifying non-trivial control flow.

Trivial code used at only one call site MUST remain inline when extraction would merely isolate an implementation step without providing a meaningful boundary.
Code is trivial when its intent is clear from its operations and it neither enforces a separate invariant nor contains non-obvious control flow.

## Temporary implementation code

Production code intentionally introduced as a temporary bridge MUST include an adjacent `TODO` comment.
Keeping the explanation next to the bridge makes the exception discoverable during maintenance and review and couples its removal to the code it qualifies; a separate tracked work item alone does not preserve that local context.
The comment MUST explain why the temporary code is currently necessary and identify the concrete condition, milestone, or tracked work item after which it MUST be removed.
Vague comments such as "remove later" are insufficient.
The comment MUST be removed together with the temporary code.
