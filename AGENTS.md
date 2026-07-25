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

When choosing a workflow, first list the available workflows with `donna -p llm list`.

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

Use this script only when the developer explicitly asks you to run it, or when an active workflow explicitly instructs
you to run it. Do not run it opportunistically as a general dependency or consistency check.

The queue is an isolated Taskwarrior database of relation-pair checks. Each queued record represents one oriented
`depmesh` relation from a changed or manually selected file to one related artifact, plus the current SHA-256 checksums
of both files, the relation id, the check status, and an optional markdown report. Pair keys include the relation and
both file checksums, so old records remain as history while changed file content creates a fresh unchecked pair.
Reconciliation immediately marks older checksum versions of the same oriented relation pair as `outdated`.

The `run-cycle` command reconciles all non-outdated queue pairs against current files, `depmesh` relations, and the
active mode. A mode that requires branch changes marks a pair `outdated` when its changed-side file is outside the
branch diff; other modes retain all current queued pairs. Each invocation processes the current dependency frontier.
It returns success only after a fresh cycle confirms that no eligible unchecked or inconsistent pairs remain;
otherwise its exit status tells the caller whether more processing or inconsistency resolution is required.

Consistency decisions after a valid fix belong to the child checker.
Primary agents MUST NOT mark a valid report consistent after applying a fix.
After every valid fix, the primary agent MUST reset the exact current relation pair with `mark-unchecked` before continuing so a child checker reevaluates the updated workspace.
If the pair no longer exists, the primary agent MUST do nothing for that pair.

The `enqueue-changed` command reconciles relation pairs for Git-changed files without processing them.

The `sync-queue` command performs mode-aware queue reconciliation without processing pairs.

`list-pairs` shows queue history by default. Pass `--current` to show only records whose stored checksums match the
current files and whose oriented relation is still returned by `depmesh`; this current-only view does not mutate the
queue.

Main commands:

- `python ./bin/inconsistency-check.py enqueue @/path/to/file` — manually add one file and all configured depmesh relation pairs for that file to the isolated queue.
- `python ./bin/inconsistency-check.py enqueue @/first @/second` — enqueue multiple files.
- `python ./bin/inconsistency-check.py enqueue-changed` — enqueue all relation pairs for files changed relative to `main` without processing unchecked pairs or spawning child checkers.
- `python ./bin/inconsistency-check.py sync-queue` — reconcile the mode-eligible queue without processing pairs.
- `python ./bin/inconsistency-check.py list-pairs --current` — show only current-checksum records for relations still returned by `depmesh`.
- `python ./bin/inconsistency-check.py progress --file @/path/to/file` — show queued records where the file is either the changed side or the related side.
- `python ./bin/inconsistency-check.py mark-consistent --changed @/changed --related @/related --relation <relation>` — explicitly mark the current-checksum relation pair as consistent.
- `python ./bin/inconsistency-check.py mark-unchecked --changed @/changed --related @/related --relation <relation>` — reset the current-checksum relation pair to unchecked, clear its previous reviewer result, and require checker reevaluation.
- `python ./bin/inconsistency-check.py mark-inconsistent --changed @/changed --related @/related --relation <relation> --report "<markdown>"` — explicitly mark the current-checksum relation pair as inconsistent.
- `python ./bin/inconsistency-check.py clear-queue` — delete all records from the isolated relation-pair queue.
- `python ./bin/inconsistency-check.py run-cycle` — reconcile the queue and process one mode-eligible dependency frontier.
- `python ./bin/inconsistency-check.py process-queue` — process one mode-eligible dependency frontier.
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

### Specification reading

Grep-like tools, including `rg`, MAY be used to discover relevant specification files. Search results MUST be treated only as discovery hints.

Before relying on, interpreting, reviewing, or changing a specification file, an agent MUST read that file in full from beginning to end. Agents MUST NOT use `sed`, `head`, `tail`, line-range readers, grep context output, or any other partial-file reading method to read specification content. If a whole-file read is truncated, the agent MUST repeat it with sufficient output capacity and MUST NOT proceed until the complete file has been read.

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
