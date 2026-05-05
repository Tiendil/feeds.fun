# Changelog Documentation

## Goal of the document

This document describes the expected tooling, source files, structure, and entry format for the Feeds Fun changelog.

## Scope

The scope of this specification is limited to changelog documentation artifacts.

The following topics are out of scope:

- release version selection.
- package publishing.
- Git tagging.
- release automation implementation details.
- project documentation files other than changelog artifacts.

## Dictionary

- `changelog artifact` - a file that is either a Changy source file in `changes/` or the generated root `CHANGELOG.md`.
- `version record` - the Markdown content that describes changes for one released or unreleased version.

## Tooling

Feeds Fun MUST use [Changy](https://github.com/Tiendil/changy/) to manage the changelog.

Changelog source files MUST live in `changes/`.

The root `CHANGELOG.md` MUST be generated from Changy source files.

Unreleased changes MUST be recorded in `changes/unreleased.md`.

## Version Record Structure

A single changelog version record MAY contain these parts, in this order:

1. A short introductory description of the whole version when the version contains large coordinated changes that benefit from context before individual entries.
2. A `Migration` section with instructions for users to migrate to the new version when there are breaking changes or required manual upgrade steps.
3. A `Changes` section with a bullet list of all notable changes in the version.
4. A `Deprecations` section with a bullet list of features or behaviors that are now deprecated.

The `Migration`, `Changes`, and `Deprecations` sections MUST use `h3` Markdown headings.

The `Changes` section SHOULD be present when the version contains notable user-visible, developer-visible, or project-maintenance changes.

The `Migration` section MUST be present when users need to perform manual steps before, during, or after upgrading.

The `Deprecations` section MUST be present when the version deprecates features, behaviors, APIs, commands, configuration fields, or documented workflows.

Additional `h3` sections MAY be used when a version needs a distinct category that is not covered by `Migration`, `Changes`, or `Deprecations`.

## Entry Format

Each bullet entry SHOULD be linked to a task, issue, or pull request when such a reference exists.

When an entry references an internal issue, the reference SHOULD use the `ff-<short-id>` form.

When an entry references a GitHub issue, the reference SHOULD use the `gh-<number>` form.

If both references exist for the same item, the entry SHOULD include both references, using `ff` reference as the primary reference and the `gh` reference as a secondary reference in parentheses.

When an entry references a pull request or another task tracker, the reference SHOULD use the shortest stable project convention for that tracker.

Each bullet entry SHOULD include a short description of the change, deprecation, migration instruction, or other notable item.

Additional details MAY be added as nested bullet points under the main entry when the detail helps users understand the impact or required action.

## Example

```markdown
<intro>

### Migration

- ff-aaa (gh-xxx) - <short migration instruction>
- ff-bbb (gh-yyy) - <short migration instruction>
  - <additional details if needed>
  - <additional details if needed>
- ff-ccc — <short migration instruction>
- gh-qqq — <short migration instruction>

### Changes

- ff-ddd (gh-zzz) - <short description of the change>

### Deprecations

- ff-eee (gh-www) - <short description of the deprecation>
```
