# Specification structure and style

## Goal of the document

This document describes the structure and style conventions for specifications in this project.

## Scope

The scope of this specification is limited to conventions for writing and editing specification documents in this project.
Decisions about which subject-matter details a specification makes normative are out of scope.

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

The `Goal of the document` and `Scope` sections MUST NOT serve as tables of contents or enumerate any of the following merely to summarize the document:

- current features.
- operations.
- entities.
- workflows.
- requirements.
- sections.

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
- Specifications SHOULD use Markdown lists for simple enumerations, including terms with definitions and named items with descriptions or a few associated properties.
- Tables SHOULD be used only when alignment across rows and columns materially helps readers compare items or understand relationships.
- Having multiple properties per item MUST NOT by itself justify a table; those properties MAY be expressed within list items or nested lists.
- Formatting choices SHOULD favor readability of Markdown source and clarity of diffs over compactness of the rendered document.

**Example:** Terms with definitions, or configuration fields with defaults and descriptions, ordinarily belong in lists.
A comparison of supported capabilities across output formats may justify a table.

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

Examples SHOULD NOT serve as inventories of current artifacts, instances, or working arrangements.

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

## Terminology stability

Names in specifications MUST describe durable domain concepts rather than current implementation, storage, or workflow structure.
New names SHOULD remain accurate across reasonable architectural changes.

An existing term MUST be preserved when a change extends the concept's behavior or representation and the term remains accurate.
A term MAY be renamed only when it has become incorrect, ambiguous, or inconsistent with established project terminology.
A rename MUST NOT be made only to mirror an internal architecture, persistence, or lifecycle change.

When only one variant needs distinction, specifications SHOULD qualify that variant locally instead of renaming the broader concept throughout the specification.

## Conceptual descriptions

Specifications SHOULD describe concerns through their meaning, purpose, or defining criteria rather than through inventories of current contents or instances.
Conceptual wording SHOULD be chosen to remain accurate across reasonable changes in scope, detail, or representation when the underlying concern remains the same.

An extensible concept's definition MUST state its semantic meaning, distinguishing invariants, or membership criteria rather than rely only on an enumeration of current instances.
An enumeration MAY supplement an extensible definition, but it MUST NOT substitute for it.

Specifications MUST use an exhaustive enumeration only when the set is intentionally closed and its completeness is part of a stable contract.
An exhaustive enumeration MAY define such a set.
Examples of members in an extensible set MUST be identified as non-exhaustive.

Adding, changing, or removing an instance of an extensible concept SHOULD NOT require changing the concept's definition unless its invariants or membership criteria change.

