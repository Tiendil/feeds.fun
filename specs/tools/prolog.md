# SWI-Prolog agent reasoning

## Goal of the document

This document describes how agents use SWI-Prolog as an auxiliary reasoning tool while working on Feeds Fun.

## Scope

The scope of this specification is limited to agent-side use of the `swipl` command-line interpreter for explicit reasoning over facts, rules, constraints, and search problems.

The following topics are out of scope:

- production Python, TypeScript, database, frontend, backend, or infrastructure behavior.
- installation or upgrade instructions for SWI-Prolog.
- a complete SWI-Prolog tutorial.
- repository dependency discovery that belongs to `depmesh`.
- source-code pattern discovery or transformation that belongs to `ast-grep`.

## Dictionary

- `reasoning model` - a small Prolog program containing facts, rules, constraints, and a query for an agent decision.
- `fact source` - an inspected source of truth such as user input, repository files, `depmesh` output, `ast-grep` output, test output, type-checker output, or linter output.
- `generated fact` - a Prolog fact derived from a fact source for a specific reasoning task.
- `entrypoint predicate` - the predicate passed to `swipl -g`, usually `main/0`, that runs the query and prints the result.

## Role

SWI-Prolog is an auxiliary reasoning tool for agents.

Agents MUST NOT use SWI-Prolog as production implementation code unless the user explicitly changes this rule.

Agents SHOULD use SWI-Prolog when a task has a meaningful logical structure that benefits from explicit facts, rules, constraints, or search.

Typical uses include:

- validating an implementation plan against explicit prerequisites.
- computing transitive impact or reachability from dependency facts.
- choosing between candidate plans, files, tests, or task orders with declared criteria.
- checking consistency between assumptions before editing code.
- making a non-trivial reasoning step inspectable and reproducible.

Agents SHOULD NOT use SWI-Prolog for simple one-step reasoning that is clearer in ordinary prose.

Agents MUST NOT use SWI-Prolog to replace tests, type checks, linters, runtime validation, or direct repository inspection.

## Fact Sources

Facts in a reasoning model MUST be justified by a fact source.

Agents MUST NOT encode guesses as facts.

When information is uncertain, agents SHOULD represent uncertainty explicitly instead of promoting it to a known fact.

Example:

```prolog
possible_owner('ffun/users/api.py', users_area).
confidence(possible_owner('ffun/users/api.py', users_area), low).
```

Do not write `owner('ffun/users/api.py', users_area).` unless that ownership is known from a fact source.

Generated facts SHOULD be refreshed before reuse when the underlying repository files or tool outputs may have changed.

## Modeling Rules

Reasoning models SHOULD be small and limited to the current decision.

Fact names SHOULD be concrete and domain-specific.

Good examples:

```prolog
artifact(Path, Kind).
depends_on(From, To, Reason).
changed(Path).
test_covers(TestFile, Artifact).
candidate_plan(Id).
plan_step(PlanId, StepIndex, Action).
```

Agents SHOULD keep observed information as facts and derived information as rules.

Rules SHOULD be small, clearly named, and reusable when the same reasoning pattern appears more than once.

Recursive graph rules SHOULD use tabling when cycles are possible.

Agents SHOULD use `library(clpfd)` for bounded integer constraints, budgets, capacities, ordering, or finite choices.

Agents MUST use negation-as-failure carefully. A rule such as `safe(Action) :- \+ unsafe(Action).` means only that `unsafe(Action)` cannot be proven from the current model; it does not prove that the action is safe.

When ranking candidates, agents MUST encode the scoring rule explicitly and SHOULD explain the meaning of the criteria when the result affects implementation decisions.

## Invocation

Agents SHOULD run Prolog non-interactively.

For small one-off reasoning tasks, agents SHOULD pass the reasoning goal as an inline string:

```bash
swipl --quiet --no-packs -f none -g "<goal>, halt" -t halt
```

The inline goal MAY use `assertz/1` to declare a small number of temporary facts or rules before running the query.

For complex, multi-line, recursive, or reusable reasoning models, agents SHOULD use a script file:

```bash
swipl --quiet --no-packs -f none -s <script.pl> -g main -t halt
```

The command options have these intended meanings:

- `--quiet` suppresses banner output.
- `--no-packs` avoids external add-on packs.
- `-f none` avoids user startup files.
- `-g "<goal>, halt"` runs an inline goal string and exits.
- `-s <script.pl>` loads the reasoning script.
- `-g main` runs the entrypoint predicate.
- `-t halt` exits instead of entering the interactive top level.

Reasoning scripts SHOULD expose a deterministic `main/0` entrypoint predicate.

Agents MUST inspect the command exit status and output before relying on the result.

Agents MUST NOT claim a Prolog result was obtained unless `swipl` ran successfully.

## Output

Reasoning scripts SHOULD produce machine-readable output when the result will be consumed programmatically.

JSON is preferred for structured output.

Plain text MAY be used for small one-off checks.

Agents SHOULD sort unordered result lists before output when order is not semantically important.

Agents MUST distinguish between:

- no solution.
- failed query.
- runtime error.
- empty but valid result.

## Failure Handling

If a Prolog script fails, the agent MUST inspect the failure before proceeding.

Common cases and required handling:

| Case              | Required handling                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------- |
| Syntax error      | Fix the Prolog file or abandon the Prolog-assisted route.                                   |
| Missing predicate | Define the predicate, import the library, or correct the query.                             |
| No solution       | Treat as a valid result only if the model is complete enough for that conclusion.           |
| Empty output      | Determine whether the script failed silently or produced a valid empty result.              |
| Unexpected result | Re-check facts, rule direction, recursion, negation, and scoring criteria.                  |

Agents MUST NOT silently replace a failed Prolog result with an LLM guess.

## Reporting

When SWI-Prolog materially influences a decision, the agent SHOULD mention the relevant model, query, or result in the work summary.

The summary SHOULD explain:

- what facts were used.
- what rules or constraints were applied.
- what result was returned.
- how the result affected the decision.

## Repository Hygiene

Agents MUST NOT use SWI-Prolog to read unrelated private files.

Agents MUST NOT use SWI-Prolog to execute shell commands unless the user explicitly requests it or the repository tooling requires it.

Agents SHOULD avoid external Prolog packs unless the user explicitly approves them.

Agents SHOULD keep any Prolog reasoning assets small enough to inspect manually.

Agents MUST NOT add Prolog files that affect production Python or TypeScript runtime behavior.
