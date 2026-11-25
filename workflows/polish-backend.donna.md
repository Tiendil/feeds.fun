# Backend Polish Workflow

```toml donna
kind = "donna.lib.workflow"
start_operation_id = "run_backend_format_autoflake"
```

Format backend code, run semantic and spelling checks, check the development CLI, and run backend tests.
The workflow covers backend application code and tests, along with the dependencies, configuration, environments, tasks, scripts, and workflow logic that affect these checks.
Successful completion means these checks pass against the final repository state.

## Run backend formatting: autoflake

```toml donna
id = "run_backend_format_autoflake"
kind = "donna.lib.run_script"
fsm_mode = "start"
save_stdout_to = "backend_format_autoflake_output"
goto_on_success = "run_backend_format_isort"
goto_on_failure = "fix_backend_format_autoflake"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run format:backend:autoflake
```

## Fix backend formatting: autoflake

```toml donna
id = "fix_backend_format_autoflake"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_format_autoflake_output") }}
```

1. Fix backend autoflake formatting issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run backend formatting: isort

```toml donna
id = "run_backend_format_isort"
kind = "donna.lib.run_script"
save_stdout_to = "backend_format_isort_output"
goto_on_success = "run_backend_format_black"
goto_on_failure = "fix_backend_format_isort"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run format:backend:isort
```

## Fix backend formatting: isort

```toml donna
id = "fix_backend_format_isort"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_format_isort_output") }}
```

1. Fix backend isort formatting issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run backend formatting: black

```toml donna
id = "run_backend_format_black"
kind = "donna.lib.run_script"
save_stdout_to = "backend_format_black_output"
goto_on_success = "run_backend_semantics_tach"
goto_on_failure = "fix_backend_format_black"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run format:backend:black
```

## Fix backend formatting: black

```toml donna
id = "fix_backend_format_black"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_format_black_output") }}
```

1. Fix backend black formatting issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run backend semantic checks: tach

```toml donna
id = "run_backend_semantics_tach"
kind = "donna.lib.run_script"
save_stdout_to = "backend_semantics_tach_output"
goto_on_success = "run_backend_semantics_autoflake_check"
goto_on_failure = "fix_backend_semantics_tach"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run check:backend:tach
```

## Fix backend semantic checks: tach

```toml donna
id = "fix_backend_semantics_tach"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_semantics_tach_output") }}
```

1. Fix backend tach module boundary issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run backend semantic checks: autoflake check

```toml donna
id = "run_backend_semantics_autoflake_check"
kind = "donna.lib.run_script"
save_stdout_to = "backend_semantics_autoflake_output"
goto_on_success = "run_backend_semantics_flake8"
goto_on_failure = "fix_backend_semantics_autoflake_check"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run check:backend:autoflake
```

## Fix backend semantic checks: autoflake check

```toml donna
id = "fix_backend_semantics_autoflake_check"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_semantics_autoflake_output") }}
```

1. Fix backend autoflake semantic issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run backend semantic checks: flake8

```toml donna
id = "run_backend_semantics_flake8"
kind = "donna.lib.run_script"
save_stdout_to = "backend_semantics_flake8_output"
goto_on_success = "run_backend_semantics_mypy"
goto_on_failure = "fix_backend_semantics_flake8"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run check:backend:flake8
```

## Fix backend semantic checks: flake8

```toml donna
id = "fix_backend_semantics_flake8"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_semantics_flake8_output") }}
```

1. Fix backend flake8 issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

{{ donna.lib.include("@/.harness/workflows/polish/python/flake8.md") }}

## Run backend semantic checks: mypy

```toml donna
id = "run_backend_semantics_mypy"
kind = "donna.lib.run_script"
save_stdout_to = "backend_semantics_mypy_output"
goto_on_success = "run_backend_semantics_poetry_check"
goto_on_failure = "fix_backend_semantics_mypy"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run check:backend:mypy
```

## Fix backend semantic checks: mypy

```toml donna
id = "fix_backend_semantics_mypy"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_semantics_mypy_output") }}
```

1. Fix backend mypy issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

{{ donna.lib.include("@/.harness/workflows/polish/python/mypy.md") }}

## Run backend semantic checks: poetry check

```toml donna
id = "run_backend_semantics_poetry_check"
kind = "donna.lib.run_script"
save_stdout_to = "backend_semantics_poetry_check_output"
goto_on_success = "run_backend_spellcheck"
goto_on_failure = "fix_backend_semantics_poetry_check"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run check:backend:poetry
```

## Fix backend semantic checks: poetry check

```toml donna
id = "fix_backend_semantics_poetry_check"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_semantics_poetry_check_output") }}
```

1. Fix backend poetry-check issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run backend spellcheck

```toml donna
id = "run_backend_spellcheck"
kind = "donna.lib.run_script"
save_stdout_to = "backend_spellcheck_output"
goto_on_success = "run_runtime_checks_help"
goto_on_failure = "fix_backend_spellcheck"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run check:backend:spelling
```

## Fix backend spellcheck

```toml donna
id = "fix_backend_spellcheck"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_spellcheck_output") }}
```

1. Fix backend spellcheck issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run runtime checks: help

```toml donna
id = "run_runtime_checks_help"
kind = "donna.lib.run_script"
save_stdout_to = "runtime_checks_help_output"
goto_on_success = "run_runtime_checks_print_configs"
goto_on_failure = "fix_runtime_checks_help"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run check:backend:cli:help
```

## Fix runtime checks: help

```toml donna
id = "fix_runtime_checks_help"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("runtime_checks_help_output") }}
```

1. Fix runtime help-check issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run runtime checks: print configs

```toml donna
id = "run_runtime_checks_print_configs"
kind = "donna.lib.run_script"
save_stdout_to = "runtime_checks_print_configs_output"
goto_on_success = "run_backend_tests"
goto_on_failure = "fix_runtime_checks_print_configs"
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run check:backend:cli:configs
```

## Fix runtime checks: print configs

```toml donna
id = "fix_runtime_checks_print_configs"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("runtime_checks_print_configs_output") }}
```

1. Fix runtime print-configs issues reported above.
2. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Run backend tests

```toml donna
id = "run_backend_tests"
kind = "donna.lib.run_script"
save_stdout_to = "backend_tests_output"
goto_on_success = "finish"
goto_on_failure = "fix_broken_test"
timeout = 300
```

```bash donna script
#!/usr/bin/env bash

set -e

mise run backend:test -- --maxfail=1
```

## Fix broken test

```toml donna
id = "fix_broken_test"
kind = "donna.lib.request_action"
```

```
{{ donna.lib.task_variable("backend_tests_output") }}
```

1. If the test is broken because of `FFUN_LIBRARIAN_TAG_PROCESSORS_CONFIG` or `FFUN_FEEDS_COLLECTIONS_COLLECTION_CONFIGS`, tell the developer about the problem and wait for it to be fixed; do not complete this action request.
2. Fix the broken backend test reported above.
3. `{{ donna.lib.goto("run_backend_format_autoflake") }}`

## Finish

```toml donna
id = "finish"
kind = "donna.lib.finish"
```

Backend Polish workflow completed.
