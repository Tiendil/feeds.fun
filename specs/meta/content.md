# Specification content boundaries

## Goal of the document

This document describes requirements for the level of detail in specification contracts.

## Scope

The scope of this specification is limited to the level of detail used to state requirements in specification documents.
Requirements for the subjects described by those documents are out of scope.

## Abstraction level

Specifications MUST describe their subject matter at the highest level that is still precise enough to distinguish conforming from non-conforming cases.
Specifications MUST NOT prescribe incidental details.
A detail is incidental when it does not affect whether the required properties or constraints are satisfied.

When a requirement can be expressed either as a concrete detail or as a general rule without changing which cases conform, the specification MUST prefer the general rule.

**Example:** A JSON response specification may require a field named `publication_date` because clients read that exact field.
The field name is part of the response contract.

**Counterexample:** If the specification governs only the JSON response, requiring the server to use a private class named `PublicationDateResponse` adds a detail unrelated to that response contract.

**Example:** A document-format specification may require a section headed `Scope` so readers can find the document's applicability boundary under the agreed heading.

**Counterexample:** If the document format constrains only the delivered Markdown, requiring the author's draft file to be named `specification-draft.docx` prescribes a working detail that does not affect the delivered document.

## Implementation neutrality

A specification MUST NOT require a particular method when multiple methods can satisfy the same required properties and constraints, unless the choice of method is itself part of the specification's subject matter or is necessary to satisfy an independently stated requirement.
When a specification requires a particular method, it MUST state why the method matters or which required property an alternative would violate.

**Example:** A search specification may require results in descending publication-date order while leaving the sorting algorithm unspecified.

**Counterexample:** If result ordering is the only relevant requirement, mandating quicksort excludes other sorting methods without identifying a required property that depends on quicksort.

**Example:** A publication procedure may require a reviewer other than the author to approve a report before release.
Here the independent review decision is the release gate being defined, so the prescribed review step is part of the procedure's subject matter.

**Counterexample:** A report specification that requires a findings section in a PDF deliverable does not justify mandating Microsoft Word merely because the current author uses it.

A specification MAY recommend a durable project-wide practice when it promotes a stated project-wide quality, even when alternative methods can satisfy the same requirements.
A recommended practice MUST use `SHOULD` or `SHOULD NOT`, MUST state its intended benefit, and MUST permit justified exceptions.
Specifications MUST NOT present a local, temporary, or purely stylistic preference as a project-wide practice.

**Example:** A publication workflow may state that reviewers `SHOULD` use a checklist to reduce missed corrections, while permitting an equivalent review process that checks the same criteria.

**Counterexample:** Requiring the current editor's checklist template solely because that editor prefers its layout excludes other processes that satisfy the same review criteria.

Specifications MUST NOT resolve a choice of method merely to make a requirement or example more concrete.
When a choice of method does not affect the required properties or constraints and is not a qualified recommended practice, the specification MUST omit that choice.
