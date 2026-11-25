
# Instructions for the AI Agents

This document provides instructions and guidelines for the AI agents working on this project.

Every agent MUST follow the rules and guidelines outlined in this document when performing their work.

## Primary agent

The primary agent runs the main session for the developer's overall task.
The primary agent MUST follow the rest of this section.
All other agents MUST skip the rest of this section and follow their assigned role and task.

The primary agent is responsible for completing the overall task.
The primary agent MUST coordinate the work of all other agents on the task.
The primary agent MUST handle communication with the developer.

The primary agent MUST use sub-agents for independent work when delegation would improve speed or quality.

The primary agent SHOULD make project changes directly unless one of the following applies.

- Another agent explicitly takes responsibility for the part of the task that requires the changes.
- The applicable specifications require the primary agent to delegate the changes.
- The developer explicitly instructs the primary agent to delegate the changes.

## Subagents

The primary agent runs the main session for the developer's overall task and is session-scoped.
An agent that spawns a subagent MUST choose the subagent's lifetime and state that choice in the initial assignment.
The spawning agent SHOULD use the scope recommended in the subagent's role description.
If the role description gives no recommendation, the spawning agent SHOULD use subtask scope.

### Lifetimes

- `Session` — The subagent stays available for related assignments until the main session ends.
  The primary agent SHOULD spawn it when first needed and reuse its thread for later assignments that benefit from its context.
- `Subtask` — The subagent handles one assignment and its follow-ups.
  Once the subagent delivers its result and returns any delegated write baton, the spawning agent MUST close the thread if a tool is available to close it.

### Runtime names

The spawning agent MUST use the format for the chosen scope.

- `Session` — `session__<role>`.
- `Subtask` — `subtask__<role>__<task>`.

Use the selected role name for `<role>` and a short description of the assigned work for `<task>`.
Use lowercase ASCII letters, digits, and single underscores within each field.

In Codex, pass the name as a single `task_name` segment when the spawn tool accepts it.
Use the returned path for messages, such as `/root/session__qa_automation` or `/root/subtask__reviewer_technical__subscription_cli` for direct children of the primary agent.
If the spawn tool supplies only an agent ID for addressing, include the name as a label in the initial assignment and use that ID for messages.

## Environment

Read, edit, and search repository files on the host.

Invoke mise from the host. Task definitions determine whether their
commands run on the host or in Docker.

Commands that execute backend/frontend application code or require
backend/frontend dependencies MUST run through the corresponding
mise tasks.

For targeted test runs, prefer these mise commands.

- Backend — `mise run backend:poetry -- run pytest <path>`
- Frontend — `mise run frontend:run -- npm run test:unit -- --run <path>`

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

### Communication

Agents MUST follow the applicable language rules in `specs/meta/language.md`.

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

During implementation, you MUST NOT run linters, formatters, full test suites, or Polish workflows unless the developer or an active workflow explicitly requires them at that stage.

When the planned changes are ready for final validation, assess each Polish workflow.
If the changes can affect the application code, tests, or checks that a Polish workflow covers, you MUST run that workflow to successful completion against the final repository state.

- Backend — `donna -p llm run @/workflows/polish-backend.donna.md`
- Frontend — `donna -p llm run @/workflows/polish-frontend.donna.md`

When both workflows apply, you MUST run the backend workflow first.
You MUST limit Polish validation to the applicable Donna workflows.
The developer or an active workflow MAY explicitly override these choices for the current changes.

When a Polish workflow applies, you MUST use its Donna command for final validation in place of separate runs of its linters, formatters, or full test suites, unless the developer or an active workflow explicitly requires separate execution at that stage.

Validate changes outside the Polish workflows' scope as follows:

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

