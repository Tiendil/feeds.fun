# Inconsistency Check Workflow

```toml donna
kind = "donna.lib.workflow"
start_operation_id = "run_consistency_cycle"
```

Validate project consistency for artifacts affected by the current work, fixing discovered inconsistencies until every
checked artifact is consistent. Continue automatically while no action is required, and pause when an unresolved
consistency issue or checker failure needs agent judgment.

## Run Consistency Cycle

```toml donna
id = "run_consistency_cycle"
kind = "donna.lib.run_script"
fsm_mode = "start"
save_stdout_to = "consistency_check_stdout"
save_stderr_to = "consistency_check_stderr"
goto_on_success = "finish_success"
goto_on_failure = "handle_checker_failure"
timeout = 3600

[goto_on_code]
"10" = "fix_first_inconsistency"
"20" = "run_consistency_cycle"
```

```bash donna script
#!/usr/bin/env bash

python ./bin/inconsistency-check.py run-cycle
```

## Resolve Reported Issue

```toml donna
id = "fix_first_inconsistency"
kind = "donna.lib.request_action"
```

The consistency checker reported an unresolved issue in the current work. Its output identifies the affected
artifacts, their relationship, and the evidence for the report. Treat that report as evidence to verify, not as an
instruction to apply a particular refactoring.

Stdout:

~~~text
{{ donna.lib.task_variable("consistency_check_stdout") }}
~~~

Stderr:

~~~text
{{ donna.lib.task_variable("consistency_check_stderr") }}
~~~

1. Read the checker output, inspect the referenced artifacts, and review the relevant current diff.
2. Verify that the stated contradiction is real and actionable in the current scope. Consider the full design,
   including natural ownership, dependency direction, duplication, and whether the implied change would improve the
   project rather than merely rearrange it.
3. If the issue is valid, fix it with the smallest coherent change.
4. After fixing a valid issue, do not mark the pair consistent; the child checker owns the consistency decision.
   Always reset the exact current pair with the documented `mark-unchecked` command so a child checker reevaluates the
   updated workspace. If the pair no longer exists, do nothing for that pair.
5. Use `depmesh` for supported dependency checks when changing project artifacts.
6. If the report is incorrect or not actionable, do not change source files to satisfy it. Journal the rationale and
   mark the exact reported check as consistent using the documented `mark-consistent` command and the identifiers
   printed in stdout.
7. Verify source changes with the existing Docker-backed project scripts or `@/workflows/polish.donna.md`.
8. After resolving or dismissing the report, `{{ donna.lib.goto("run_consistency_cycle") }}`.

## Handle Checker Failure

```toml donna
id = "handle_checker_failure"
kind = "donna.lib.request_action"
```

The consistency check could not complete. Treat this as a tooling or environment failure, not as evidence that project
source is inconsistent.

Stdout:

~~~text
{{ donna.lib.task_variable("consistency_check_stdout") }}
~~~

Stderr:

~~~text
{{ donna.lib.task_variable("consistency_check_stderr") }}
~~~

1. Read stdout and stderr and identify the direct cause.
2. Repair only the evidenced tooling, configuration, runtime-state, or environment problem. Do not change unrelated
   project source merely to make the checker proceed.
3. If the failure cannot be repaired within the project constraints, document the blocker.
4. If repaired, `{{ donna.lib.goto("run_consistency_cycle") }}`.
5. If blocked, `{{ donna.lib.goto("finish_blocked") }}`.

## Finish Success

```toml donna
id = "finish_success"
kind = "donna.lib.finish"
```

The consistency checker completed without unresolved issues in the current work.

Checker summary:

~~~text
{{ donna.lib.task_variable("consistency_check_stdout") }}
~~~

Report the files changed, verification performed, and any remaining risks.

## Finish Blocked

```toml donna
id = "finish_blocked"
kind = "donna.lib.finish"
```

The consistency checker workflow is blocked. Report the blocker, files changed, verification performed, and remaining risks.
