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

- `specification` — a Markdown document in `./specs/` that describes project requirements and related terminology or documentation rules.
- `top-level section` — a section introduced by an `h2` Markdown header.
- `nested section` — a section introduced by an `h3` or deeper Markdown header.
- `non-normative callout` — a short supplementary explanation that clarifies normative content without changing the specification's contract.
- `bold inline label` — a bold Markdown prefix at the start of a prose paragraph that identifies the kind of non-normative callout that follows.

## Sections

A specification MUST contain a single `h1` header with the name of the specification, which SHOULD be unique across all specifications.

Top-level information SHOULD be organized in sections with `h2` headers.

Nested sections MAY use `h3`, `h4`, and deeper headers to represent a meaningful hierarchy within a top-level concern.

Nested sections SHOULD be used for details that belong to a parent top-level section, such as:

- examples.
- option descriptions.
- record fields.
- subsections of a larger topic.

Each section heading MUST identify the section's stable conceptual concern rather than summarize or enumerate its current contents.
An existing section heading MUST be preserved while it remains accurate for that concern.
It MUST NOT be renamed merely to mention a subordinate detail added to the section.
A heading MAY be renamed only when the section's conceptual boundary changes or the existing heading becomes incorrect or ambiguous.

Sections that are mandatory for all specifications:

- `Goal of the document`
- `Scope`

Optional sections:

- `Dictionary`

The first sections of a specification SHOULD be placed in this order:

1. `Goal of the document`
2. `Scope`
3. `Dictionary`, when the section exists

The `Goal of the document` section MUST describe the document's subject matter and purpose in terms of the content it contains.
Statements in the section MUST be verifiable from the document's content alone.
They MUST NOT depend on readers following the specification or on governed artifacts achieving a desired quality.

The `Goal of the document` section MUST NOT define requirements for the document itself, such as saying that the document:

- MUST define something.
- MUST list something.
- MUST describe something.

`This document describes the abstraction level and content conventions for backend module specifications` is an appropriate goal because it identifies the document's content.
`This document describes conventions that keep backend module specifications focused` is inappropriate because it claims an intended effect on governed specifications.

The `Scope` section MUST identify the class of artifacts, behavior, or concerns to which the specification applies.
It MUST describe that boundary at a stable conceptual level.
It SHOULD be descriptive rather than normative when it explains what the document covers.
It MUST NOT serve as a table of contents or enumerate any of the following merely to summarize the document:

- current features.
- operations.
- entities.
- workflows.
- requirements.
- sections.

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
- When a prose statement names four or more distinct items, those items SHOULD be formatted as a Markdown list rather than inline prose.

Each sentence in a prose paragraph MUST be written on a separate Markdown source line.
Consecutive sentence lines MUST NOT be separated by a blank line when they belong to the same paragraph.

Changes to an existing specification SHOULD preserve its wording and structure wherever they remain accurate.
An edit SHOULD change only the smallest portion necessary to express the intended requirement.
A broader rewrite MAY be used when a targeted edit would leave the specification ambiguous, contradictory, or materially harder to understand.

### Non-normative callouts

Specifications MAY include short non-normative callouts when supplementary context materially clarifies an existing requirement.
Each callout MUST remain within the section whose content it clarifies and SHOULD appear immediately after that content.
A specification SHOULD NOT create a dedicated callout subsection unless several callouts jointly clarify one substantial concern and grouping materially improves readability.
The normative requirement or constraint MUST be stated independently, and removing the callout MUST NOT change the specification's contract.

Specifications SHOULD include a non-normative example or counterexample when a requirement is materially easier to understand through a concrete case.
Authors SHOULD specifically consider a callout when a requirement involves:

- interaction between multiple rules or states.
- temporal, precedence, or concurrency relationships.
- aggregation or calculation.
- a distinction between similar cases.
- behavior that is correct but likely to be surprising.
- an abstraction boundary that could otherwise be mistaken for an implementation requirement.

A callout SHOULD demonstrate the observable consequence of the surrounding requirement.
It SHOULD NOT merely replace abstract names with invented names while repeating the same statement.
A specification MAY omit a callout when the requirement is already concrete and adding one would not resolve a plausible ambiguity.

Examples and counterexamples MAY use invented names, quantities, and times, but those illustrative values MUST NOT define:

- required representations.
- required bounds.
- exhaustive sets.
- additional cases.

Every callout MUST comply with the requirements governing its surrounding specification and MUST NOT introduce otherwise excluded content.
A callout SHOULD be omitted when it merely restates already clear content.

