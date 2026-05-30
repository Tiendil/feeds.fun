# Instructions for the AI Agents

This document provides instructions and guidelines for the AI agents working on this project.

Every agent MUST follow the rules and guidelines outlined in this document when performing their work.

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
- `./bin/taskwarior.sh` — run Taskwarrior commands related to project journaling.

If you need to search or manipulate code, do that on the host machine, no need to use scripts from `./bin` or docker containers for that.

## Resticted changes / operations

You ABSOLUTELY MUST NOT perform the following operations without explicit instructions to do so:

- Changing `docker-compose.yml` or any Docker-related configuration.
- Changing Docker runtime parameters (like allocated resources, volumes, etc.).
- Changing running Docker services related to other projects or unrelated to development environment.
- Installing any new dependencies, both for frontend and backend.
- Updating lock files.
- Installing any new tools, utilities, or software on the host machine or in the development containers.
- Changing project structure, such as moving files around, creating new directories, etc.
- Staging or unstaging files in git, including commands such as `git add`, `git restore --staged`, and `git reset`.

If you want to change something in the above list, you MUST ask for explicit instructions and permission to do so.

## Top priority tools

These tools MUST have the highest priority when an agent is deciding which tool to use for a given task:

### `donna`

Use Donna to run project-local deterministic workflows when the developer, these instructions, or an active Donna workflow explicitly asks for one.

Donna controls workflow state only. Agents remain responsible for reading project instructions, using `depmesh` where applicable, editing files, running checks, and reporting results.

You may need to read the usage intructions for `donna -p llm skill usage` in these cases:

- You need to run a workflow first time in the session.
- You need to list available workflows first time in the session.

Use Donna's `llm` protocol for agent-facing commands unless a human explicitly asks for another protocol:

Depmesh is configured to log significant operation steps via `task` tool.

Special workflows to use:

- `@/workflows/polish.donna.md` — format, fix architecture, lint, and test errors. Run it after making changes to the codebase at the moments when the project is expected to be in a working state: between significant implementation steps, before reporting completion of a task, etc. Run this workflow instead of running individual operations, unless you are explicitly needed to run a specific operation for some reason.

Do not run `donna -p llm new-session` unless the developer explicitly asks to reset or start a fresh Donna session.

### `depmesh`

`depmesh` — a tool for discovering dependencies between project artifacts.

Agents MUST use `depmesh` for dependency types supported by its configuration.

At the start of each work session, read the `depmesh` usage instructions for details:

```bash
depmesh skill usage
```

### `inconsistency-check.py`

`./bin/inconsistency-check.py` — a direct helper script for managing the depmesh-backed consistency-check queue.

Use this script only when the developer explicitly asks you to run it, or when an active Donna workflow explicitly
instructs you to run it. Do not run it opportunistically as a general dependency or consistency check.

The queue is an isolated Taskwarrior database of relation-pair checks. Each queued record represents one oriented
`depmesh` relation from a changed or manually selected file to one related artifact, plus the current SHA-256 checksums
of both files, the relation id, the check status, and an optional markdown report. Pair keys include the relation and
both file checksums, so old records remain as history while changed file content creates a fresh unchecked pair.

The checker loop is the `run-cycle` command. It discovers files changed relative to `main`, queries all configured
`depmesh` relations for those files, reconciles the current relation pairs into the queue, then handles at most one
unchecked pair. If a current pair is already marked `inconsistent`, the loop prints it and exits before spawning any
child checker. Otherwise it runs one read-only child Codex checker for the first unchecked pair, stores the result, and
exits with a code that tells the Donna workflow whether to stop for a fix, continue the loop, or finish successfully.

Main commands:

- `python ./bin/inconsistency-check.py enqueue @/path/to/file` — manually add one file and all configured depmesh relation pairs for that file to the isolated queue.
- `python ./bin/inconsistency-check.py enqueue @/first @/second` — enqueue multiple files.
- `python ./bin/inconsistency-check.py progress --file @/path/to/file` — show queued records where the file is either the changed side or the related side.
- `python ./bin/inconsistency-check.py mark-consistent --changed @/changed --related @/related --relation <relation>` — explicitly mark the current-checksum relation pair as consistent.
- `python ./bin/inconsistency-check.py mark-inconsistent --changed @/changed --related @/related --relation <relation> --report "<markdown>"` — explicitly mark the current-checksum relation pair as inconsistent.
- `python ./bin/inconsistency-check.py clear-queue` — delete all records from the isolated relation-pair queue.
- `python ./bin/inconsistency-check.py run-cycle` — run one checker cycle: discover changed files relative to `main`, reconcile relation pairs, and process at most one unchecked pair.
- `python ./bin/inconsistency-check.py process-queue` — process already queued relation pairs until all are checked or the first inconsistency is found.
- `python ./bin/inconsistency-check.py self-check` — run deterministic script verification without spawning a child Codex checker.

The script stores its relation-pair queue and runtime files only under `@/.session/inconsistency-check/`.

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

### `rg`

Use `rg` for text and file searches unless a structural code query is needed.

`ast-grep` has a higher priority than `rg` whenever a structural code query is needed.

### `taskwarrior`

`task` — Taskwarrior — is the project journal for significant agent-side work.

You MUST use it to write journal records with these exact command templates from the project root:

```bash
./bin/taskwarior.sh log +journal +agent kind:goal "<goal description>"
./bin/taskwarior.sh log +journal +agent kind:step "<phase progress or completion handoff>"
./bin/taskwarior.sh log +journal +agent kind:thought "<important thought>"
./bin/taskwarior.sh log +journal +agent kind:assumption "<important assumption>"
./bin/taskwarior.sh log +journal +agent kind:change "<what changed and where>"
```

Journal messages MUST be single-line strings.

You MUST log:

- Goals of long-running agent-side operations with `kind:goal`.
- Significant steps of long-running operations with `kind:step`.
- Significant thoughts during long-running operations with `kind:thought`.
- Significant assumptions during long-running operations with `kind:assumption`.
- Changes in project source code or project structure with `kind:change`.

You MAY add extra tags after `+agent` and before the message:

```bash
./bin/taskwarior.sh log +journal +agent kind:<message-kind> +<extra-tag>... "<single-line journal message>"
```

For each non-trivial Donna action request or long-running agent task:

1. Write exactly one `goal` record at action-request or task start.
2. Write `step` records at significant phase boundaries.
3. Write `change` records after each meaningful source update batch.
4. Write one final `step` record immediately before reporting completion or handing work back to the developer.

You MUST consider these cases significant phase boundaries:

- A work phase expected to take more than 10 seconds.
- Transition from analysis or research to implementation.
- Transition to a new step in a multi-step process.
- Start or completion of a multi-file or multi-artifact change batch.
- A decision that changes implementation direction.

You MUST NOT log:

- CLI commands you execute.
- Elementary or trivial steps.

You can read the logged journal with:

```bash
./bin/journal-tail.py --lines 20
```

## Special instructions

**When the developer asks you a question — answer it as a question, do not implement the answer as a code change or a plan, just answer the question.**
