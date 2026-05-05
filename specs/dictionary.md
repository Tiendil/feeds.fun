# Feeds Fun dictionary

## Goal of the document

This document defines Feeds Fun terminology that is shared by multiple specifications and dependency metadata rules.

## Scope

The scope of this specification is limited to project-specific terminology.

Detailed behavior, implementation requirements, and configuration schemas are out of scope.

## Terms

- `feed` - an RSS, Atom, or similar source of news entries.
- `entry` - one news article or item loaded from a feed.
- `tag` - semantic label assigned to an entry.
- `rule` - user-defined score expression based on tags.
- `collection` - curated feed collection configuration.
- `integration` - external source-specific behavior, such as YouTube or Reddit support.
- `backend` - Python application in `ffun/ffun`.
- `frontend` - Vue application in `site/src`.
- `development helper` - Docker-backed command in `bin`.
- `Donna workflow` - workflow artifact under `.donna/project/work` or `.donna/session`.
- `specification` - Markdown document under `spec` that describes expected project behavior, structure, terminology, or documentation rules.
- `changelog fragment` - Markdown file under `changes` consumed by Changy.
- `module boundary` - tach rule that describes allowed imports between Python package modules.
