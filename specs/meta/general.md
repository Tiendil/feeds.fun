# General specification requirements

## Goal of the document

This document describes the general requirements for specifications in this project.

## Scope

The scope of this specification is limited to requirements for specification documents in this project.

The following topics are out of scope except when they affect how specification documents should be written:

- project behavior.
- implementation requirements.
- product requirements.

## Dictionary

- `specification` — a Markdown document in `./specs/` that describes requirements, behavior, terminology, or documentation rules for the project.
- `top-level section` — a section introduced by an `h2` Markdown header.
- `nested section` — a section introduced by an `h3` or deeper Markdown header.

## Sections

A specification MUST contain a single `h1` header with the name of the specification, which SHOULD be unique across all specifications.

Top-level information SHOULD be organized in sections with `h2` headers.

Nested sections MAY use `h3`, `h4`, and deeper headers when they make the document easier to navigate.

Nested sections SHOULD be used for details that belong to a parent top-level section, such as:

- examples.
- option descriptions.
- record fields.
- subsections of a larger topic.

Sections that are mandatory for all specifications:

- `Goal of the document` — a brief description of what the specification is about and what it aims to achieve.
- `Scope` — a brief description of what the specification covers and what it intentionally does not cover.

Optional sections:

- `Dictionary` — a list of terms that are specific to the specification.

The first sections of a specification SHOULD be placed in this order:

1. `Goal of the document`
2. `Scope`
3. `Dictionary`, when the section exists

The `Goal of the document` section MUST describe the content and purpose of the document.

The `Goal of the document` section MUST NOT define requirements for the document itself, such as saying that the document:

- MUST define something.
- MUST list something.
- MUST describe something.

The `Scope` section MUST identify the class of artifacts, behavior, or concerns to which the specification applies.
It MUST describe that boundary at a stable conceptual level.
It SHOULD be descriptive rather than normative when it explains what the document covers.
It MUST NOT serve as a table of contents or enumerate current features, operations, entities, workflows, requirements, or sections merely to summarize the document.
It SHOULD remain accurate when requirements are added, changed, or removed without changing the specification's conceptual boundary.
An in-scope enumeration MAY be used only when the enumerated set is intentionally closed and membership in that set defines the specification boundary.
The section SHOULD explicitly mention important adjacent concerns that readers or future authors could reasonably mistake as covered.
It SHOULD NOT attempt to enumerate every unrelated or excluded concern.
It MUST NOT explain where to find requirements that belong to other specifications.

The `Dictionary` section SHOULD be placed immediately after the `Scope` section.
It SHOULD contain only terms that are specific to the specification.
Terms that are used by multiple specifications SHOULD be defined in `./specs/dictionary.md`.

## Style

- Specifications MUST use Markdown syntax for formatting the document.
- Specifications MUST follow [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).
- Specifications MUST NOT break long lines to fit within 80 characters or any other number; they MUST use as many characters as needed to express the idea clearly.
- Long enumerations SHOULD be organized as Markdown lists when possible.

Each sentence in a prose paragraph MUST be written on a separate Markdown source line.
Consecutive sentence lines MUST NOT be separated by a blank line when they belong to the same paragraph.

Changes to an existing specification SHOULD preserve its wording and structure wherever they remain accurate.
An edit SHOULD change only the smallest portion necessary to express the intended requirement.
A broader rewrite MAY be used when a targeted edit would leave the specification ambiguous, contradictory, or materially harder to understand.

## Abstraction level

Specifications MUST describe project behavior, architecture, constraints, terminology, and compatibility contracts at the highest level that is still precise enough to guide implementation.

Specifications SHOULD define:

- externally visible behavior and data contracts.
- stable architectural boundaries and ownership responsibilities.
- constraints that must hold across implementations.
- technology choices when they are part of the intended architecture.
- examples that clarify the requirement being specified.

Specifications MUST NOT define incidental implementation details.

Incidental implementation details include:

- private helper function names.
- exact class names that are not part of a stable project convention or public boundary.
- exact file paths for code that is not owned by a module-layout or ownership requirement.
- local constructor signatures.
- temporary implementation strategies.
- repeated examples that restate ownership already defined elsewhere without adding a new constraint.

Specifications MAY name concrete files, modules, symbols, commands, or formats when the name itself is a stable contract.

Stable contracts include:

- public CLI commands, options, arguments, and output records.
- configuration file names, fields, and values.
- module ownership boundaries defined by architecture specifications.
- naming conventions that all implementations are expected to follow.
- concrete dependencies or language features that are intentional architectural choices.

When a requirement can be expressed either as an implementation detail or as a general architectural rule, the specification MUST prefer the general rule.

For example, a specification SHOULD require closed sets of named values to use enums instead of raw strings.
It SHOULD NOT require a specific enum class name or file location unless that class name or location is itself a stable architectural boundary.

Examples in specifications SHOULD illustrate behavior or ownership.
Examples SHOULD NOT be treated as a place to enumerate every current implementation file or symbol.

### Terminology stability

Names in specifications MUST describe durable domain concepts rather than current implementation, storage, or workflow structure.
New names SHOULD remain accurate across reasonable architectural changes.

An existing term MUST be preserved when a change extends the concept's behavior or representation and the term remains accurate.
A term MAY be renamed only when it has become incorrect, ambiguous, or inconsistent with established project terminology.
A rename MUST NOT be made only to mirror an internal architecture, persistence, or lifecycle change.

When only one variant needs distinction, specifications SHOULD qualify that variant locally instead of renaming the broader concept throughout the specification.

### Extensible definitions

Specifications SHOULD define extensible concepts through their invariants, responsibilities, and membership criteria rather than by enumerating their current instances.

Specifications MUST use an exhaustive enumeration only when the set is intentionally closed and its completeness is part of a stable contract.
Examples of members in an extensible set MUST be identified as non-exhaustive.

Adding, changing, or removing an instance of an extensible concept SHOULD NOT require changing the concept's definition unless its invariants or membership criteria change.

## Implementation neutrality

Specifications MUST distinguish required behavior and architectural constraints from recommended implementation practices.

A specification MUST NOT require an implementation mechanism when multiple implementations can satisfy the same required behavior and stable observable contracts, unless that mechanism is itself an intentional architectural requirement or an observable caller contract.
When a specification requires a concrete mechanism, such as a class, function, decorator, inheritance hierarchy, or specific helper, it MUST state why the mechanism matters or which required property an alternative implementation would violate.

A specification MAY recommend a durable project-wide implementation practice when it promotes a stated quality such as maintainability, diagnosability, security, testability, or consistency, even when alternative implementations can satisfy the same observable contract.
A recommended implementation practice MUST use `SHOULD` or `SHOULD NOT`, MUST state its intended benefit, and MUST permit justified exceptions.
Specifications MUST NOT present a local, temporary, or purely stylistic implementation preference as a project-wide practice.

Specifications MUST NOT resolve an implementation choice merely to make a requirement or example more concrete.
When an implementation choice does not affect the required behavior or stable contract and is not a qualified recommended practice, the specification MUST omit that choice.