- `specs/backend/db.md` — the Feeds Fun backend architecture for PostgreSQL-backed persistence.
- `specs/backend/errors.md` — how the Feeds Fun backend represents fatal errors and warnings and passes those values to API, CLI, and worker boundaries.
- `specs/backend/modules/audit.md` — the responsibility and observable audit behavior of the `ffun.audit` backend module.
- `specs/backend/modules/benefits.md` — the responsibility and observable benefit-application behavior of the `ffun.benefits` backend module.
- `specs/backend/modules/core.md` — requirements for the shared entity base in the `ffun.core` backend module.
- `specs/backend/modules/domain.md` — requirements for shared semantic identifier ownership in the `ffun.domain` backend module.
- `specs/backend/modules/entitlements.md` — the responsibility and observable entitlement behavior of the `ffun.entitlements` backend module.
- `specs/backend/modules/locks.md` — the responsibility and observable coordination behavior of the `ffun.locks` backend module.
- `specs/backend/modules/one_time_purchases.md` — the responsibility and observable one-time-purchase behavior of the `ffun.one_time_purchases` backend module.
- `specs/backend/modules/resources.md` — the responsibility and observable accounting behavior of the `ffun.resources` backend module.
- `specs/backend/modules/subscriptions.md` — the responsibility and observable subscription behavior of the `ffun.subscriptions` backend module.
- `specs/backend/modules_and_roles.md` — the Feeds Fun backend layout by module and role.
- `specs/backend/roles/domain.md` — requirements for Python code with the Domain role (`domain.py`) in the Feeds Fun backend.
- `specs/backend/roles/entities.md` — requirements for Python code with the Entities role (`entities.py`) in the Feeds Fun backend.
- `specs/backend/roles/errors.md` — requirements for Python code with the Errors role (`errors.py`) and for error definitions elsewhere in the Feeds Fun backend.
- `specs/backend/roles/operations.md` — requirements for Python code with the Operations role (`operations.py`) in the Feeds Fun backend.
- `specs/backend/roles/settings.md` — requirements for Python code with the Settings role (`settings.py`) and for configuration entities and settings objects elsewhere in the Feeds Fun backend.
- `specs/backend/roles/tests.md` — requirements for Python code with the Tests role (`tests/`) in the Feeds Fun backend.
- `specs/behavior/cli.md` — the stable shared behavior of the Feeds Fun backend command-line interface.
- `specs/behavior/cli/benefits.md` — the Feeds Fun CLI command family for applying administrator-authorized benefit transactions and refreshing subscription entitlements from current benefit configuration.
- `specs/behavior/cli/entitlements.md` — the Feeds Fun CLI command family for inspecting user entitlements.
- `specs/behavior/cli/subscriptions.md` — the Feeds Fun CLI command family for inspecting locally persisted purchased-subscription snapshots.
- `specs/behavior/ui_click_tracking.md` — This document defines the UI controls that require click tracking and the naming convention for their tracking identifiers.
- `specs/dictionary.md` — This document defines Feeds Fun terminology that is shared by multiple specifications and dependency metadata rules.
- `specs/documentation/changelog.md` — requirements for changelog documentation.
- `specs/documentation/readme.md` — the expected content, structure, and tone of the Feeds Fun `README.md`.
- `specs/frontend/components.md` — the architecture, registration, naming, and composition conventions for Feeds Fun frontend components.
- `specs/frontend/modules/logic.md` — requirements for the Feeds Fun frontend logic module.
- `specs/frontend/modules_and_roles.md` — the Feeds Fun frontend layout by module and role.
- `specs/frontend/roles/tests.md` — requirements for the Tests role in the Feeds Fun frontend.
- `specs/meta/backend_modules.md` — requirements for the structure, abstraction level, and content of specifications for individual Feeds Fun backend modules.
- `specs/meta/content.md` — requirements for the level of detail in specification contracts.
- `specs/meta/dictionary.md` — conventions for project-level dictionaries and shared project terminology.
- `specs/meta/directories.md` — conventions for organizing specification files into subject areas.
- `specs/meta/format.md` — the structure and style conventions for specifications in this project.
- `specs/meta/language.md` — language conventions for specifications and for written communication among agents and with the developer.
- `specs/meta/project_areas.md` — the Feeds Fun additions to the shared specification area catalog.
- `specs/programming/code.md` — conventions for program implementations.
- `specs/programming/content.md` — content requirements for programming specifications.
- `specs/programming/dto.md` — the responsibilities and ownership of data transfer objects in a DTO-centric architecture.
- `specs/programming/modules_and_roles.md` — how projects organize source files and code elements by module and role.
- `specs/programming/postgresql.md` — conventions for relational schema design and SQL in PostgreSQL.
- `specs/programming/tests.md` — conventions for organizing automated software tests and verifying program behavior.
- `specs/python/language.md` — language-level implementation conventions for Python source code.
- `specs/python/libs/pydantic.dto_foundation.md` — how projects use a shared Pydantic base class for their DTOs.
- `specs/python/libs/pydantic.md` — conventions for defining and using Pydantic models.
- `specs/python/libs/pytest.md` — conventions for writing Python tests with pytest.
- `specs/python/tests.md` — conventions for writing and organizing Python tests.
- `specs/typescript/libs/vitest.md` — conventions for writing tests with Vitest.
- `specs/typescript/tests.md` — naming conventions for TypeScript tests.

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

