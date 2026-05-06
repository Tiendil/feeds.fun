# SWI-Prolog Agent Reasoning Spec

This document defines how agents use SWI-Prolog through the `swipl` command-line interpreter in this repository.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY are to be interpreted according to RFC 2119.

## 1. Purpose

SWI-Prolog is an auxiliary reasoning tool for the agent.

It is used to express explicit facts, rules, constraints, and search problems that help the agent make better decisions while working on a Python + TypeScript backend/frontend codebase.

SWI-Prolog MUST NOT be used as production application code in this repository unless the user explicitly changes this rule.

The intended uses are:

- Reasoning over dependencies.
- Validating implementation plans.
- Ranking candidate actions.
- Computing transitive implications.
- Checking consistency of assumptions.
- Selecting files, tests, or tasks from constrained candidate sets.
- Generating small structured plans from explicit facts.
- Making reasoning inspectable and reproducible.

## 3. Scope boundaries

### 3.1 What SWI-Prolog is for

Agents SHOULD use SWI-Prolog when the problem has an explicit logical shape, such as:

* "This file depends on that artifact."
* "This test should run if one of these artifacts changed."
* "This plan is valid only if these preconditions hold."
* "This option is better if it satisfies more required constraints and fewer risk predicates."
* "These tasks must be ordered according to dependency and safety constraints."
* "This refactor is unsafe if an affected public API is used by a frontend module."

### 3.2 What SWI-Prolog is not for

Agents MUST NOT use SWI-Prolog to:

* Replace ordinary programming judgment.
* Replace type checking, tests, linters, or runtime validation.
* Search code when `ast-grep` is the appropriate tool.
* Discover configured project dependencies when `depmesh` is the appropriate tool.
* Generate large blocks of Python or TypeScript production code.
* Hide uncertain assumptions behind formal-looking facts.
* Produce unverifiable claims about the repository.

### 3.3 Relationship to `depmesh`

`depmesh` is the preferred tool for discovering dependencies between project artifacts.

Agents MUST use `depmesh` for dependency types supported by its configuration.

SWI-Prolog MAY be used after `depmesh` to reason over dependency facts, for example:

* Compute transitive closure.
* Find affected artifacts.
* Detect cycles or invalid dependency directions.
* Rank migration plans by dependency risk.
* Select tests or checks based on dependency impact.

### 3.4 Relationship to `ast-grep`

`ast-grep` is the preferred tool for source-code pattern search and Abstract Syntax Tree based manipulation.

Agents MUST use `ast-grep` for code-structure discovery or code transformation when it is applicable.

SWI-Prolog MAY be used after `ast-grep` to reason over extracted facts, for example:

* Decide which matched functions require follow-up work.
* Group matches by risk or dependency impact.
* Validate whether all required call sites are covered.
* Select a safe order for small refactoring steps.

## 4. Repository Prolog knowledge base

Agents MAY maintain a reusable Prolog knowledge base under:

```text
./prolog
```

This directory MAY contain facts, rules, helper predicates, examples, tests, and temporary generated facts used by the agent.

Recommended structure:

```text
./prolog/
  AGENT_SWIPL.md          # This spec.
  main.pl                 # Optional default entrypoint for agent reasoning.
  lib/
    graph.pl              # Reusable graph/dependency predicates.
    ranking.pl            # Reusable scoring/ranking predicates.
    planning.pl           # Reusable plan validation/order predicates.
    output.pl             # Reusable JSON/text output helpers.
  facts/
    project.pl            # Stable project-level facts, if any.
    conventions.pl        # Stable conventions and policy facts.
  generated/
    current_facts.pl      # Generated facts from depmesh, ast-grep, or file inspection.
  queries/
    impact.pl             # One query-oriented script.
    choose_plan.pl        # Another query-oriented script.
  examples/
    dependency_impact.pl
    plan_validation.pl
    candidate_ranking.pl
```

The layout is advisory, not mandatory.

Agents SHOULD keep reusable predicates in `./prolog/lib`.

Agents SHOULD keep stable facts in `./prolog/facts`.

Agents SHOULD keep tool-derived, refreshable facts in `./prolog/generated`.

Agents MUST NOT treat generated facts as permanently true unless they are refreshed or verified.

Agents SHOULD add comments documenting fact schemas and rule meanings.

