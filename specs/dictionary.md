# Feeds Fun dictionary

## Goal of the document

This document defines Feeds Fun terminology that is shared by multiple specifications and dependency metadata rules.

## Scope

The scope of this specification is limited to project-specific terminology.

Detailed behavior, implementation requirements, and configuration schemas are out of scope.

## Terms

Terms defined in this section are stable project vocabulary. Project artifacts MUST use these terms when referring to the corresponding concepts and MUST preserve them across behavioral, architectural, implementation, and storage changes while their definitions remain accurate. A dictionary term MAY be renamed only when its existing name or definition has become incorrect or ambiguous.

- `feed` - an RSS, Atom, or similar source of news entries.
- `entry` - one news article or item loaded from a feed.
- `tag` - semantic label assigned to an entry.
- `rule` - user-defined score expression based on tags.
- `collection` - curated feed collection configuration.
- `integration` - external source-specific behavior, such as YouTube or Reddit support.
- `audit record` - append-only durable record of a business change or event, including its actor and subject entities.
- `backend` - Python application in `ffun/ffun`.
- `frontend` - Vue application in `site/src`.
- `architecture test` - a test that verifies cross-cutting structural rules or conventions defined by an architecture specification.
- `development helper` - Docker-backed command in `bin`.
- `Donna workflow` - workflow artifact under `.donna/project/work` or `.donna/session`.
- `specification` - Markdown document under `spec` that describes expected project behavior, structure, terminology, or documentation rules.
- `changelog fragment` - Markdown file under `changes` consumed by Changy.
- `module boundary` - tach rule that describes allowed imports between Python package modules.