#### Backend Polish Workflow

Run `donna -p llm run @/workflows/polish-backend.donna.md` to execute the workflow.

Format backend code, run semantic and spelling checks, check the development CLI, and run backend tests.
The workflow covers backend application code and tests, along with the dependencies, configuration, environments, tasks, scripts, and workflow logic that affect these checks.
Successful completion means these checks pass against the final repository state.

#### Frontend Polish Workflow

Run `donna -p llm run @/workflows/polish-frontend.donna.md` to execute the workflow.

Format frontend code, run type and spelling checks, and run frontend tests.
The workflow covers frontend application code and tests, along with the dependencies, configuration, environments, tasks, scripts, and workflow logic that affect these checks.
Successful completion means these checks pass against the final repository state.


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

Use these command templates from the project root.
You MUST set `agent:` to your runtime name in each record you write.
In Codex, use `/root` for the primary agent and the full name returned by the spawn tool for a subagent, such as `/root/session__qa_automation` or `/root/subtask__reviewer_technical__subscription_cli`.
If the spawn tool supplies only an ID for addressing, use the runtime name from your initial assignment.

```bash
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:goal "<goal description>"
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:step "<phase progress or completion handoff>"
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:thought "<important thought>"
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:assumption "<important assumption>"
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:change "<what changed and where>"
```

Journal messages MUST be single-line strings.

You MUST log:

- Goals of long-running agent-side operations with `kind:goal`.
- Significant steps of long-running operations with `kind:step`.
- Significant thoughts during long-running operations with `kind:thought`.
- Significant assumptions during long-running operations with `kind:assumption`.
- Changes in project source code or project structure with `kind:change`.

You MAY add extra tags before the message.

