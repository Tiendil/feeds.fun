
# Instructions for the AI Agents

This document provides instructions and guidelines for the AI agents working on this project.

Every agent MUST follow the rules and guidelines outlined in this document when performing their work.

## Environment

All development-related operations MUST be performed in Docker containers, see `./docker-compose.yml` for details.

You MUST not perform any development-related operations directly on the host machine.

Most important commands have script shortcuts in `./bin` directory.

Command you are allowed to use:

- `./bin/backend-utils.sh` — run utils in the backend environment, for example `/bin/backend-utils.sh poetry run <your command>`
- `./bin/build-dev-containers.sh` — build base Docker images for development. Call this command after making changes to Docker configs or dependencies.
- `./bin/frontend-utils.sh` — run utils in the frontend environment.
- `./bin/taskwarior.sh` — run Taskwarrior commands related to project journaling.

Code and file searches MUST run on the host using host-installed tools, including `ast-grep` and `rg`, without Docker or development-helper wrappers.
Read and manipulate code on the host machine as well.

## Principles

You MUST follow principles defined in these sections for every related task you perform.

### Fundamentals

These principles are your primary guide doing ALL tasks.

- KISS (Keep It Simple, Stupid) principles.
- DRY (Don't Repeat Yourself) principles.
- YAGNI (You Aren't Gonna Need It) principles.
- SOLID (Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, Dependency Inversion) principles.
- HCD (Human-Centered Design) principles — place the human user at the center of the design process, ensuring that the system is usable, accessible, and meets the needs of its intended audience.
- DCD (Developer-Centered Design) principles — place the developer at the center of the design process, ensuring that the system is maintainable, extensible, and meets the needs of its intended developers.

### Design

These principles are your primary guide for making design decisions.

- Start with the smallest design that satisfies the current explicit requirements and preserves existing behavior. Do not design for hypothetical future requirements.
- Every proposed abstraction, entity, persisted value, workflow, etc. must serve a current requirement and have a current consumer. If removing it does not break required behavior or an existing invariant, omit it.
- Prefer one source of truth. Derive information when it is unambiguous, and do not duplicate facts for convenience, symmetry, debugging, auditability, or possible future use unless explicitly required.
- Before presenting or implementing a design, perform a subtraction pass: try removing each newly introduced concept and keep it only when its absence causes a concrete problem.
- Consider corner cases only when they follow from current requirements, existing behavior, or observed data and materially affect the design. Defer speculative cases instead of building for them.
- When several approaches satisfy the requirements, recommend the less complicated one (with fewer concepts, states, exectution paths, etc.). Present additional flexibility only as an optional extension.

### Implementation

These principles are your primary guide for making implementation decisions.

- You MUST follow Simplicity-first principles.
- Simplicity does not mean merging unrelated interfaces at any cost. Do not combine APIs when doing so introduces mutually exclusive optional arguments, invalid states, pervasive runtime branching, etc.

## Behavior

You MUST adjust your behavior according to rules in these sections.

### Reaction on the developer commands

When processing developer commands, you MUST follow these rules:

- When the developer asks you a question — answer it as a question. Do not implement the answer as a code change or a plan, just answer the question.

### Ask the developer when

You MUST ask an explicit question to the developer when:

- You want or need to perform one of restricted operations.
- You are choosing between multiple options with significant consequences and have no instructions on fully autonomous decision-making.
- You encounter / discover a fact that critically changes the context/requirements/outcome of your current task.

When you are asking the developer, you MUST provide:

- A clear description of the operation you want to perform.
- A clear explanation of why you want to perform the operation.
- A clear explanation of the potential consequences of performing the operation.

### Working with text artifacts

For the needs of this section, text artifacts are any text-based files, including but not limited to source code, configuration files, specification files, and documentation.

You may use grep-like/search/specialized tools to discover relevant text artifacts files.
Search results MUST be treated only as discovery hints.

You MUST read text artifacts in full from beginning to end before relying on, interpreting, reviewing, or changing them.

You MUST NOT use partial-file reading methods (such as `sed`, `head`, `tail`, line-range readers, grep context output, etc.) to read text artifacts.

If a whole-file read is truncated, you MUST repeat it with sufficient output capacity and MUST NOT proceed until the complete file has been read.

Special exceptions to the above rules are:

- You may skip reading each file when bulk editing of particular parts of text artifacts (replacing a particular string in all source files, renaming a particular function, etc.).

### Introducing changes

You MUST separate the stage of introducing changes ("I've introduced some changes and will introduce more later") from the stage of finalizing changes ("I've finished introducing all changes and and count them as final").

On the introducing changes stage:

- You MUST NOT run linters, formatters, or full test suites unless explicitly instructed to do so by the developer or by the project instructions.
- You MUST NOT run any polishing-related workflows unless explicitly instructed to do so by the developer or by the project instructions.
- You MAY run subsets of tests to verify that your changes are working as expected.

On the finalizing changes stage:

- You MUST not run separate linters, formatters, or full test suites unless explicitly instructed to do so by the developer or by the project instructions.
- Instead, you MUST run dedicated polishing workflow that are designed to groom the code after you've introduced changes.

### Resticted operations

You ABSOLUTELY MUST NOT perform the following operations without explicit instructions to do so.

#### Project restrictions

You MUST NOT perform the following operations without explicit instructions to do so:

- Changing project structure, such as moving files around, creating new directories, etc.

#### Dependencies restrictions

You MUST NOT perform the following operations without explicit instructions to do so:

- Installing any new dependencies for any part of the project.
- Updating any kind of lock files.
- Installing any new tools, utilities, or software on the host machine or in the development containers.

#### Docker restrictions

You MUST NOT perform the following operations without explicit instructions to do so:

- Changing `docker-compose.yml`, Dockerfiles or any image-/container-related configuration files.
- Changing Docker service runtime parameters (such as allocated resources, volumes, etc.).
- Changing running Docker services related to other projects or unrelated to the current environment.

#### Git restrictions

You MUST NOT perform the following operations without explicit instructions to do so:

- Staging or unstaging files in git, including commands such as `git add`, `git restore --staged`, and `git reset`.
- Changing git configuration.

## CLI Tools

These CLI tools MUST have the highest priority when an agent is deciding which tool to use for a given task.

You MUST run all listed tools on the host machine unless explicitly instructed to run them in other ways (in a Docker container, in a virtual environment, etc.).

### `donna`

Use Donna to run project-local deterministic workflows.

Run Donna workflows only when explicitly instructed to do so by the developer or by the project instructions.
Do not run workflows on your own initiative.

When you run Donna workflows: Donna controls workflow state and execution flow, you follow the instructions provided by Donna.

Run `donna -p llm skill usage` when:

- You run a workflow first time in the session.
- You need to create a new workflow or modify an existing workflow.
- You need to perform an operation that is not covered by instructions.

Run `donna -p llm new-session` when the developer explicitly instructs you to start a new **Donna** session.

Special instructions:

- Use donna polish workflow to groom the code after you've introduced changes (instead of running linters, formatters and while tests manually).

Here is a list of available workflows.

#### Inconsistency Check Workflow

Run `donna -p llm run @/workflows/inconsistency-check.donna.md` to execute the workflow.

Validate project consistency for artifacts affected by the current work, fixing discovered inconsistencies until every
checked artifact is consistent. Continue automatically while no action is required, and pause when an unresolved
consistency issue or checker failure needs agent judgment.

#### Polish Workflow

Run `donna -p llm run @/workflows/polish.donna.md` to execute the workflow.

Polish the repository by formatting code, running semantic validations, and running runtime checks in the required order.
Successful completion guarantees that formatting, semantic validations, spelling checks, runtime checks, and backend and frontend tests all pass against the final repository state.


### `depmesh`

`depmesh` — a tool for discovering dependencies between project artifacts.

Agents MUST use `depmesh` to discover dependency types supported by its configuration.

At the start of each work session, read the `depmesh` usage instructions for details:

```bash
depmesh skill usage
```

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

Use `rg` for text and file searches.

`ast-grep` has a higher priority than `rg` whenever a structural code query is needed.

### `difftastic`

Use `difft` as the default tool for inspecting code changes and whenever a semantic, syntax-aware diff is useful. Prefer stable, agent-readable output:

```bash
difft --display=inline --color=never --context=6 OLD-PATH NEW-PATH
difft --display=inline --color=never --context=6 --sort-paths OLD-DIR NEW-DIR
GIT_EXTERNAL_DIFF="difft --display=inline --color=never --context=6" git --no-pager diff -- PATH
GIT_EXTERNAL_DIFF="difft --display=inline --color=never --context=6" git --no-pager diff --cached -- PATH
```

Use a classic line-oriented diff, such as `git --no-pager diff --no-ext-diff` or `diff -u`, only when the task explicitly requires raw line-by-line output—for example, producing a patch, inspecting exact whitespace or line endings, or supplying unified-diff input to another tool. Do not choose a classic diff merely because a change is small or limited to text.

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

### `inconsistency-check.py`

`./bin/inconsistency-check.py` — a direct helper script for managing the depmesh-backed consistency-check queue.

Use this script only when the developer explicitly asks you to run it, or when an active workflow explicitly instructs
you to run it. Do not run it opportunistically as a general dependency or consistency check.

The queue is an isolated SQLite database of relation-pair checks. Each queued record represents one oriented `depmesh`
relation from a changed or manually selected file to one related artifact, plus the current SHA-256 checksums of both
files, the relation id, the check status, and an optional markdown report. Pair keys include the relation and both file
checksums, so old records remain as history while changed file content creates a fresh unchecked pair. Reconciliation
immediately marks older checksum versions of the same oriented relation pair as `outdated`.

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

`list-operations` shows the latest pair operations in chronological order. The history records queue creation,
completed child checks, explicit status marks, and automatic status changes. It remains available when queue records
are cleared.

Main commands:

- `python ./bin/inconsistency-check.py enqueue @/path/to/file` — manually add one file and all configured depmesh relation pairs for that file to the isolated queue.
- `python ./bin/inconsistency-check.py enqueue @/first @/second` — enqueue multiple files.
- `python ./bin/inconsistency-check.py enqueue-changed` — enqueue all relation pairs for files changed relative to `main` without processing unchecked pairs or spawning child checkers.
- `python ./bin/inconsistency-check.py sync-queue` — reconcile the mode-eligible queue without processing pairs.
- `python ./bin/inconsistency-check.py list-pairs --current` — show only current-checksum records for relations still returned by `depmesh`.
- `python ./bin/inconsistency-check.py list-operations --last 20` — show the latest pair operations oldest-to-newest within the selected tail.
- `python ./bin/inconsistency-check.py progress --file @/path/to/file` — show queued records where the file is either the changed side or the related side.
- `python ./bin/inconsistency-check.py mark-consistent --changed @/changed --related @/related --relation <relation>` — explicitly mark the current-checksum relation pair as consistent.
- `python ./bin/inconsistency-check.py mark-unchecked --changed @/changed --related @/related --relation <relation>` — reset the current-checksum relation pair to unchecked, clear its previous reviewer result, and require checker reevaluation.
- `python ./bin/inconsistency-check.py mark-inconsistent --changed @/changed --related @/related --relation <relation> --report "<markdown>"` — explicitly mark the current-checksum relation pair as inconsistent.
- `python ./bin/inconsistency-check.py clear-queue` — delete all records from the isolated relation-pair queue without deleting pair-operation history.
- `python ./bin/inconsistency-check.py run-cycle` — reconcile the queue and process one mode-eligible dependency frontier.
- `python ./bin/inconsistency-check.py process-queue` — process one mode-eligible dependency frontier.
- `python ./bin/inconsistency-check.py self-check` — run deterministic script verification without spawning a child Codex checker.

The script stores its relation-pair queue and runtime files only under `@/.session/inconsistency-check/`.
Relation-pair state and structured pair-operation history are stored in
`@/.session/inconsistency-check/state.sqlite3`. The previously migrated `taskwarrior/` database and `operations.jsonl`
remain as recoverable artifacts; the script does not read, write, or delete them.
