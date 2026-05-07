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
- `./bin/prolog.sh` — run a small inline SWI-Prolog reasoning program, passed as a single string argument.

If you need to do complex "test & lint & fix" activities, you MUST use the `donna-do` skill to run the code polish workflow.

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

If you want to change something in the above list, you MUST ask for explicit instructions and permission to do so.

## Top priority tools

These tools MUST have the highest priority when an agent is deciding which tool to use for a given task:

### `depmesh`

`depmesh` — a tool for discovering dependencies between project artifacts.

Agents MUST use `depmesh` for dependency types supported by its configuration.

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

### SWI-Prolog `swipl`

`swipl` — the SWI-Prolog command-line interpreter. Use it as an auxiliary reasoning tool for explicit facts, rules, constraints, dependency reasoning, plan validation, ranking, and combinatorial choice.

SWI-Prolog is NOT a production implementation tool for this project.

Agents MUST use `swipl` when a task involves non-trivial structured reasoning that is easier to check as explicit facts, rules, constraints, or search.

Good uses include:

- validating a plan against explicit constraints.
- computing transitive impact or reachability from known facts.
- choosing between several candidates with declared criteria.
- checking consistency between assumptions before editing code.
- deriving an ordered task, file, or test plan from known dependencies.

Agents MUST NOT use `swipl` for:

- Replacing `depmesh` for dependency discovery.
- Replacing `ast-grep` for code-pattern discovery or code transformation.
- Replacing tests, type checks, linters, or runtime validation.
- Writing production Python, TypeScript, or application behavior.
- Encoding repository guesses as facts.
- Encoding a preselected answer as a `candidate` fact and then asking Prolog to confirm it.
- Performing simple one-step reasoning that does not need a formal model.

**When repository facts are needed, agents MUST extract them from the appropriate source first.**

When `swipl` is used to choose between architectures, plans, files, tests, task orders, or other alternatives, agents
SHOULD model independent facts, finite choice dimensions, and constraints, then let Prolog generate/filter/rank the
solutions. Checklist-style validation of a manually chosen plan is allowed only when reported as validation, not as
Prolog inference. See `./specs/tools/prolog.md` for the preferred modeling pattern.

For simple reasoning tasks, pass the reasoning goal as an inline string:

```bash
./bin/prolog.sh "<goal>"
```

For complex reasoning tasks, read `./specs/tools/prolog.md` before using `swipl`; complex tasks SHOULD use `./prolog/main.pl` as the shared entrypoint and call a task-specific predicate.

When `swipl` materially influences a decision, the agent SHOULD mention the relevant model, query, or result in the work summary.

**You MUST log each usage of prolog into `./prolog/log.md` as `h2` markdown section with explanation of why, how, prolog code in fences, output in fences, conclusions you made from it and next actions**

Example of log record:

```
## <short usage description>

<why I decided to use prolog, what I wanted to achieve>

<how I plan to use prolog for this task>

code:

```prolog
<prolog code>
```

output:

```
<prolog output>
```

<conclusions I made from the prolog output and how it influenced my decisions>

<my next actions based on the prolog output and conclusions>

```
