
# Instructions for the AI Agents

This document provides instructions and guidelines for the AI agents working on this project.

Every agent MUST follow the rules and guidelines outlined in this document when performing their work.

## Environment

Read, edit, and search repository files on the host.

Invoke mise from the host. Task definitions determine whether their
commands run on the host or in Docker.

Commands that execute backend/frontend application code or require
backend/frontend dependencies MUST run through the corresponding
mise tasks.

Run `mise run docker:build` after changing development Docker
configuration or backend/frontend dependencies.

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

#### Reading and reusing content

You MUST read text artifacts in full from beginning to end before relying on, interpreting, reviewing, or changing them.
A complete copy of a text artifact already available in the active context satisfies this requirement.

You MUST reuse previously read content while it remains available and current.
You MUST NOT reread an artifact merely because a new turn or work phase begins.

Unless explicitly told otherwise, you MUST assume you are the only active editor of text artifacts.
You MUST NOT reread artifacts or perform freshness checks merely to guard against hypothetical concurrent edits.

Reread only when the required content is no longer available, there is concrete evidence of an intervening change, or the developer or an active workflow explicitly requires a fresh read.

You MUST NOT use partial-file reading methods (such as `sed`, `head`, `tail`, line-range readers, grep context output, etc.) to read text artifacts.

If a whole-file read is truncated, you MUST repeat it with sufficient output capacity and MUST NOT proceed until the complete file has been read.

Special exceptions to the above rules are:

- You may skip reading each file when bulk editing of particular parts of text artifacts (replacing a particular string in all source files, renaming a particular function, etc.).

### Introducing changes

You MUST distinguish implementation from final validation.

- **Implementation:** the planned changes are still in progress. Use focused checks permitted by the project to guide the work.
- **Final validation:** the planned changes are complete and ready for review. Perform the final validation required by the project before reporting completion.

Final validation may require corrections. Make those corrections and repeat the validation required by the project or active workflow for the resulting state.

Task permissions do not override the project's rules about when to run a task.

You MUST NOT report work as complete while required validation has failed or remains incomplete. Report any validation that could not be completed.

#### Feeds Fun validation

During implementation, you MAY run focused tests through permitted mise tasks.

During implementation, you MUST NOT run linters, formatters, full test suites, or the Polish workflow unless the developer or an active workflow explicitly requires them at that stage.

When the planned changes are complete and ready for final validation, assess whether any changes can affect behavior or checks within the scope declared in `workflows/polish.donna.md`:

- If they can, you MUST run `donna -p llm run @/workflows/polish.donna.md` to successful completion.
- If they cannot, you MUST NOT run the Polish workflow.

The developer or an active workflow MAY explicitly override this choice for the current changes.

When the Polish workflow applies, you MUST use it during final validation instead of running its linters, formatters, or full test suites separately, unless the developer or an active workflow explicitly requires separate execution at that stage.

Validate changes outside the Polish workflow's scope as follows:

- Agent instructions or their Cog generation: run `mise run harness:agents.md:generate` and inspect the generated `AGENTS.md`.
- Donna workflow definitions: run `donna -p llm validate @/path/to/workflow.donna.md` for each changed workflow and inspect its rendered instructions.
- Prose-only documentation or specifications: review the changed content, examples, references, and consistency with affected artifacts.

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

## Specifications

This index lists the available specifications and their goals.