Agents SHOULD enhance `./prolog` when a new reusable predicate, fact schema, or reasoning pattern would improve future agent performance.

Agents MUST NOT add Prolog files that affect production Python or TypeScript runtime behavior.

## 5. Invocation rules

The preferred non-interactive invocation pattern is:

```bash
swipl --quiet --no-packs -f none -s ./prolog/main.pl -g main -t halt -- "$@"
```

Meaning:

* `--quiet` suppresses unnecessary banner output.
* `--no-packs` avoids loading external add-on packs.
* `-f none` avoids user startup files.
* `-s FILE` loads the target Prolog file.
* `-g GOAL` runs the named goal.
* `-t halt` exits instead of entering the interactive top level.
* `--` separates SWI-Prolog arguments from application arguments.

Agents SHOULD use deterministic entrypoint predicates named `main/0` for scripts.

Example:

```prolog
:- use_module(library(http/json)).

main :-
    Result = _{status: ok},
    json_write_dict(current_output, Result, [width(0)]),
    nl.
```

Run:

```bash
swipl --quiet --no-packs -f none -s ./prolog/main.pl -g main -t halt
```

Agents MUST inspect command exit status and output.

Agents MUST NOT claim a Prolog result was obtained unless the command actually ran successfully.

Agents SHOULD treat failure, no solution, parse errors, and unexpected empty output as meaningful signals.

## 6. Input and output conventions

### 6.1 Fact input

Agents SHOULD encode structured knowledge as Prolog facts.

Example:

```prolog
artifact('backend/users/service.py', python_file).
artifact('backend/users/api.py', python_file).
artifact('frontend/src/users/UserView.tsx', typescript_file).

depends_on('backend/users/service.py', 'backend/users/api.py', imports).
depends_on('frontend/src/users/UserView.tsx', 'backend/users/api.py', api_contract).

changed('backend/users/api.py').
```

Paths SHOULD be repository-relative.

Paths SHOULD be quoted atoms.

Fact names SHOULD be concrete and domain-specific.

Good:

```prolog
artifact(Path, Kind).
depends_on(From, To, Reason).
changed(Path).
test_covers(TestFile, Artifact).
candidate_plan(Id).
plan_step(PlanId, StepIndex, Action).
```

Bad:

```prolog
thing(X).
related(X, Y).
data(A, B, C).
maybe_useful(X).
```

### 6.2 Output

Agents SHOULD produce machine-readable output when the result will be consumed programmatically.

Preferred output is JSON.

Example:

```prolog
:- use_module(library(http/json)).

main :-
    findall(Path, affected(Path), Paths0),
    sort(Paths0, Paths),
    json_write_dict(current_output, _{affected: Paths}, [width(0)]),
    nl.
```

Agents MAY output plain text for small one-off reasoning tasks.

Agents SHOULD use `sort/2` before output when order is not semantically important.

Agents MUST distinguish between:

* No solution.
* Failed query.
* Runtime error.
* Empty but valid result.

## 7. Modeling rules

### 7.1 Facts

Facts MUST represent information the agent can justify from:

* User instructions.
* Repository files.
* `depmesh` output.
* `ast-grep` output.
* Test output.
* Type-checker output.
* Explicitly inspected source code.
* Stable project conventions documented in the repository.

Agents MUST NOT encode guesses as facts.

Uncertain information SHOULD be represented explicitly.

Example:

```prolog
possible_owner('backend/users/api.py', users_team).
confidence(possible_owner('backend/users/api.py', users_team), low).
```

Do not write:

```prolog
owner('backend/users/api.py', users_team).
```

unless this is actually known.

### 7.2 Rules

Rules SHOULD be small, named clearly, and reusable.

Good:

```prolog
affected_by_change(Target) :-
    changed(Source),
    depends_on(Target, Source, _Reason).
```

Better for transitive reasoning:

```prolog
:- table transitive_depends_on/2.

transitive_depends_on(From, To) :-
    depends_on(From, To, _).

transitive_depends_on(From, To) :-
    depends_on(From, Mid, _),
    transitive_depends_on(Mid, To).
```

Agents SHOULD use tabling for recursive graph rules where cycles are possible.

Agents SHOULD avoid cuts (`!`) unless they are clearly justified.

Agents SHOULD prefer pure predicates when possible.

