# Programming code conventions

## Goal of the document

This document describes conventions for program implementations.

## Scope

This specification applies to program source code.
The content of programming specifications is out of scope.

## Closed sets of named values

Closed sets of named values SHOULD use enums instead of raw strings to make allowed values explicit and reduce accidental use of invalid values.
Justified alternatives MAY be used when another representation provides equivalent guarantees or is necessary to satisfy an independently stated requirement.

**Example:** A task that can only be pending or complete may represent its state with an enum to catch misspelled states during type checking or validation.