- `specs/backend_architecture/db.md` — the Feeds Fun backend architecture for PostgreSQL-backed persistence.
- `specs/backend_architecture/entities.md` — the architecture of Feeds Fun backend entities and data structures used to pass domain, configuration, integration, and command information between backend modules.
- `specs/backend_architecture/errors.md` — how Feeds Fun backend modules represent fatal errors and warnings, and how those values move from lower layers to API, CLI, and worker boundaries.
- `specs/backend_architecture/modules/audit.md` — the responsibility and observable audit behavior of the `ffun.audit` backend module.
- `specs/backend_architecture/modules/benefits.md` — the responsibility and observable benefit-application behavior of the `ffun.benefits` backend module.
- `specs/backend_architecture/modules/entitlements.md` — the responsibility and observable entitlement behavior of the `ffun.entitlements` backend module.
- `specs/backend_architecture/modules/locks.md` — the responsibility and observable coordination behavior of the `ffun.locks` backend module.
- `specs/backend_architecture/modules/one_time_purchases.md` — the responsibility and observable one-time-purchase behavior of the `ffun.one_time_purchases` backend module.
- `specs/backend_architecture/modules/resources.md` — the responsibility and observable accounting behavior of the `ffun.resources` backend module.
- `specs/backend_architecture/modules/subscriptions.md` — the responsibility and observable subscription behavior of the `ffun.subscriptions` backend module.
- `specs/backend_architecture/modules_layout.md` — the stable backend package layout and ownership boundaries for Feeds Fun.
- `specs/backend_architecture/tests.md` — the architecture of Feeds Fun backend tests, including where tests live, how they relate to backend modules, and how they cover entities and errors.
- `specs/behavior/cli.md` — the stable shared behavior of the Feeds Fun backend command-line interface.
- `specs/behavior/cli/benefits.md` — the Feeds Fun CLI command family for applying administrator-authorized benefit transactions and refreshing subscription entitlements from current benefit configuration.
- `specs/behavior/cli/entitlements.md` — the Feeds Fun CLI command family for inspecting user entitlements.
- `specs/behavior/cli/subscriptions.md` — the Feeds Fun CLI command family for inspecting locally persisted purchased-subscription snapshots.
- `specs/behavior/ui_click_tracking.md` — This document defines the UI controls that require click tracking and the naming convention for their tracking identifiers.
- `specs/dictionary.md` — This document defines Feeds Fun terminology that is shared by multiple specifications and dependency metadata rules.
- `specs/documentation/changelog.md` — requirements for changelog documentation.
- `specs/documentation/readme.md` — the expected content, structure, and tone of the Feeds Fun `README.md`.
- `specs/frontend_architecture/components.md` — the architecture, registration, naming, and composition conventions for Feeds Fun frontend components.
- `specs/frontend_architecture/modules_layout.md` — the frontend module structure of Feeds Fun.
- `specs/frontend_architecture/tests.md` — the architecture of Feeds Fun frontend tests, including where tests live, how they relate to frontend modules, and how they cover user-facing logic.
- `specs/meta/backend_modules.md` — requirements for the structure, abstraction level, and content of specifications for individual Feeds Fun backend modules.
- `specs/meta/content.md` — requirements for the level of detail in specification contracts.
- `specs/meta/dictionary.md` — conventions for project-level dictionaries and shared project terminology.
- `specs/meta/directories.md` — conventions for organizing specification files into subject areas.
- `specs/meta/format.md` — the structure and style conventions for specifications in this project.
- `specs/programming/code.md` — conventions for program implementations.
- `specs/programming/content.md` — content requirements for programming specifications.
- `specs/programming/postgresql.md` — conventions for relational schema design and SQL in PostgreSQL.
- `specs/programming/python.md` — language-level implementation conventions for Python source code.

## CLI Tools

These CLI tools MUST have the highest priority when an agent is deciding which tool to use for a given task.

You MUST run all listed tools on the host machine unless explicitly instructed to run them in other ways (in a Docker container, in a virtual environment, etc.).

### `mise`

Use mise to discover and run project tasks. Project tasks tagged `agent` are available to agents, subject to all other project instructions and task-specific restrictions.

You MUST ask the developer for permission before running any other mise task or directly invoking any project script.
Approved tasks and authorized workflows may run their configured scripts and child tasks; this does not authorize invoking those internals directly or bypassing this rule through a generic runner.
Adding the `agent` tag to any other task requires developer approval.