Agents SHOULD use `dif/2` for logical non-equality when appropriate.

Agents SHOULD use `library(clpfd)` for finite integer constraints.

Example:

```prolog
:- use_module(library(clpfd)).

valid_effort(Effort) :-
    Effort #>= 1,
    Effort #=< 5.
```

### 7.3 Negation

Agents MUST be careful with negation-as-failure.

This pattern:

```prolog
safe(Action) :-
    \+ unsafe(Action).
```

means "Action is safe if `unsafe(Action)` cannot be proven."

It does NOT mean "Action has been proven safe."

When this distinction matters, agents SHOULD encode positive evidence separately.

Example:

```prolog
proven_safe(Action) :-
    checked(Action),
    \+ known_violation(Action).
```

Agents SHOULD NOT use negation-as-failure to hide missing facts.

## 8. Common reasoning patterns

### 8.1 Dependency impact

Use this when facts describe artifacts and dependency relationships.

Assumed meaning:

```prolog
depends_on(From, To, Reason).
```

means `From` depends on `To`.

Example:

```prolog
:- table affected/2.

affected(Source, Target) :-
    depends_on(Target, Source, _Reason).

affected(Source, Target) :-
    depends_on(Intermediate, Source, _Reason),
    affected(Intermediate, Target).
```

Query:

```prolog
main :-
    findall(Target, (changed(Source), affected(Source, Target)), Targets0),
    sort(Targets0, Targets),
    writeln(Targets).
```

This can help answer:

* Which files may be affected by a changed API?
* Which tests should be considered?
* Which frontend modules depend on a backend contract?
* Which artifacts should be inspected before a refactor?

### 8.2 Plan validation

Use this when a proposed implementation plan has ordered steps and constraints.

Example:

```prolog
required_before(check_existing_usage, edit_code).
required_before(edit_code, run_tests).
required_before(run_tests, summarize_result).

plan_step(plan_a, 1, check_existing_usage).
plan_step(plan_a, 2, edit_code).
plan_step(plan_a, 3, run_tests).
plan_step(plan_a, 4, summarize_result).

step_index(Plan, Step, Index) :-
    plan_step(Plan, Index, Step).

violates_order(Plan, Earlier, Later) :-
    required_before(Earlier, Later),
    step_index(Plan, Earlier, I1),
    step_index(Plan, Later, I2),
    I1 >= I2.

valid_plan(Plan) :-
    \+ violates_order(Plan, _, _).
```

Query:

```prolog
main :-
    (   valid_plan(plan_a)
    ->  writeln(valid)
    ;   writeln(invalid)
    ).
```

This can help answer:

* Is the planned edit order safe?
* Did the agent forget a prerequisite check?
* Are tests scheduled after the relevant changes?
* Does a migration plan violate dependency order?

### 8.3 Candidate ranking

Use this when there are multiple possible actions and explicit scoring criteria.

Example:

```prolog
:- use_module(library(lists)).
:- use_module(library(http/json)).

% candidate(Id, Value, Risk, Effort).
candidate(plan_a, 8, 2, 3).
candidate(plan_b, 6, 1, 1).
candidate(plan_c, 9, 5, 2).

valid_candidate(Id) :-
    candidate(Id, _Value, Risk, Effort),
    Risk =< 3,
    Effort =< 4.

score(Id, Score) :-
    candidate(Id, Value, Risk, Effort),
    valid_candidate(Id),
    Score is Value * 10 - Risk * 4 - Effort * 2.

best_candidate(Id, Score) :-
    setof(Score0-Id0, score(Id0, Score0), Pairs),
    last(Pairs, Score-Id).

main :-
    best_candidate(Id, Score),
    json_write_dict(current_output, _{best: Id, score: Score}, [width(0)]),
    nl.
```

This can help answer:

* Which implementation strategy has the best value/risk/effort balance?
* Which tests should run under a time budget?
* Which files should be inspected first?
* Which refactor path minimizes dependency risk?

### 8.4 Test selection

Example:

