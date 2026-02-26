# Instructions for the AI Agents

This document provides instructions and guidelines for the AI agents working on this project.

Every agent MUST follow the rules and guidelines outlined in this document when performing their work.

## Initialization

You MUST run the next commands on the start of your work session:

- `donna -p llm -r <project-root> artifacts view '*:intro'` — to get an introduction to the project and its context.

## Environment

All development-related operations MUST be performed in Docker containers, see `./docker-compose.yml` for details.

You MUST not perform any development-related operations directly on the host machine.

Most important commands have script shortcuts in `./bin` directory.

Command you are allowed to use:

- `./bin/backend-tests.sh` — run ALL backend tests via pytest.
- `./bin/backend-utils.sh` — run utils in the backend environment, for example `/bin/backend-utils.sh poetry run pytest ffun/parsers/tests/test_feed.py`
- `./bin/build-dev-containers.sh` — build base Docker images for development. Call this command after making changes to Docker configs or dependencies.
- `./bin/check-code-spelling.sh` — check code spelling with `codespell` tool. Both for frontend and backend code.
- `./bin/dev-check-formatting.sh` — check code formatting. Both for frontend and backend code.
- `./bin/dev-check-runtime.sh` — check if code starts without errors — very basic smoke tests.
- `./bin/dev-check-semantics.sh` — check code semantics (types, linting, etc.). Both for frontend and backend code.
- `./bin/frontend-tests.sh` — run ALL frontend tests.
- `./bin/frontend-utils.sh` — run utils in the frontend environment.

If you need to do complex "test & lint & fix" activities, you MUST use the `donna-do` skill to run the code polish workflow.

## Resticted changes / operations

You ABSOLUTELY MUST NOT perform the following operations without explicit instructions to do so:

- Changing `docker-compose.yml` or any Docker-related configuration.
- Changing Docker runtime parameters (like allocated resources, volumes, etc.).
- Changing running Docker services related to other projects or unrelated to development environment.
- Installing any new dependencies, both for frontend and backend.
- Updating lock files.
- Installing any new tools, utilities, or software on the host machine or in the development containers.
- Changing project structure, such as moving files around, creating new directories, etc.

If you want to change something in the above list, you MUST ask for explicit instructions and permission to do so.

## Top priority tools

These tools MUST have the highest priority when an agent is deciding which tool to use for a given task:

### `ast-grep`

`ast-grep` — a tool for searching and manipulating Abstract Syntax Trees in code. Use it when you work with particular code patterns, structures, or constructs in the codebase.

You MUST use it to:

- Search for specific code patterns or structures in the codebase.
- Extract information from code, such as function definitions, variable declarations, or specific code constructs.
- Analyze code for specific patterns or anti-patterns, such as code smells, security vulnerabilities, performance issues, specific usage of libraries or APIs, etc.
- Refactor particular code patterns or structures across the codebase.
- Introduce new small behaviors or features into existing code.

You MUST NOT use it for:

- Implementing huge features or behaviors that require adding massive blocks of code (like adding a new class, module, writing a huge function, etc.).