Run `mise tasks ls --no-global --hidden --tag agent` to inspect tagged task metadata.
Pass task arguments after `--`, for example `mise run <task> -- <arguments>`.

The following tasks are available to agents. This list includes task definitions within this repository and its vendored files:

- `mise run backend:ffun` — Run the backend CLI in the development container
- `mise run backend:poetry` — Run Poetry in the backend development container
- `mise run backend:run` — Run a command in the backend development container
- `mise run backend:test` — Run backend tests
- `mise run backend:yoyo` — Run Yoyo in the backend development container
- `mise run check:backend:autoflake` — Check for unused Python imports and variables
- `mise run check:backend:black` — Check Python code formatting
- `mise run check:backend:cli:configs` — Check that the development CLI prints configuration
- `mise run check:backend:cli:help` — Check that the development CLI help works
- `mise run check:backend:flake8` — Check Python code conventions
- `mise run check:backend:isort` — Check Python import formatting
- `mise run check:backend:mypy` — Check backend types
- `mise run check:backend:poetry` — Check backend package configuration
- `mise run check:backend:spelling` — Check backend code spelling
- `mise run check:backend:tach` — Check backend module boundaries
- `mise run check:consistency` — Manage the specification consistency queue
- `mise run check:format` — Check backend and frontend formatting
- `mise run check:frontend:prettier` — Check frontend formatting
- `mise run check:frontend:spelling` — Check frontend code spelling
- `mise run check:frontend:vue-tsc` — Check frontend types
- `mise run check:runtime` — Build and check the production backend image
- `mise run check:semantics` — Check backend and frontend code semantics
- `mise run check:spelling` — Check backend and frontend code spelling
- `mise run docker:build` — Build the backend and frontend development images
- `mise run docker:down:multi-user` — Stop and remove multi-user development containers and shared services, including PostgreSQL
- `mise run docker:down:single-user` — Stop and remove single-user development containers and shared services, including PostgreSQL
- `mise run docker:up:multi-user` — Start the multi-user development services in the background
- `mise run docker:up:single-user` — Start the single-user development services in the background
- `mise run frontend:run` — Run a command in the frontend development container
- `mise run frontend:test` — Run frontend tests
- `mise run harness:agents.md:generate` — Regenerate AGENTS.md
- `mise run harness:generate` — Regenerate harness
- `mise run harness:load` — Update shared harness
- `mise run harness:skills:install` — Install shared harness skills
- `mise run harness:specs:install` — Install selected shared harness specifications
- `mise run journal:tail` — Show or follow project journal records
- `mise run journal:task` — Run Taskwarrior with the project journal configuration

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

Here is a list of available workflows.

#### Inconsistency Check Workflow

Run `donna -p llm run @/workflows/inconsistency-check.donna.md` to execute the workflow.

Validate project consistency for artifacts affected by the current work, fixing discovered inconsistencies until every
checked artifact is consistent. Continue automatically while no action is required, and pause when an unresolved
consistency issue or checker failure needs agent judgment.

#### Polish Workflow

Run `donna -p llm run @/workflows/polish.donna.md` to execute the workflow.

Polish backend and frontend code by formatting it, running semantic and spelling checks, checking the development CLI, and running backend and frontend tests in the required order.
Successful completion means these checks pass against the final repository state.

This workflow covers:

- Backend and frontend application code and tests.
- Dependencies, configuration, and execution environments used by these checks.
- Task definitions, scripts, and workflow execution logic that determine how these checks run.