```prolog
:- table affected/2.

% depends_on(From, To, Reason): From depends on To.
depends_on('backend/users/service.py', 'backend/users/api.py', imports).
depends_on('frontend/src/users/UserView.tsx', 'backend/users/api.py', api_contract).

test_covers('backend/tests/test_users_service.py', 'backend/users/service.py').
test_covers('frontend/src/users/UserView.test.tsx', 'frontend/src/users/UserView.tsx').

changed('backend/users/api.py').

affected(Source, Target) :-
    depends_on(Target, Source, _).

affected(Source, Target) :-
    depends_on(Mid, Source, _),
    affected(Mid, Target).

selected_test(Test) :-
    changed(Source),
    affected(Source, Artifact),
    test_covers(Test, Artifact).

main :-
    findall(Test, selected_test(Test), Tests0),
    sort(Tests0, Tests),
    writeln(Tests).
```

This can help the agent choose a focused initial test set before running broader validation.

### 8.5 Consistency checking

Example:

```prolog
public_api('backend/users/api.py').
changed('backend/users/api.py').

frontend_contract_depends_on('frontend/src/users/UserView.tsx', 'backend/users/api.py').

requires_frontend_check(ApiFile) :-
    public_api(ApiFile),
    changed(ApiFile),
    frontend_contract_depends_on(_, ApiFile).

main :-
    (   requires_frontend_check(Api)
    ->  format('frontend_check_required(~q)~n', [Api])
    ;   writeln(no_frontend_check_required)
    ).
```

This can help prevent an agent from editing a backend API without considering frontend consumers.

## 9. Best practices

Agents SHOULD follow these practices.

### 9.1 Keep the model small

Only encode facts needed for the current reasoning task.

Do not mirror the entire repository into Prolog unless the task requires it.

### 9.2 Keep fact schemas explicit

Every reusable fact predicate SHOULD have a comment explaining its meaning.

Example:

```prolog
% depends_on(From, To, Reason)
% Means: artifact From depends on artifact To for Reason.
depends_on('frontend/src/App.tsx', 'frontend/src/routes.ts', imports).
```

### 9.3 Separate observed facts from inferred facts

Observed facts SHOULD come from tools, files, tests, or user input.

Inferred facts SHOULD be rules.

Good:

```prolog
changed('backend/users/api.py').

affected(Target) :-
    changed(Source),
    depends_on(Target, Source, _).
```

Bad:

```prolog
affected('frontend/src/users/UserView.tsx').
```

unless this fact was directly observed.

### 9.4 Prefer reusable predicates

When a reasoning pattern appears more than once, the agent SHOULD add a reusable predicate under `./prolog/lib`.

Examples:

```prolog
transitive_depends_on/2
affected_by_change/2
valid_plan/1
violates_constraint/2
best_candidate/2
ranked_candidate/2
```

### 9.5 Prefer deterministic script entrypoints

A script used by the agent SHOULD expose `main/0`.

The `main/0` predicate SHOULD produce all relevant output and then exit.

### 9.6 Use tabling for recursive graph reasoning

Recursive dependency and reachability rules SHOULD use tabling when cycles are possible.

Example:

```prolog
:- table reachable/2.

reachable(A, B) :-
    edge(A, B).

reachable(A, C) :-
    edge(A, B),
    reachable(B, C).
```

### 9.7 Use constraints for combinatorial choice

When reasoning about bounded integers, budgets, capacities, ordering, or finite choices, agents SHOULD use `library(clpfd)`.

Example:

```prolog
:- use_module(library(clpfd)).
```

`CLP(FD)` means Constraint Logic Programming over Finite Domains.

### 9.8 Make scoring criteria explicit

When ranking options, the agent MUST encode the scoring rule explicitly.

The agent SHOULD NOT choose a "best" option from Prolog output unless the scoring rule is visible in the Prolog file or query.

### 9.9 Preserve explainability

When a Prolog result materially influences work, the agent SHOULD be able to explain:

* What facts were used.
* What rules were applied.
* What query was run.
* What result was returned.
* How the result affected the implementation decision.

### 9.10 Avoid side effects

Prolog reasoning scripts SHOULD avoid side effects other than reading declared inputs and writing the final result.

Agents SHOULD NOT use predicates such as `shell/1` or process-spawning predicates from Prolog unless explicitly necessary and documented.

### 9.11 Do not overfit one-off facts

Temporary facts SHOULD go under `./prolog/generated` or a clearly temporary query file.

Stable reusable project knowledge MAY go under `./prolog/facts`.

Temporary generated facts SHOULD be refreshed before reuse.

### 9.12 Verify before relying