### Bold inline labels

A non-normative callout SHOULD use the narrowest applicable bold inline label so readers can distinguish the callout's role from normative requirements.
A callout MAY remain unlabeled when its non-normative role is already unambiguous from the surrounding structure.
A bold inline label MUST use exactly one of these forms:

- `**Example:**` — a conforming concrete illustration.
- `**Counterexample:**` — a concrete illustration of non-conforming behavior.
- `**Rationale:**` — an explanation of why a requirement exists.
- `**Note:**` — an ancillary clarification that does not fit a narrower label.
- `**Context:**` — background that helps readers understand the surrounding content.
- `**Terminology:**` — an explanation of a term already established by the specification's contract.
- `**Compatibility:**` — an explanation of the implications of an independently stated compatibility requirement.
- `**Warning:**` — an explanation of a risk or consequence associated with violating or misapplying an independently stated requirement.

`**Note:**` and `**Context:**` SHOULD NOT be used when a narrower label applies.
`**Terminology:**` MUST NOT define or alter a term.
`**Compatibility:**` and `**Warning:**` MUST NOT establish the requirements whose implications or consequences they explain.

The label MUST begin the callout's first sentence, MUST include its colon inside the bold markup, and MUST be followed by one space and the callout text on the same source line.
The label MUST NOT appear by itself, inside a heading, or in the middle of a sentence.

A labeled callout MUST be one prose paragraph.
The label applies to every consecutive sentence line in that paragraph and MUST NOT be repeated on later lines of the same paragraph.
Material that requires multiple paragraphs SHOULD be integrated into the surrounding section or, when it forms one substantial concern, placed in a dedicated nested section.

Bold inline labels MUST NOT identify:

- normative requirements.
- defaults.
- invariants.
- exceptions.
- section structure.
- general emphasis.

The presence or absence of a label MUST NOT change whether any text is normative.
Specifications MUST NOT introduce additional bold inline labels without first extending this convention.

## Abstraction level

Specifications MUST describe the following at the highest level that is still precise enough to distinguish conforming from non-conforming implementations:

- project behavior.
- architecture.
- constraints.
- terminology.
- compatibility contracts.

Specifications SHOULD define:

- externally visible behavior and data contracts.
- stable architectural boundaries and ownership responsibilities.
- constraints that must hold across implementations.
- technology choices when they are part of the intended architecture.

Specifications MUST NOT define incidental implementation details.

Incidental implementation details include:

- private helper function names.
- exact class names that are not part of a stable project convention or public boundary.
- exact file paths for code that is not owned by a module-layout or ownership requirement.
- local constructor signatures.
- temporary implementation strategies.
- repeated examples that restate ownership already defined elsewhere without adding a new constraint.

Specifications MAY name the following concrete details when the name itself is a stable contract:

- files.
- modules.
- symbols.
- commands.
- formats.

Stable contracts include:

- public CLI contracts covering:
  - commands.
  - options.
  - arguments.
  - output records.
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

An extensible concept's definition MUST state its semantic meaning, distinguishing invariants, or membership criteria rather than rely only on an enumeration of current instances.
An enumeration MAY supplement an extensible definition, but it MUST NOT substitute for it.

Specifications MUST use an exhaustive enumeration only when the set is intentionally closed and its completeness is part of a stable contract.
Examples of members in an extensible set MUST be identified as non-exhaustive.

Adding, changing, or removing an instance of an extensible concept SHOULD NOT require changing the concept's definition unless its invariants or membership criteria change.

## Implementation neutrality

Specifications MUST distinguish required behavior and architectural constraints from recommended implementation practices.

A specification MUST NOT require an implementation mechanism when multiple implementations can satisfy the same required behavior and stable observable contracts, unless that mechanism is itself an intentional architectural requirement or an observable caller contract.
When a specification requires a concrete implementation mechanism, it MUST state why the mechanism matters or which required property an alternative implementation would violate.

A specification MAY recommend a durable project-wide implementation practice when it promotes a stated project-wide quality, even when alternative implementations can satisfy the same observable contract.
A recommended implementation practice MUST use `SHOULD` or `SHOULD NOT`, MUST state its intended benefit, and MUST permit justified exceptions.
Specifications MUST NOT present a local, temporary, or purely stylistic implementation preference as a project-wide practice.

Specifications MUST NOT resolve an implementation choice merely to make a requirement or example more concrete.
When an implementation choice does not affect the required behavior or stable contract and is not a qualified recommended practice, the specification MUST omit that choice.