Prose-only documentation and specification changes, workflow descriptions, agent instructions and their generation, and independent tooling are outside this workflow's scope when they do not affect the code or checks above.


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
mise run journal:task -- log +journal +agent kind:goal "<goal description>"
mise run journal:task -- log +journal +agent kind:step "<phase progress or completion handoff>"
mise run journal:task -- log +journal +agent kind:thought "<important thought>"
mise run journal:task -- log +journal +agent kind:assumption "<important assumption>"
mise run journal:task -- log +journal +agent kind:change "<what changed and where>"
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
mise run journal:task -- log +journal +agent kind:<message-kind> +<extra-tag>... "<single-line journal message>"
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
mise run journal:tail -- --lines 20
```

### `mise run check:consistency`

`mise run check:consistency` — a task for managing the depmesh-backed consistency-check queue.

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

- `mise run check:consistency -- enqueue @/path/to/file` — manually add one file and all configured depmesh relation pairs for that file to the isolated queue.
- `mise run check:consistency -- enqueue @/first @/second` — enqueue multiple files.
- `mise run check:consistency -- enqueue-changed` — enqueue all relation pairs for files changed relative to `main` without processing unchecked pairs or spawning child checkers.
- `mise run check:consistency -- sync-queue` — reconcile the mode-eligible queue without processing pairs.
- `mise run check:consistency -- list-pairs --current` — show only current-checksum records for relations still returned by `depmesh`.
- `mise run check:consistency -- list-operations --last 20` — show the latest pair operations oldest-to-newest within the selected tail.
- `mise run check:consistency -- progress --file @/path/to/file` — show queued records where the file is either the changed side or the related side.
- `mise run check:consistency -- mark-consistent --changed @/changed --related @/related --relation <relation>` — explicitly mark the current-checksum relation pair as consistent.
- `mise run check:consistency -- mark-unchecked --changed @/changed --related @/related --relation <relation>` — reset the current-checksum relation pair to unchecked, clear its previous reviewer result, and require checker reevaluation.
- `mise run check:consistency -- mark-inconsistent --changed @/changed --related @/related --relation <relation> --report "<markdown>"` — explicitly mark the current-checksum relation pair as inconsistent.
- `mise run check:consistency -- clear-queue` — delete all records from the isolated relation-pair queue without deleting pair-operation history.
- `mise run check:consistency -- run-cycle` — reconcile the queue and process one mode-eligible dependency frontier.
- `mise run check:consistency -- process-queue` — process one mode-eligible dependency frontier.
- `mise run check:consistency -- self-check` — run deterministic script verification without spawning a child Codex checker.

The script stores its relation-pair queue and runtime files only under `@/.session/inconsistency-check/`.
Relation-pair state and structured pair-operation history are stored in
`@/.session/inconsistency-check/state.sqlite3`. The previously migrated `taskwarrior/` database and `operations.jsonl`
remain as recoverable artifacts; the script does not read, write, or delete them.

<!--
The following specifications are included in full and apply within their stated scopes.
-->

<!-- BEGIN SPECIFICATION: specs/dictionary.md -->

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
- `benefit parameter` - one named normalized whole-number value accepted by a benefit package template at materialization time.
- `benefit package template` - the locally controlled definition from which one configured product benefit can be materialized.
- `benefit package` - one concrete set of entitlement guarantees produced by materializing a benefit package template with normalized benefit parameters.
- `package materialization` - deterministic validation and application of normalized benefit parameters to one configured benefit package template.
- `entitlement guarantee` - one entitlement kind and integer value promised by a benefit package or another entitlement-granting product concept.
- `purchase state` - the current provider-independent understanding of one purchase at one provider update time.
- `benefit transaction` - one immutable accepted operation that records and atomically applies one complete purchased state.
- `business state` - every field of a current-state snapshot except its provider update time.
- `provider update time` - the authoritative time associated with provider-reported purchased state and used to order competing versions of that state.
- `provider status` - the open-ended lifecycle description received from the external authority for provider-reported purchased state.
- `audit record` - append-only durable record of a business change or event, including its actor and subject entities.
- `architecture test` - a test that verifies cross-cutting structural rules or conventions defined by an architecture specification.

<!-- END SPECIFICATION: specs/dictionary.md -->