Agents MUST NOT rely on stale generated facts.

Agents SHOULD regenerate facts from `depmesh`, `ast-grep`, or repository inspection when the relevant files may have changed.

## 10. Failure handling

If a Prolog script fails, the agent MUST inspect the failure before proceeding.

Common cases:

| Case              | Required handling                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------- |
| Syntax error      | Fix the Prolog file or abandon the Prolog-assisted route.                                   |
| Missing predicate | Define the predicate, import the library, or correct the query.                             |
| No solution       | Treat as a valid reasoning result only if the model is complete enough for that conclusion. |
| Empty output      | Determine whether the script failed silently or produced a valid empty result.              |
| Unexpected result | Re-check facts, rule direction, recursion, and negation.                                    |

Agents MUST NOT silently replace a failed Prolog result with an LLM guess.

## 11. Example workflow: dependency-aware planning

A typical workflow:

1. Use `depmesh` to get dependency information.
2. Use `ast-grep` if code structure or specific constructs are relevant.
3. Convert the relevant extracted information into Prolog facts.
4. Add or reuse Prolog rules under `./prolog/lib`.
5. Run a Prolog query through `swipl`.
6. Inspect the output.
7. Use the result to refine the implementation plan.
8. Mention the Prolog-assisted decision when summarizing work.

Example generated facts:

```prolog
% ./prolog/generated/current_facts.pl

artifact('backend/users/api.py', python_file).
artifact('backend/users/service.py', python_file).
artifact('frontend/src/users/UserView.tsx', typescript_file).

depends_on('backend/users/service.py', 'backend/users/api.py', imports).
depends_on('frontend/src/users/UserView.tsx', 'backend/users/api.py', api_contract).

changed('backend/users/api.py').
```

Example query script:

```prolog
% ./prolog/queries/impact.pl

:- use_module(library(http/json)).
:- ['../generated/current_facts.pl'].

:- table affected/2.

affected(Source, Target) :-
    depends_on(Target, Source, _Reason).

affected(Source, Target) :-
    depends_on(Mid, Source, _Reason),
    affected(Mid, Target).

main :-
    findall(Target, (changed(Source), affected(Source, Target)), Targets0),
    sort(Targets0, Targets),
    json_write_dict(current_output, _{affected: Targets}, [width(0)]),
    nl.
```

Run:

```bash
swipl --quiet --no-packs -f none -s ./prolog/queries/impact.pl -g main -t halt
```

Example output:

```json
{"affected":["backend/users/service.py","frontend/src/users/UserView.tsx"]}
```

The agent SHOULD then inspect or test the affected artifacts before finalizing the edit plan.

## 12. Example workflow: choosing a plan

Example:

```prolog
% ./prolog/queries/choose_plan.pl

:- use_module(library(lists)).
:- use_module(library(http/json)).

% candidate_plan(Id, Value, Risk, Effort, Reversibility).
% Higher Value and Reversibility are better.
% Lower Risk and Effort are better.

candidate_plan(minimal_patch, 6, 1, 1, 5).
candidate_plan(local_refactor, 8, 2, 3, 4).
candidate_plan(broad_rewrite, 10, 5, 5, 1).

acceptable_plan(Id) :-
    candidate_plan(Id, _Value, Risk, Effort, _Reversibility),
    Risk =< 3,
    Effort =< 4.

plan_score(Id, Score) :-
    candidate_plan(Id, Value, Risk, Effort, Reversibility),
    acceptable_plan(Id),
    Score is Value * 10 + Reversibility * 3 - Risk * 5 - Effort * 2.

best_plan(Id, Score) :-
    setof(Score0-Id0, plan_score(Id0, Score0), Pairs),
    last(Pairs, Score-Id).

main :-
    best_plan(Id, Score),
    json_write_dict(current_output, _{best_plan: Id, score: Score}, [width(0)]),
    nl.
```

Run:

```bash
swipl --quiet --no-packs -f none -s ./prolog/queries/choose_plan.pl -g main -t halt
```

This is appropriate only if the criteria are explicit and meaningful.

The agent MUST NOT invent numeric scores without explaining their meaning.

## 13. Example workflow: validating an edit sequence

Example:

```prolog
% ./prolog/queries/validate_sequence.pl

:- use_module(library(http/json)).

required_before(inspect_callers, edit_api).
required_before(edit_api, update_tests).
required_before(update_tests, run_tests).

plan_step(plan, 1, inspect_callers).
plan_step(plan, 2, edit_api).
plan_step(plan, 3, update_tests).
plan_step(plan, 4, run_tests).

step_index(Plan, Step, Index) :-
    plan_step(Plan, Index, Step).

violation(Plan, order(Earlier, Later)) :-
    required_before(Earlier, Later),
    step_index(Plan, Earlier, I1),
    step_index(Plan, Later, I2),
    I1 >= I2.

valid_plan(Plan) :-
    \+ violation(Plan, _).

main :-
    findall(V, violation(plan, V), Violations),
    (   Violations = []
    ->  Status = valid
    ;   Status = invalid
    ),
    json_write_dict(current_output, _{status: Status, violations: Violations}, [width(0)]),
    nl.
```

Run:

```bash
swipl --quiet --no-packs -f none -s ./prolog/queries/validate_sequence.pl -g main -t halt
```

## 14. Minimal reusable library examples

### 14.1 `./prolog/lib/graph.pl`

```prolog
:- module(graph, [
    reachable/3,
    transitive_depends_on/3
]).

:- table reachable/3.
:- table transitive_depends_on/3.

% reachable(Edges, From, To)
% Edges is a list of edge(From, To) terms.
reachable(Edges, From, To) :-
    member(edge(From, To), Edges).

reachable(Edges, From, To) :-
    member(edge(From, Mid), Edges),
    reachable(Edges, Mid, To).

% transitive_depends_on(DependsOn, From, To)
% DependsOn is a list of depends_on(From, To, Reason) terms.
transitive_depends_on(DependsOn, From, To) :-
    member(depends_on(From, To, _Reason), DependsOn).

transitive_depends_on(DependsOn, From, To) :-
    member(depends_on(From, Mid, _Reason), DependsOn),
    transitive_depends_on(DependsOn, Mid, To).
```

### 14.2 `./prolog/lib/ranking.pl`

```prolog
:- module(ranking, [
    best_by_score/3
]).

:- use_module(library(lists)).

% best_by_score(+Candidates, :ScorePredicate, -Best)
%
% Candidates is a list of candidate identifiers.
% ScorePredicate is called as call(ScorePredicate, Candidate, Score).
% Best is the candidate with the highest score.
best_by_score(Candidates, ScorePredicate, Best) :-
    findall(Score-Candidate,
            (member(Candidate, Candidates),
             call(ScorePredicate, Candidate, Score)),
            Pairs),
    Pairs \= [],
    sort(Pairs, Sorted),
    last(Sorted, _BestScore-Best).
```

Use reusable modules only when doing so reduces repeated ad hoc code.

## 15. Security and repository hygiene

Agents MUST NOT use Prolog to read unrelated private files.

Agents MUST NOT use Prolog to execute shell commands unless the user explicitly requests it or the repository tooling requires it.

Agents SHOULD keep Prolog files small enough to inspect manually.

Agents SHOULD avoid external Prolog packs unless the user explicitly approves them.

Agents SHOULD prefer standard SWI-Prolog libraries available from the Ubuntu package.

Agents MUST NOT commit stale generated facts unless the repository intentionally tracks them.

Agents SHOULD add generated files to the appropriate ignore mechanism when they are not meant to be tracked.

## 16. Decision reporting

When Prolog materially affects the agent's work, the agent SHOULD report the result in a concise way.

Good summary:

```text
Used SWI-Prolog to validate the edit order. The model encoded required_before/2 constraints for caller inspection, API edit, test update, and test execution. The selected plan had no ordering violations.
```

Good summary:

```text
Used SWI-Prolog over depmesh-derived dependency facts. The query found two affected artifacts: backend/users/service.py and frontend/src/users/UserView.tsx. I inspected both before editing the API.
```

Bad summary:

```text
Prolog said this is fine.
```

Bad summary:

```text
I reasoned formally, so the plan is correct.
```

The agent MUST NOT overstate Prolog results. Prolog proves conclusions only relative to the encoded facts and rules.

## 17. Final rule

Use SWI-Prolog when it makes the agent's reasoning more explicit, checkable, and reproducible.

Do not use SWI-Prolog merely to make ordinary judgment look formal.

```
