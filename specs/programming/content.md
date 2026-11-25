# Programming specification content

## Goal of the document

This document describes content requirements for programming specifications.

## Scope

This specification applies to the content of specifications for program behavior and architecture.
General document structure and style are out of scope.

## Behavior and architecture

Specifications SHOULD define:

- externally visible behavior and data contracts.
- stable architectural boundaries and ownership responsibilities.
- constraints that must hold across implementations.
- technology choices when they are part of the intended architecture.

These concerns provide the basis for assessing whether an implementation conforms to the intended behavior and architecture.
A specification MAY omit a concern that does not apply to its subject matter.

## Implementation details

Specifications SHOULD NOT require specific names or locations for implementation elements unless those names or locations are themselves part of a stable contract.

**Example:** A specification for a task that can only be pending or complete may define those allowed states without prescribing an enum class name or file location.

**Counterexample:** Requiring the enum to be called `TaskState` and defined in `models/task_state.py` solely because the current implementation uses those names adds details unrelated to the state contract.
