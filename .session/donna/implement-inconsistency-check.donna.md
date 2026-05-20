# Implement Inconsistency Check Workflow

```toml donna
kind = "donna.lib.workflow"
start_operation_id = "review_plan_and_constraints"
```

Implement the depmesh-backed inconsistency checker described in `@/.session/inconsistency-check-plan.md`, with one operation per meaningful artifact, function, or decision path added.

## Review Plan And Constraints

```toml donna
id = "review_plan_and_constraints"
kind = "donna.lib.request_action"
fsm_mode = "start"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Read `@/.session/inconsistency-check-plan.md`, `@/AGENTS.md`, `@/donna.toml`, and the current state of `@/workflows/polish.donna.md`.

Confirm these implementation constraints before editing:

1. Do not change Docker configuration, dependency files, lock files, or unrelated project structure.
2. Keep helper scripts under `@/bin/inconsistency-check/`.
3. Keep runtime state under `@/.session/inconsistency-check/`.
4. Use `depmesh` for supported dependency discovery while changing project artifacts.
5. Use existing project verification paths, especially `@/workflows/polish.donna.md`, when the implementation is expected to work.

If the implementation can proceed, `{{ donna.lib.goto("implement_runtime_workflow") }}`.

If a project constraint blocks the implementation, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Runtime Workflow

```toml donna
id = "implement_runtime_workflow"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Create `@/workflows/inconsistency-check.donna.md`.

The workflow must contain these runtime operations:

1. `run_consistency_cycle`: run `python ./bin/inconsistency-check/main.py run-cycle`, save stdout and stderr, route exit code `0` to success, `10` to the primary fix request, `20` back to itself, and other failures to checker failure handling.
2. `fix_first_inconsistency`: show the saved checker output, instruct the primary agent to fix the first current inconsistent pair, include a false-positive escape hatch, then return to `run_consistency_cycle`.
3. `handle_checker_failure`: show saved stdout and stderr, ask the primary agent to repair tooling or report a blocker, then return to `run_consistency_cycle` or finish blocked.
4. `finish_success`: report the checker summary and tell the agent to summarize files changed, verification, and remaining risks.

After adding the workflow artifact, `{{ donna.lib.goto("implement_script_scaffold") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Script Scaffold

```toml donna
id = "implement_script_scaffold"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Create the helper script entry point at `@/bin/inconsistency-check/main.py`.

Add only the scaffold needed for later operations:

1. A script header documenting the chosen oriented pair-key policy and unsupported deleted/binary file behavior.
2. Constants for runtime paths under `@/.session/inconsistency-check/`.
3. A small data model for relation pairs and check records.
4. CLI dispatch for `run-cycle` and `progress --file`.
5. An exit-code enum or constants for success, inconsistency found, continue cycle, and checker failure.
6. A placeholder or planned location for script-side project journal logging.

After the scaffold exists, `{{ donna.lib.goto("implement_command_helpers") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Command Helpers

```toml donna
id = "implement_command_helpers"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the helper functions that run external commands and parse their structured output.

Required logic:

1. Run subprocesses from the project root with explicit argv lists.
2. Capture stdout, stderr, and exit codes without shell interpolation.
3. Parse JSON Lines output for `depmesh -p automation`.
4. Convert subprocess or JSON parse failures into checker failures with clear diagnostic text.

When these helpers are implemented, `{{ donna.lib.goto("implement_script_journal_logging") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Script Journal Logging

```toml donna
id = "implement_script_journal_logging"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement script-side project journal logging in `@/bin/inconsistency-check/main.py`.

Required logic:

1. Add a helper that invokes `./bin/taskwarior.sh log +journal +agent kind:<kind> "<single-line message>"` from the project root.
2. Ensure every generated journal message is a single-line string.
3. Use this helper only for project journal events, never for relation-pair records.
4. Log important script operations: command start, changed-file discovery result, depmesh query result, queue reconciliation result, existing current inconsistency detection, selected unchecked pair, child checker start and result, pair status update, final run-cycle outcome, progress report invocation, and checker failures.
5. Make journal logging failures visible according to the checker failure policy, unless the script header explicitly documents a safer fallback.

When script journal logging is implemented, `{{ donna.lib.goto("implement_session_state") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Session State

```toml donna
id = "implement_session_state"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the runtime state setup functions.

Required logic:

1. Create `@/.session/inconsistency-check/` runtime directories when the script runs.
2. Create or refresh `taskrc` with a dedicated `data.location`.
3. Define Taskwarrior UDAs exactly for `pair_key`, `file_pair`, `changed_path`, `related_path`, `relation`, `checksum_changed`, `checksum_related`, `check_status`, `report`, and `checked_at`.
4. Ensure the script never uses `@/bin/taskwarior.sh` for pair records; that wrapper is only for script-side project journal logging.

When state setup is implemented, `{{ donna.lib.goto("implement_changed_file_discovery") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Changed File Discovery

```toml donna
id = "implement_changed_file_discovery"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the functions that identify changed files relative to `main`.

Required logic:

1. Resolve the comparison base by preferring local `main`, then `origin/main`.
2. Compute the merge base with `HEAD`.
3. Read `git diff --name-status --diff-filter=ACMR <merge-base> --` so committed, staged, and unstaged changes are included.
4. Normalize paths to root-anchored artifact ids like `@/README.md`.
5. Treat deleted or unsupported file states as explicit checker failures instead of silently skipping them.

When changed file discovery is implemented, `{{ donna.lib.goto("implement_depmesh_queries") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Depmesh Queries

```toml donna
id = "implement_depmesh_queries"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the functions that read configured depmesh relations and query dependencies.

Required logic:

1. Call `depmesh -p automation relations`.
2. Query each changed file separately for each relation with `depmesh -p automation dependencies --relation <relation-id> <artifact>`.
3. Preserve which changed file, relation id, and related artifact produced each pair.
4. Include all configured relations unless the implementation adds an explicit documented allowlist later.
5. Sort candidate pairs deterministically by changed path, relation id, and related path.

When depmesh query logic is implemented, `{{ donna.lib.goto("implement_path_and_checksum_helpers") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Path And Checksum Helpers

```toml donna
id = "implement_path_and_checksum_helpers"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the file normalization and checksum helper functions.

Required logic:

1. Convert between root-anchored artifact ids and root-relative filesystem paths.
2. Read exact current working-tree bytes for both sides of a relation pair.
3. Compute SHA-256 checksums from those bytes.
4. Detect missing, deleted, or unsupported binary files and convert them to explicit checker failures according to the script header policy.

When path and checksum helpers are implemented, `{{ donna.lib.goto("implement_pair_key_builder") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Pair Key Builder

```toml donna
id = "implement_pair_key_builder"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the function that builds stable check identities.

Required logic:

1. Build the human-readable `file_pair` field as `<root-path, sha256:<checksum>>-<root-path, sha256:<checksum>>`.
2. Build the cache identity as `<relation>|<file_pair>`.
3. Preserve separate fields for `pair_key`, `file_pair`, `changed_path`, `related_path`, `relation`, `checksum_changed`, and `checksum_related`.
4. Keep the pair orientation explicit as changed-file to related-file unless the script header documents a different policy.

When pair-key construction is implemented, `{{ donna.lib.goto("implement_taskwarrior_io") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Taskwarrior IO

```toml donna
id = "implement_taskwarrior_io"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement isolated Taskwarrior database access functions.

Required logic:

1. Call `task rc:.session/inconsistency-check/taskrc ...` directly.
2. Prefer JSON export/import or another robust structured path so markdown reports with newlines are stored reliably.
3. Query by exact `pair_key`.
4. Create new records as `check_status=unchecked`.
5. Update existing records while preserving current status and report unless the current check result is being written.

When Taskwarrior IO is implemented, `{{ donna.lib.goto("implement_queue_reconciliation") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Queue Reconciliation

```toml donna
id = "implement_queue_reconciliation"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the logic that turns current relation pairs into a durable queue.

Required logic:

1. Upsert every current relation-pair before validating any pair.
2. Preserve existing current records and reports when the `pair_key` is unchanged.
3. Keep old records for old checksums as cache or history.
4. Ensure only pair keys present in the current cycle can block workflow success.
5. Return the current records in deterministic order.

When queue reconciliation is implemented, `{{ donna.lib.goto("implement_progress_command") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Progress Command

```toml donna
id = "implement_progress_command"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement `python ./bin/inconsistency-check/main.py progress --file <path>`.

Required logic:

1. Normalize the provided path to a root-anchored artifact id.
2. Find records where either `changed_path` or `related_path` equals that artifact id.
3. Summarize counts by `check_status`.
4. List relation, opposite file, checksums, pair key, and report status for each matching record.
5. Avoid requiring agents or humans to compose Taskwarrior filters manually.

When the progress command is implemented, `{{ donna.lib.goto("implement_current_pair_selection") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Current Pair Selection

```toml donna
id = "implement_current_pair_selection"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the decision logic that chooses what `run-cycle` does next before spawning any child agent.

