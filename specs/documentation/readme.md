# README Documentation

## Goal of the document

This document describes the expected content, structure, and tone of the Feeds Fun `README.md`.

## Scope

The scope of this specification is limited to the repository root `README.md`.

The following topics are out of scope:

- package metadata.
- generated command help.
- detailed backend API behavior.
- detailed frontend component behavior.
- detailed deployment examples.
- development environment rules for agents.
- documentation files other than the root `README.md`.

## Audience

`README.md` MUST be written primarily for humans who are discovering Feeds Fun or deciding whether to self-host it.

`README.md` SHOULD help readers quickly understand:

- what Feeds Fun is.
- what user problem Feeds Fun solves.
- what major features Feeds Fun provides.
- how to try Feeds Fun locally.
- how to find self-hosting instructions.
- how backend and frontend packages are distributed.
- how to work on the project.

`README.md` MAY mention coding-agent development tooling, but it MUST NOT duplicate the full agent workflow documentation from `AGENTS.md` or Donna artifacts.

## Structure

`README.md` MUST start with a single h1 heading containing the project name.

The first paragraphs after the h1 heading SHOULD explain the core value proposition in plain language.

`README.md` MUST include these sections:

- `Screenshots` - product visuals.
- `Features` - main product capabilities.
- `Motivation` - the user problem and project reason.
- `Official site` - hosted Feeds Fun service.
- `Fastest way to try locally` - shortest local trial path.
- `Self-hosted version` - deployment and package distribution entry point.
  - `Configuration` - backend and frontend configuration overview.
    - `Configure tag processors`.
    - `Use third-party LLM models`.
    - `Configure tag normalizers`.
    - `Configure integrations with new sources`.
  - `Backend` - backend package usage and minimal backend run commands.
  - `Frontend` - frontend package usage and minimal frontend build commands.
- `Architecture` - high-level runtime architecture.
  - `Loader worker`.
  - `Librarian worker`.
- `Development` - local development workflow.
  - `Preparations`.
  - `Run`.
  - `Utils`.
  - `DB migrations`.
  - `Upgrade to new versions`.
  - `Profiling`.

The self-hosted installation section SHOULD link to maintained deployment examples instead of duplicating every Docker Compose detail.

The configuration section MAY include concrete environment variable examples when they help users understand naming patterns.

The backend and frontend package sections SHOULD explain that compatible backend and frontend versions must be used together.

The architecture section SHOULD stay high level and focus on the API server and worker responsibilities.

The development section SHOULD describe the required Docker-backed development workflow and repository helper scripts at a practical level.

Additional sections MAY be added when they help readers evaluate, run, operate, or contribute to Feeds Fun.

`README.md` SHOULD avoid deep implementation details.

## Content Requirements

`README.md` MUST identify Feeds Fun as a self-hosted news reader with AI-assisted or LLM-assisted tagging.

`README.md` MUST explain that Feeds Fun assigns tags to news entries.

`README.md` MUST explain that users can create rules to score news by tags.

`README.md` MUST explain that users can filter and sort news by score, tags, date, or similar reading signals.

`README.md` MUST link to the official hosted site when it exists.

`README.md` SHOULD link to the project blog and roadmap when those resources are maintained.

`README.md` MUST include at least one product screenshot or product visual when image assets are available.

`README.md` MUST mention the main product features:

- feed management.
- automatic tag assignment.
- tag-based scoring rules.
- filtering.
- sorting.
- read-state tracking.
- improved support for major feed sources.

`README.md` MUST describe where to find the fastest local trial instructions.

`README.md` MUST link to self-hosting examples for single-user and multi-user modes when those examples are present in the repository.

`README.md` MUST mention support for third-party LLM models when the repository has maintained instructions for them.

`README.md` MUST describe how backend configuration can be overridden.

`README.md` MUST show the backend environment variable naming convention.

`README.md` MUST describe tag processor configuration.

`README.md` MUST describe LLM processor configuration.

`README.md` MUST describe tag normalizer configuration.

`README.md` MUST describe integration plugin configuration.

`README.md` MUST mention that the backend is distributed as the `ffun` package when that package is published.

`README.md` MUST mention that the frontend is distributed as the `feeds-fun` package when that package is published.

`README.md` MUST include minimal backend run commands for installation, migrations, API server startup, and workers.

`README.md` MUST include minimal frontend build commands or point readers to a maintained frontend build path.

`README.md` MUST describe the local development domains required by the Docker development setup.

`README.md` MUST describe the basic development startup flow:

1. clone the repository.
2. build development containers.
3. start Docker Compose services.
4. start backend workers.

`README.md` MUST explain how to run backend utility commands through `./bin/backend-utils.sh`.

`README.md` MUST explain how to apply and create database migrations.

`README.md` MUST explain that upgrades should keep backend and frontend versions in sync.

`README.md` MUST point readers to `CHANGELOG.md` for upgrade notes, migrations, and breaking changes.

## Style

`README.md` SHOULD be practical and direct.

`README.md` SHOULD prefer short explanations, bullet lists, and command examples.

`README.md` SHOULD use a confident but accurate tone.

`README.md` SHOULD avoid promising behavior that is only planned or not implemented.

`README.md` SHOULD not be an exhaustive user manual; detailed deployment and configuration guidance belongs in maintained examples and source-specific documentation.