```bash
mise run journal:task -- log +journal +agent agent:"<agent-name>" kind:"<message-kind>" +<extra-tag>... "<single-line journal message>"
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

Use `journal:tail` to read recent records.
The actor column shows the runtime name in place of the `agent` tag when `agent:` is set.

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

<!-- BEGIN SPECIFICATION: specs/meta/project_areas.md -->

# Project specification areas

## Goal of the document

This document describes the Feeds Fun additions to the shared specification area catalog.

## Scope

This specification applies to the subject areas Feeds Fun adds to the shared specification area catalog.

## Additional areas

Feeds Fun extends the shared area catalog in `./specs/meta/directories.md` with the following areas.

- `backend` — Architecture and behavior of the Feeds Fun backend and its modules.
- `frontend` — Architecture and behavior of the Feeds Fun frontend, including its modules and components.

<!-- END SPECIFICATION: specs/meta/project_areas.md -->

<!-- BEGIN SPECIFICATION: specs/meta/language.md -->

# Language conventions

## Goal of the document

This document describes language conventions for specifications and for written communication among agents and with the developer.

## Scope

This specification applies to prose in specifications and to messages agents write to one another or to the developer.

## Prose

Prose SHOULD address its intended human readers and provide the context they need.
Prose SHOULD explain or reference project knowledge that readers need to understand or act on the text.
Prose SHOULD use a limited vocabulary of familiar words and keep sentence structures simple.
Prose SHOULD NOT use rare, ornate, invented, or needlessly formal wording when familiar wording conveys the intended meaning.
Simplification SHOULD preserve the technical distinctions that readers need to interpret and use the text.

Established technical terms MAY be used when they communicate the intended meaning more clearly than an everyday substitute.
Prose SHOULD explain terms and abbreviations unfamiliar to its intended readers at first use.
The same concept SHOULD have the same name throughout a document or message, without synonyms introduced solely for stylistic variety.

Each sentence SHOULD have one main point.
Conditions and exceptions SHOULD stay close to the statements they qualify.
Prose SHOULD prefer active voice and direct verbs such as “check.”
A sentence SHOULD name the actor when responsibility matters.
Long noun phrases SHOULD be rewritten when they obscure relationships between components, actions, or properties.
A sentence SHOULD repeat a name when a pronoun or other reference could identify more than one thing.

Prose SHOULD state conditions, alternatives, and the order of actions explicitly where they affect interpretation.
Prose SHOULD state quantities, units, and bounds precisely where they affect behavior.
Distinctions such as “all” versus “some” or “either” versus “both” SHOULD be explicit where they affect behavior.
Vague qualifiers such as “fast,” “adequate,” or “normally” SHOULD be replaced with concrete criteria when readers need those criteria to act on or verify a statement.

Prose SHOULD NOT use idioms, decorative metaphors, or promotional claims.
Prose SHOULD NOT use rhetorical questions or filler.
Prose SHOULD state uncertainty and missing information plainly where they affect interpretation.
A specification or message MAY depart from these recommendations when doing so improves readability or when strict adherence would add little practical value.

## Normative requirements

Specifications MUST follow [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).
Each requirement in a specification SHOULD express one main obligation.
Requirements in specifications SHOULD remain distinguishable from surrounding explanations and examples.

<!-- END SPECIFICATION: specs/meta/language.md -->

<!-- BEGIN SPECIFICATION: specs/programming/code.md -->

# Programming code conventions

## Goal of the document

This document describes conventions for program implementations.

## Scope

This specification applies to program source code in all programming languages.
It also covers retroactive application of programming specifications to existing implementations and artifacts.
The content of programming specifications is out of scope.

## Applying specifications to code

Programming specifications MUST be applied to newly written code.
Existing implementations and artifacts MUST NOT be changed retroactively to conform to a programming specification unless the developer explicitly requests the change.
This restriction applies regardless of how the change is made, including when it is carried out by newly written code.

## Enums for closed sets

Project-owned closed sets of named values MUST use enums instead of primitive values or constants.
Primitive values or constants MAY be used when exact literal values are required by a third-party interface or when the values do not represent independently named project concepts.

**Rationale:** Enums make allowed values discoverable and help tools detect invalid member references.
They also simplify refactoring.

### Enum values

Enums MAY omit underlying values only when the language supports enums without them and architectural contracts explicitly require that approach.

Unless an established contract explicitly requires value generation, project-owned enum members with underlying values MUST define those values explicitly and MUST NOT use value generators, such as `enum.auto()` in Python.

**Rationale:** Explicit values keep member identities independent from declaration order or generated naming rules.
They also allow names to change without changing stored or externally exchanged values.

Assigned persisted values MUST NOT be changed or reused for a different enum member.

Enum values used in external compatibility contracts MUST NOT be changed or reused without an explicit compatibility transition.

Deprecated enum members SHOULD be marked using the language's native deprecation mechanism or a `DEPRECATED` comment in the language's comment syntax, including the reason for deprecation.

When choosing types for enum values, consider the enum’s architectural role.

- API-boundary enums SHOULD use values required by the API contract.
- Storage-bound enums SHOULD use values that provide performance and storage efficiency.
- Domain-bound enums SHOULD use values that make runtime semantics clearer, simplify conversion to other representations, and avoid degrading performance.

All other things being equal:

- API-boundary enums SHOULD use human-readable representations, for example, strings.
- Storage-bound enums SHOULD use compact representations, for example, integers.

When converting between enum representations, such as between domain logic and an API boundary, code SHOULD use explicit conversion instead of relying on shared underlying values.

### Enum processing

Code that branches over an enum SHOULD prefer `match` or `switch` statements over `if`/`elif`/`else` chains when the language supports them, to make case handling easier to read and review.

Code that dispatches on an enum MUST handle every member permitted at that point by the operation's contract.
Code SHOULD use static exhaustiveness checking to verify that coverage when supported by the language or type checker.

## Interface contracts

Callers MUST NOT rely on behavior outside the interface’s contract, including implementation details they can see in the source code or observe at runtime.

A module MAY expose a public interface before it has production callers if a current requirement calls for the capability and direct tests verify the interface’s documented contract.

## Types at module boundaries

Where the language supports distinct types, structured application values MUST have explicit types before crossing a module boundary.
Untyped mappings MUST NOT be used for those values unless the data is already being prepared as a serialized representation.

### Semantic primitive types

Where the language supports distinct types, primitive values with a distinct domain meaning MUST use a type specific to that meaning before crossing a module boundary.
Data model fields and public function signatures MUST use the corresponding semantic types for these values.

Raw primitive types MAY be used at the following boundaries where external data is converted into or out of project types.

- parsing.
- rendering.
- storage.
- serialization.

Raw primitive types MAY be used inside local helper code when the value has already been validated or when adding a semantic type would not improve module-boundary clarity.

## Runtime type validation

Functions called through project-controlled typed interfaces SHOULD treat declared parameter types as caller contracts.
They SHOULD NOT perform runtime checks solely to verify that arguments match their declared types.

Runtime validation remains appropriate at untyped or external boundaries, including the following examples.

- HTTP input.
- CLI input.
- configuration.
- deserialized database rows.
- third-party responses.
- plugin data.

Code that parses external input SHOULD validate it during parsing, before constructing typed application values.

Code MUST still validate semantic constraints that are not guaranteed by the contracts of the declared types.
Such constraints include the following.

- non-empty identifiers.
- timezone awareness.
- numeric ranges.
- configured values.
- valid cross-field combinations.

Code that constructs a semantically specific typed value from raw or untyped data MUST validate the semantic invariants of that type at the construction boundary.
Functions and methods that receive the constructed typed value MUST assume those invariants hold and MUST NOT repeat their validation.

## Validation and resolution

Validation functions and methods MUST only verify invariants.
They MUST return no data on success, apart from any validation status required by their contract, and MUST signal failure through the error mechanism defined by their contract.

Each validation function, method, or hook SHOULD enforce one cohesive invariant or one closely related family of constraints.
Independent concerns SHOULD use separate validators.
A single validator MAY examine multiple values when they jointly define one invariant.
Separating independent validation concerns keeps invariants locally understandable, independently testable, and easier to diagnose.

Validation functions and methods MUST NOT return information obtained merely as a by-product of validation through any of the following operations.

- retrieval.
- resolution.
- transformation.
- extraction.

They MAY perform such operations internally when required to verify invariants.
Callers that need the resulting information MUST obtain it separately, unless the operation explicitly acts as a validating constructor.

Functions and methods that return whether a condition holds SHOULD use predicate-based names, such as names with `is`, `has`, or `can` prefixes in the implementation language's naming style, to make their boolean result clear to callers.
Functions and methods whose names express predicates SHOULD return boolean results and MUST NOT signal an error for an ordinary negative result.

A validation function or method MAY return a constructed value when it intentionally serves as a constructor paired with validation.
Constructing and returning that value MUST be part of the operation's explicit contract; this exception does not permit returning dependencies resolved or information incidentally extracted during validation.

Framework validation hooks whose protocols require returning the validated value or instance are exempt from the success-result restriction.

## Data structure conventions

Input whose order is significant SHOULD be represented with ordered collections.

Sets MAY be used internally for de-duplication.
Externally visible output order MUST be produced explicitly according to the relevant behavior or API specification.

Value objects whose equality is based on their data SHOULD be immutable after construction when practical.
Objects used for de-duplication SHOULD be hashable when practical.

Outgoing serialized representations MUST be created at protocol boundaries.
Domain logic SHOULD operate on the corresponding typed application values.

Structured log data MUST use stable keys and MUST NOT contain presentation formatting.

## Function boundaries

A separate function or method MAY be introduced, including at a single call site, when it provides a meaningful boundary, for example by:

- representing a meaningful domain operation.
- centralizing an invariant.
- sharing logic between call sites.
- materially simplifying non-trivial control flow.

Trivial code used at only one call site MUST remain inline when extraction would merely isolate an implementation step without providing a meaningful boundary.
Code is trivial when its intent is clear from its operations and it neither enforces a separate invariant nor contains non-obvious control flow.

## Interchangeable components

When each member of a small, closed family of interchangeable components has meaningful behavior of its own, each implementation SHOULD live in a separate file, module, or package.
Code that groups the implementations SHOULD be limited to definitions and behavior common to the family, plus code that selects or iterates over its members.

## Temporary implementation code

Production code intentionally introduced as a temporary bridge MUST include an adjacent `TODO` comment.
Keeping the explanation next to the bridge makes the exception discoverable during maintenance and review and couples its removal to the code it qualifies; a separate tracked work item alone does not preserve that local context.
The comment MUST explain why the temporary code is currently necessary and identify the concrete condition, milestone, or tracked work item after which it MUST be removed.
Vague comments such as "remove later" are insufficient.
The comment MUST be removed together with the temporary code.

<!-- END SPECIFICATION: specs/programming/code.md -->

<!-- BEGIN SPECIFICATION: specs/backend/modules_and_roles.md -->

# Backend modules and roles

## Goal of the document

This document describes the Feeds Fun backend layout by module and role.

## Scope

This specification applies to Python source files under `ffun/ffun`.

## File and package layout

The backend layout follows `specs/programming/modules_and_roles.md`.
Each declared module is implemented as a Python package.

A declared top-level module named `ffun.<name>` MUST use `./ffun/ffun/<name>/` as its source directory.
A declared nested module MUST use the subdirectory of its parent module that matches the final component of its package name.

## Dedicated specifications

A module or role with requirements beyond its list entry SHOULD have a dedicated specification for those requirements.

A top-level module MAY have a dedicated specification at `specs/backend/modules/<module>.md`, where `<module>` is its package name without the `ffun.` prefix.
A role MAY have a dedicated specification at `specs/backend/roles/<role>.md`, where `<role>` is its lowercase name.

The goal of a dedicated specification MUST name the module or role it governs.
If a role has a source filename or path pattern, the goal SHOULD mention it.
The scope MUST state which code the specification governs.
Its requirements apply alongside the layout rules in this specification.

## Modules

A top-level module MUST own the definitions and behavior that directly implement its responsibilities.

- `ffun.api` owns the backend's HTTP entry points.
- The `ffun.api.spa` nested module owns the HTTP endpoints used by the frontend.
- `ffun.application` owns application construction and application-wide settings.
- `ffun.audit` owns the audit records produced by backend workflows.
- `ffun.auth` owns authentication and authorization logic.
- `ffun.benefits` owns benefit package templates and the benefit transactions that coordinate changes to purchased state and its corresponding entitlements.
- `ffun.cli` owns the command-line interface for managing the backend.
- `ffun.core` owns the domain-neutral technical infrastructure shared by backend modules. See `specs/backend/modules/core.md`.
- `ffun.data_protection` owns data protection and privacy-related behavior.
- `ffun.dispatcher` owns dispatching entries to tag processor queues and tracking per-processor entry processing status.
- `ffun.domain` owns the shared code that represents and supports foundational Feeds Fun domain concepts. See `specs/backend/modules/domain.md`.
- `ffun.entitlements` owns source-specific user entitlement state and merged effective entitlements.
- `ffun.feeds` owns feed storage and feed management.
- `ffun.feeds_collections` owns curated feed collection configuration and behavior.
- `ffun.feeds_discoverer` owns discovery of feeds for external sites.
- `ffun.feeds_links` owns relationships between feeds and users.
- `ffun.google` owns Google service integrations.
- `ffun.integrations` owns source-specific integration plugins.
- `ffun.librarian` owns tag processor orchestration and processor implementations.
- `ffun.library` owns storage and management of news entries.
- `ffun.llms_framework` owns provider-neutral LLM framework logic.
- `ffun.loader` owns loading news entries from feeds.
- `ffun.locks` provides transaction-scoped logical mutual exclusion for backend workflows.
- `ffun.markers` owns read/unread and similar entry markers.
- `ffun.meta` owns business logic that coordinates multiple domain modules.
- `ffun.one_time_purchases` owns durable provider-independent one-time-purchase identities, provider-purchase references, and lifecycle snapshots linked to causal benefit transactions.
- `ffun.ontology` owns stored tag ontology behavior.
- `ffun.openai` owns OpenAI service integration.
- `ffun.parsers` owns feed, entry, site, and OPML parsing logic.
- `ffun.processors_quality` owns quality validation for tagging processors.
- `ffun.product` owns product-specific definitions and behavior with no more specific domain owner when multiple top-level modules need them directly for their own production responsibilities.
- `ffun.queues` owns the shared infrastructure for persistent work queues.
- `ffun.resources` owns per-user resource accounting and enforces caller-supplied limits on reservations.
- `ffun.scores` owns score rules and score calculation.
- `ffun.subscriptions` owns durable provider-independent purchased-subscription identities, provider-subscription references, and lifecycle snapshots linked to causal benefit transactions.
- `ffun.tags` owns tag normalization and validation logic that is not ontology storage.
- `ffun.user_settings` owns user-specific settings storage and behavior.
- `ffun.users` owns user storage and management.

## Roles

Paths in role placement rules are relative to the source directory of the file's most specific declared module.

An **orphaned file** is a Python file in a declared module whose path matches no placement rule for a role other than Public or Private.

- **Domain** — `domain.py` implements the business logic owned by its module. See `specs/backend/roles/domain.md`.
- **Entities** — `entities.py` defines types, semantic identifiers, enums, and entities that represent its module's concepts. See `specs/backend/roles/entities.md`.
- **Errors** — `errors.py` defines its module's exception types and error values. See `specs/backend/roles/errors.md`.
- **Migrations** — Python files matching `migrations/*.py` implement changes to the database schema and stored data. See `Schema Migrations` in `specs/backend/db.md`.
- **Operations** — `operations.py` implements the technical details of its module's communication with storage and other external systems. See `specs/backend/roles/operations.md`.
- **Settings** — `settings.py` defines how its module produces validated, typed settings from configuration inputs and defaults. See `specs/backend/roles/settings.md`.
- **Tests** — Python files under directories named `tests` at any depth contain their module's colocated tests and test support code. See `specs/backend/roles/tests.md`.
  The `make` Python submodule MAY appear only inside tests packages, as `<module>.tests.make`.
- **Utilities** — `utils.py` provides technical helpers that support its module's implementation.
- **Public** — Orphaned files in modules that permit this role contain public interfaces specific to their module.
- **Private** — Orphaned files in modules that permit this role contain implementation code specific to their module.

## Permitted module and role pairs

Every declared module MAY contain files with any role in this list.

- Domain.
- Entities.
- Errors.
- Settings.
- Tests.
- Utilities.

A module MAY contain files with the Migrations role for changes it owns under the database migration rules.
A module MAY contain files with the Operations role when it owns the interaction with an external system that those files implement.

Foundational modules and `ffun.product` MAY contain files with the Public role.
Other declared modules MAY contain files with the Private role.

## Dependencies and public interfaces

Dependency rules apply to direct Python imports between files with different roles or owning modules.

### Import paths

For each definition it exposes at a boundary, a module SHOULD provide a single public import path.

**Rationale:** A single public path gives callers a consistent way to import a definition.

**Example:** The Feeds module defines `Feed` in its public `entities.py` file.
A caller with access to that interface uses `from ffun.feeds.entities import Feed`.

When a public interface exposes a definition from a private Python module, it MUST re-export the definition directly unless it adds behavior that belongs to its role or owning module.

**Rationale:** A direct re-export preserves the definition's identity and contract.

**Example:** `ffun.feeds.domain` exposes `save_feed` through `save_feed = operations.save_feed`.
A caller outside the module with access to that interface uses `from ffun.feeds.domain import save_feed`.

**Example:** `ffun.library.domain` wraps `operations.unlink_all` to own the transaction.

### Public import interfaces

A module MUST expose public interfaces only through Python modules assigned a role unless this specification explicitly allows a broader set of Python modules for it.
A Python module is private to its owning module unless explicitly declared a public interface.

The Python submodules in this list are public interfaces of their owning modules.

- `domain`.
- `entities`.
- `errors`.

Files with the Public role are public import interfaces for functionality owned by their module.
Other production files in foundational modules and `ffun.product` are also public import interfaces for functionality owned by their module.

A file with the Private role MAY be imported only by a file belonging directly to the same module.

All `tests.make` and `tests.helpers` Python submodules are public interfaces for code with the Tests role in another module.

Backend production code MUST NOT import `tests.make` or `tests.helpers`.

### Role dependencies

Role dependency rules apply only to imports between different roles when both files belong directly to the same module.

Within that scope, files with any role MAY import files with the Public or Private role.
Files with the Public or Private role MAY import files with any role except Tests.
Other imports within that scope are allowed only when their direction is listed below.

- Domain: Entities, Errors, Operations, Settings, Utilities
- Entities: Errors, Utilities
- Errors: Entities
- Operations: Entities, Errors, Settings, Utilities
- Settings: Entities
- Tests: Domain, Entities, Errors, Operations, Settings, Utilities
- Utilities: Entities, Errors, Settings

### Module kinds

#### Definitions

- **Foundational modules** provide shared technical infrastructure or foundational domain concepts.
- **Shared-service modules** provide common services for backend modules.
- **Edge modules** own boundaries through which external callers start or use the backend.
- **Domain-level modules** implement backend capabilities and workflows within their areas of responsibility.

#### Membership

- Foundational: `ffun.core`, `ffun.domain`
- Shared-service: `ffun.audit`, `ffun.locks`, `ffun.queues`
- Edge: `ffun.api`, `ffun.application`, `ffun.cli`, and their nested modules at any depth
- Domain-level: every other declared top-level module except `ffun.product`

### Module dependencies

A dependency between modules is allowed only when this specification permits its direction.

- Foundational: Foundational
- Shared-service: Foundational, Shared-service
- Domain-level: Foundational, Shared-service, Domain-level, `ffun.product`
- `ffun.product`: Foundational, Shared-service, Domain-level
- Edge: Foundational, Shared-service, Domain-level, `ffun.product`, Edge

Permissions to depend on `ffun.product` apply to the product-specific definitions and behavior the caller uses.

<!-- END SPECIFICATION: specs/backend/modules_and_roles.md -->

<!-- BEGIN SPECIFICATION: specs/frontend/modules_and_roles.md -->

# Frontend modules and roles

## Goal of the document

This document describes the Feeds Fun frontend layout by module and role.

## Scope

This specification applies to frontend source files under `site/src`.

## File and package layout

The frontend layout follows `specs/programming/modules_and_roles.md`.

The frontend MUST be implemented as a Vue 3 project under `site`.

Application source code MUST live under `site/src`.

## Modules

- `site/src` owns frontend application construction and cross-cutting frontend architecture tests.
- `site/src/assets` owns static assets such as icons, images, and similar frontend media.
- `site/src/components` owns reusable Vue components.
- `site/src/components/body_list` owns components for rendering entry body content and reference lists.
- `site/src/components/collections` owns components for collection browsing and subscription workflows.
- `site/src/components/main` owns shared main-content presentation components.
- `site/src/components/notifications` owns notification components.
- `site/src/components/page_footer` owns footer components.
- `site/src/components/page_header` owns header components.
- `site/src/components/side_pannel` owns side-panel controls.
- `site/src/components/tags` owns tag display and tag-filter components.
- `site/src/components/toolbar` owns reusable actions displayed in top content toolbars.
- `site/src/css` owns Tailwind-backed shared CSS.
- `site/src/inputs` owns small user-input components.
- `site/src/integrations` owns integration-specific frontend views or widgets.
- `site/src/layouts` owns top-level page layout components.
- `site/src/logic` owns shared frontend logic, API clients, constants, settings, and utilities.
  See `specs/frontend/modules/logic.md`.
- `site/src/plugins` owns Vue plugins.
- `site/src/router` owns Vue Router configuration.
- `site/src/stores` owns Pinia stores.
- `site/src/values` owns small display components for simple values.
- `site/src/views` owns page-level Vue views.

## Roles

Files that match no specific role placement rule have the Public or Private role permitted by their owning module.

- **Tests** — Source files under directories named `tests` at any depth contain their module's tests and test support code.
  Files with the Tests role MUST follow `specs/frontend/roles/tests.md`.
- **Public** — Files with this role contain public interfaces specific to their module.
- **Private** — Files with this role contain implementation code specific to their module.

## Permitted module and role pairs

Every declared module MAY contain files with the Tests role.

The application module MAY contain files with the Private role.
Every other declared frontend module MAY contain files with the Public role.

## Dependencies and public interfaces

Dependency rules govern direct imports and named references to registered Vue components in templates.
They apply between governed frontend source files when the files have different roles or owning modules.
Direct imports include type-only imports, dynamic imports, and re-exports from another file.
The target of a template reference is the file that defines the registered component.

### Public interfaces

Files with the Public role are public import interfaces for their modules.
Registered Vue components defined in files with the Public role are public template interfaces for their modules.
Vue component imports and template references MUST follow `specs/frontend/components.md`.

### Role dependencies

Role dependency rules apply when files with different roles belong directly to the same module.
Within that scope, the only permitted direction is from a file with the Tests role to a file with the Public or Private role.

### Module kinds

#### Definitions

- **Foundational modules** provide shared styles and static assets.
- **Shared-service modules** provide shared frontend logic, state, or Vue plugins.
- **Presentation modules** provide reusable frontend components.
- **View modules** compose the frontend content for individual pages.
- **Edge modules** own application construction or route selection.

#### Membership

- Foundational — `site/src/assets` and `site/src/css`.
- Shared-service — `site/src/logic`, `site/src/plugins`, and `site/src/stores`.
- Presentation — `site/src/components` and its declared nested modules, `site/src/inputs`, `site/src/integrations`, `site/src/layouts`, and `site/src/values`.
- View — `site/src/views`.
- Edge — the application module at `site/src` and `site/src/router`.

### Module dependencies

A dependency between modules is allowed only when this specification permits its direction.

- Foundational — Foundational.
- Shared-service — Foundational and Shared-service.
- Presentation — Foundational, Shared-service, and Presentation.
- View — Foundational, Shared-service, and Presentation.
- Edge — Foundational, Shared-service, Presentation, View, and Edge.

The `site/src/logic` module MAY depend on Vue components defined in files with the Public role in Presentation modules.

Views SHOULD compose layouts, components, inputs, values, stores, and logic.
Composition lets views coordinate pages using shared presentation and logic.

Shared logic SHOULD avoid depending on Vue components unless the dependency is explicitly UI-specific.
Limiting component dependencies keeps shared logic usable outside component rendering.

<!-- END SPECIFICATION: specs/frontend/modules_and_roles.md -->