Required logic:

1. If any current record is already `check_status=inconsistent`, print the first deterministic inconsistent pair and return exit code `10`.
2. Otherwise, select the first current `check_status=unchecked` pair.
3. If no current pair is unchecked, return exit code `0`.
4. Guarantee this decision path spawns no child Codex process while a current inconsistent pair already exists.

When current pair selection is implemented, `{{ donna.lib.goto("implement_child_prompt_schema") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Child Prompt And Schema

```toml donna
id = "implement_child_prompt_schema"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the functions that prepare the child Codex check request.

Required logic:

1. Build a prompt with both root-relative paths, both checksums, the relation id, and relation description.
2. Include relation-specific consistency criteria from the plan.
3. Include exact text content for supported text files.
4. Include explicit handling for binary, missing, or unsupported content.
5. Write an output JSON schema requiring `check_status` and `report`.
6. Require inconsistent reports to use one `##` section per issue.

When prompt and schema preparation is implemented, `{{ donna.lib.goto("implement_child_agent_execution") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Child Agent Execution

```toml donna
id = "implement_child_agent_execution"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the function that invokes one child Codex process for one unchecked pair.

Required logic:

1. Run at most one non-interactive `codex exec` process per `run-cycle`.
2. Use read-only sandboxing and no approval prompts for the child process.
3. Store the child output under `@/.session/inconsistency-check/agent-output/`.
4. Pass the prompt through stdin or another safe non-shell mechanism.
5. Treat child process failures as checker failures with enough context to debug.

When child agent execution is implemented, `{{ donna.lib.goto("implement_check_result_update") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Check Result Update

```toml donna
id = "implement_check_result_update"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the function that parses one child-agent result and updates the corresponding pair record.

Required logic:

1. Parse the structured child output against the expected schema.
2. Accept only `consistent` or `inconsistent` as check result statuses.
3. Convert malformed child output into `check_status=inconsistent` with a generated markdown section such as `## Checker output was malformed`.
4. Write `checked_at` timestamps.
5. Update exactly the record for the selected `pair_key`.

When result updates are implemented, `{{ donna.lib.goto("implement_run_cycle_outcome") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Implement Run Cycle Outcome

```toml donna
id = "implement_run_cycle_outcome"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implement the final `run-cycle` outcome selection and human-readable output.

Required logic:

1. After reconciliation and optional one-pair checking, iterate only current records in deterministic order.
2. Print pair key, changed file, related file, relation, and report for the first current inconsistent record, then exit `10`.
3. If the processed pair was consistent and unchecked current records remain, exit `20`.
4. If no current inconsistent or unchecked records remain, print a summary and exit `0`.
5. For checker failures, print actionable diagnostics and return a non-`0`, non-`10`, non-`20` code.

When `run-cycle` outcome logic is implemented, `{{ donna.lib.goto("add_focused_verification_support") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Add Focused Verification Support

```toml donna
id = "add_focused_verification_support"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Add focused verification for the helper script without new dependencies.

Acceptable options:

1. Add tests in the existing backend test framework if the project already has a suitable place and the code can run in Docker-backed project scripts.
2. Add a deterministic dry-run or self-check command to the helper script if that better matches the script's host-tool dependencies.
3. Add both if the blast radius justifies it.

The verification must cover at least changed-file discovery, pair-key construction, queue reconciliation, malformed child output handling, and `progress --file` matching either side of a pair.

When focused verification support is in place, `{{ donna.lib.goto("validate_runtime_workflow") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Validate Runtime Workflow

```toml donna
id = "validate_runtime_workflow"
kind = "donna.lib.run_script"
save_stdout_to = "runtime_workflow_validation_stdout"
save_stderr_to = "runtime_workflow_validation_stderr"
goto_on_success = "render_runtime_workflow"
goto_on_failure = "fix_runtime_workflow_validation"
timeout = 120
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

```bash donna script
#!/usr/bin/env bash
set -e
donna -p llm validate @/workflows/inconsistency-check.donna.md
```

## Fix Runtime Workflow Validation

