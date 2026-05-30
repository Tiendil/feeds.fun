# Inconsistency Check Workflow

```toml donna
kind = "donna.lib.workflow"
start_operation_id = "run_consistency_cycle"
```

Repeatedly check files changed relative to `main` against their `depmesh`-related artifacts, pausing for the primary agent to repair the first current inconsistency.

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

## Fix First Inconsistency

```toml donna
id = "fix_first_inconsistency"
kind = "donna.lib.request_action"
```

The consistency checker found the first current inconsistent relation pair.

Stdout:

~~~text
{{ donna.lib.task_variable("consistency_check_stdout") }}
~~~

Stderr:

~~~text
{{ donna.lib.task_variable("consistency_check_stderr") }}
~~~

1. Read the two files reported for the inconsistent pair.
2. Fix the inconsistency with the smallest coherent source change.
3. Use `depmesh` for supported dependency checks if the fix touches project artifacts.
4. If the report is a false positive, do not make unrelated source changes; repair the checker state or tooling with a clear rationale so the same false positive does not block the next cycle.
5. Verify with existing Docker-backed project scripts or `@/workflows/polish.donna.md` when the codebase is expected to work.
6. After the fix or false-positive handling is complete, `{{ donna.lib.goto("run_consistency_cycle") }}`.

## Handle Checker Failure

```toml donna
id = "handle_checker_failure"
kind = "donna.lib.request_action"
```

The consistency checker failed before it could produce a normal workflow outcome.

Stdout:

~~~text
{{ donna.lib.task_variable("consistency_check_stdout") }}
~~~

Stderr:

~~~text
{{ donna.lib.task_variable("consistency_check_stderr") }}
~~~

1. Repair the checker workflow, script, runtime state, or environment issue reported above.
2. If the failure cannot be repaired within the project constraints, document the blocker.
3. If repaired, `{{ donna.lib.goto("run_consistency_cycle") }}`.
4. If blocked, `{{ donna.lib.goto("finish_blocked") }}`.

## Finish Success

```toml donna
id = "finish_success"
kind = "donna.lib.finish"
```

The consistency checker completed without current inconsistencies.

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