```toml donna
id = "fix_runtime_workflow_validation"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Donna validation failed for `@/workflows/inconsistency-check.donna.md`.

Stdout:

```text
{{ donna.lib.task_variable("runtime_workflow_validation_stdout") }}
```

Stderr:

```text
{{ donna.lib.task_variable("runtime_workflow_validation_stderr") }}
```

Fix the workflow syntax or transitions, then `{{ donna.lib.goto("validate_runtime_workflow") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Render Runtime Workflow

```toml donna
id = "render_runtime_workflow"
kind = "donna.lib.run_script"
save_stdout_to = "runtime_workflow_render_stdout"
save_stderr_to = "runtime_workflow_render_stderr"
goto_on_success = "review_runtime_workflow_render"
goto_on_failure = "fix_runtime_workflow_render"
timeout = 120
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

```bash donna script
#!/usr/bin/env bash
set -e
donna -p llm render @/workflows/inconsistency-check.donna.md --mode view
```

## Fix Runtime Workflow Render

```toml donna
id = "fix_runtime_workflow_render"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Rendering failed for `@/workflows/inconsistency-check.donna.md`.

Stdout:

```text
{{ donna.lib.task_variable("runtime_workflow_render_stdout") }}
```

Stderr:

```text
{{ donna.lib.task_variable("runtime_workflow_render_stderr") }}
```

Fix the render problem, then `{{ donna.lib.goto("validate_runtime_workflow") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Review Runtime Workflow Render

```toml donna
id = "review_runtime_workflow_render"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Review the rendered runtime workflow and confirm the action requests are clear.

Rendered output:

```text
{{ donna.lib.task_variable("runtime_workflow_render_stdout") }}
```

Confirm that:

1. The primary fix request shows enough context to fix the first inconsistent pair.
2. The checker failure request shows stdout and stderr diagnostics.
3. The false-positive escape hatch cannot cause a silent success without an intentional documented decision.
4. The workflow summary matches the implemented script exit-code contract.

If the rendered workflow is ready, `{{ donna.lib.goto("verify_script_behavior") }}`.

If the rendered workflow needs fixes, `{{ donna.lib.goto("fix_runtime_workflow_validation") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Verify Script Behavior

```toml donna
id = "verify_script_behavior"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Run focused verification for the helper script.

Required checks:

1. Confirm one `run-cycle` invocation processes at most one unchecked relation-pair.
2. Confirm the script exits `10` without spawning a child agent when a current inconsistent pair already exists.
3. Confirm unchanged pair keys preserve cached `consistent` or `inconsistent` records.
4. Confirm editing one file changes the pair key and forces a fresh check.
5. Confirm `.session/taskwarrior` journal records and `.session/inconsistency-check/taskwarrior` pair records remain separate.
6. Confirm `progress --file` reports records where the file is either `changed_path` or `related_path`.
7. Confirm the implemented script logs important runtime operations through `./bin/taskwarior.sh` and does not use that wrapper for relation-pair records.

Use Docker-backed project scripts where project tests or linting are involved. Use Donna or host CLIs only for Donna, git, depmesh, task, codex, and the helper workflow operations that explicitly require them.

When focused verification passes, `{{ donna.lib.goto("run_project_polish") }}`.

If verification reveals implementation issues, fix them and `{{ donna.lib.goto("validate_runtime_workflow") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Run Project Polish

```toml donna
id = "run_project_polish"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Run `@/workflows/polish.donna.md` now that the implementation is expected to be in a working state.

Complete that workflow before returning to this action request.

If polish succeeds, `{{ donna.lib.goto("final_review") }}`.

If polish reports fixable issues, fix them and `{{ donna.lib.goto("validate_runtime_workflow") }}`.

If polish is blocked by unrelated project state, document the blocker and `{{ donna.lib.goto("final_review") }}`.

## Final Review

```toml donna
id = "final_review"
kind = "donna.lib.request_action"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Perform the final implementation review.

Check:

1. `git diff` includes only the intended workflow, helper script, and focused verification changes.
2. No Docker config, dependency files, lock files, or unrelated structure changed.
3. The implementation follows `@/.session/inconsistency-check-plan.md`.
4. Runtime artifacts are written only under `@/.session/inconsistency-check/`.
5. The implemented script contains script-side project journal logging for important runtime operations.

When final review is complete, `{{ donna.lib.goto("finish_success") }}`.

If blocked, document the blocker and `{{ donna.lib.goto("finish_blocked") }}`.

## Finish Success

```toml donna
id = "finish_success"
kind = "donna.lib.finish"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implementation workflow complete. Report changed files, verification performed, and any residual risks to the developer.

## Finish Blocked

```toml donna
id = "finish_blocked"
kind = "donna.lib.finish"
```

If any implementation detail is unclear, consult the original plan at `@/.session/inconsistency-check-plan.md`.

Implementation workflow stopped because a blocker was encountered. Report the blocker, current changed files, and the safest next action to the developer.
