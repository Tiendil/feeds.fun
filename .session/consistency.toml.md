# Handoff Spec: `consistency.toml` for `bin/inconsistency-check.py`

## Task

Introduce a root-level `consistency.toml` configuration file for `bin/inconsistency-check.py`.

The script must load this config automatically from the project root. The config controls checker runtime settings,
agent command execution, prompt rendering, output schema, and relation-specific criteria.

Do not implement in this handoff step. This file is the implementation spec for the next agent run.

## Current Problem

`bin/inconsistency-check.py` currently hardcodes:

- runtime paths under `.session/inconsistency-check`
- allowed depmesh relations
- journal command/tag
- relation-specific criteria
- prompt text
- output schema
- child Codex command

The prompt is built inline in `build_child_prompt(...)` and currently embeds full changed/related file contents. This
causes whole-file validation reports that can be true but not actionable for the current work scope.

The new design should let modes change prompt instructions and agent command without editing Python code. The default
prompt should instruct the child agent to read files itself instead of embedding file contents in the prompt.

## Existing Config Style To Follow

`donna.toml` uses command arrays:

```toml
[journal]
cmd = ["./bin/taskwarior.sh", "log", "+journal", "+donna", "kind:event", "{message}"]
```

`depmesh.toml` uses structured top-level arrays/tables:

```toml
[[relations]]
id = "governed_by"
description = "Specifications that apply to the artifact."

[[rules]]
relation = "governed_by"
input = { type = "glob", pattern = "@/ffun/ffun/**/*.py" }
output = { type = "files", pattern = "@/specs/backend_architecture/*.md" }
```

Donna workflows store shell bodies in markdown `bash donna script` blocks. For `consistency.toml`, keep all prompts and
schemas in TOML itself; do not use separate prompt/schema files as source config.

## Requirements

### Config Location

- Add root-level `consistency.toml`.
- The script automatically loads it from project root.
- If missing, fail with a clear error. Do not silently write or use a hidden built-in default once the config is
  introduced, because the config should become part of the project contract.

### Global Defaults And Modes

- All config parameters live globally by default.
- `mode = "default"` selects the global config as-is.
- Other modes are declared under `[modes.<mode-id>]`.
- A mode starts as a copy of the full global config, then each key/table specified in the selected mode replaces the
  corresponding global key/table.
- Replacement is shallow and exact:
  - no parent inheritance
  - no smart merging
  - no partial nested merge
  - no `[modes.<id>.parent]`
- TOML subtables under a mode still represent one top-level replacement. For example, `[modes.diff.output_schema]` and
  `[modes.diff.output_schema.properties.report]` together replace the global `[output_schema]` table as a whole.
- Example: if global `[prompt]` has `template`, and `[modes.diff.prompt]` exists, the mode's whole `prompt` table
  replaces the global `prompt` table. Therefore it must include all required prompt fields.
- The only key that should not be overrideable is `modes` itself.
- The script should support a CLI option to select mode, e.g. `--mode diff`, and should default to config `mode`.
  Practical placement can be either a global parser option or subcommand option.

### Not Configurable

Keep these in Python source:

- Taskwarrior binary and UDA implementation details.
- Queue statuses and status transition names.
- Pair key format.
- JSON parsing mechanics.
- Core record storage mechanics.

Do not add config for:

```toml
[taskwarrior]
bin = "task"

[queue]
statuses = [...]
```

### Configurable Queue Behavior

These must be configurable:

```toml
reset_outdated_to_unchecked_on_matching_pair = true
mark_outdated_during_processing = true
```

Expected meaning:

- `mark_outdated_during_processing`: when processing detects that a registered pair's files are missing or have checksums
  different from the pair record, mark the pair `outdated` instead of checking/removing it.
- `reset_outdated_to_unchecked_on_matching_pair`: when a newly reconciled pair has the same pair key/checksums as an
  existing `outdated` record, reset that record to `unchecked`.

### Journal Config

Use Donna-style command arrays:

```toml
[journal]
cmd = ["./bin/taskwarior.sh", "log", "+journal", "+consistency", "kind:{kind}", "{message}"]
```

The script should format placeholders before executing:

- `{kind}`
- `{message}`

If command formatting fails due to missing variables, fail clearly.

### Agent Command Config

Use argv arrays, not shell strings:

```toml
[agent]
cmd = [
  "codex", "exec",
  "--cd", "{project_root}",
  "--sandbox", "read-only",
  "-c", "approval_policy=\"never\"",
  "--ephemeral",
  "--output-schema", "{schema_path}",
  "--output-last-message", "{output_path}",
  "-"
]
timeout_seconds = 3600
```

No `stdin = "{prompt}"` config is needed. The rendered prompt is always passed to the configured command via stdin.

Command placeholders should include at least:

- `{project_root}`
- `{prompt_path}`
- `{schema_path}`
- `{output_path}`

The script should still store the rendered prompt/schema/output under `.session/inconsistency-check/...` unless
`runtime_dir` overrides the root runtime path.

### Prompt Template

Prompts must live inline in `consistency.toml` as TOML multiline strings. Do not use external prompt files.

The default prompt should not embed full file contents. It should instruct the child agent to read files itself from the
workspace. The child runs read-only, so it may inspect the target files, `git diff`, and additional context files.

Prompt formatting should allow advanced Python expressions like:

- `{pair.relation}`
- `{changed.path}`
- `{git.merge_base}`
- `{fenced_content("Label", text)}`

The user explicitly requested support for advanced Python formatting including function calls.

Implementation options:

- Use a trusted project-local expression renderer.
- Treat prompt templates as code-equivalent project config.
- Do not use arbitrary user input from outside the repo in the expression context.
- Keep the expression context small and explicit.

Suggested context objects/names:

- `pair`
  - `relation`
  - `relation_description`
- `changed`
  - `path`
  - `root_path`
  - `checksum`
- `related`
  - `path`
  - `root_path`
  - `checksum`
- `git`
  - `merge_base`
- `criteria`
  - rendered bullet list/string
- helper functions:
  - `fenced_content(label, content)`
  - optionally `sha256_file(path)` or similar if prompts instruct the child to verify checksums itself

Since default prompts do not embed file contents, do not require `changed.text` or `related.text` in the default mode.
They may still exist in the context for a strict/full-context mode if useful.

### Comparison Base

The script already computes a merge base for changed-file discovery. Make it available to prompt templates as
`{git.merge_base}`.

Meaning:

```bash
git merge-base main HEAD
```

or `origin/main` fallback according to `comparison_base_refs`.

The child agent can run:

```bash
git diff <merge-base> -- <path>
```

to understand current work scope, including uncommitted changes.

The parent script must still verify stored pair checksums before invoking the child and mark stale pairs `outdated`
according to config. Child-side checksum verification is an additional prompt instruction, not the primary safety
mechanism.

### Output Schema

Output schema must be a real TOML table, not a JSON string.

The script should serialize the resolved `[output_schema]` table to the `.schema.json` file before invoking the agent.

Example:

```toml
[output_schema]
type = "object"
additionalProperties = false
required = ["check_status", "report"]

[output_schema.properties.check_status]
type = "string"
enum = ["consistent", "inconsistent"]

[output_schema.properties.report]
type = "string"
```

Mode overrides may replace the whole `[output_schema]` table.

### Relations In Config

Relation descriptions and criteria must be configurable.

Use relation tables:

```toml
[relations.governed_by]
description = "Specifications that apply to the artifact."
criteria = [
  "The implementation or artifact must follow the governing specification's behavior and public contract.",
]
```

Use global common criteria:

```toml
[criteria]
common = [
  "No stale names, missing cases, contradictory defaults, or incompatible examples.",
  "Prefer issues introduced by or made actionable by the current work scope over pre-existing whole-file issues.",
]
```

The rendered `{criteria}` should combine relation-specific criteria and common criteria.

### Allowed Relations

Move hardcoded `ALLOWED_FILE_RELATIONS` into config:

```toml
allowed_file_relations = ["governed_by"]
```

If a relation is allowed but not present in `[relations]`, fail clearly or fall back to depmesh description with empty
custom criteria. Preferred: fail clearly so config remains explicit.

### Runtime Paths

Make runtime root configurable:

```toml
runtime_dir = ".session/inconsistency-check"
```

Subdirectories may remain hardcoded relative to `runtime_dir`:

- `taskwarrior`
- `agent-output`
- `prompts`
- `schemas`
- `self-check`

No need to configure each subdirectory initially.

## Full Example `consistency.toml`

```toml
version = 1

mode = "default"

runtime_dir = ".session/inconsistency-check"
comparison_base_refs = ["main", "origin/main"]
allowed_file_relations = ["governed_by"]

reset_outdated_to_unchecked_on_matching_pair = true
mark_outdated_during_processing = true

[journal]
cmd = ["./bin/taskwarior.sh", "log", "+journal", "+consistency", "kind:{kind}", "{message}"]

[agent]
cmd = [
  "codex", "exec",
  "--cd", "{project_root}",
  "--sandbox", "read-only",
  "-c", "approval_policy=\"never\"",
  "--ephemeral",
  "--output-schema", "{schema_path}",
  "--output-last-message", "{output_path}",
  "-"
]
timeout_seconds = 3600

[prompt]
template = """
You are checking consistency between project artifacts.

Relation: {pair.relation}
Relation description: {pair.relation_description}

Changed file: {changed.path}
Changed checksum: sha256:{changed.checksum}

Related file: {related.path}
Related checksum: sha256:{related.checksum}

Comparison base: {git.merge_base}

Instructions:
- Read the files yourself from the workspace.
- Verify that the current file checksums match the checksums above before analyzing.
- Use git diff against the comparison base to identify the current work scope.
- You may read additional project files when necessary to understand the consistency question.
- Do not edit files.
- Report only inconsistencies that are actionable for the current work scope.
- Return JSON only.

Consistency criteria:
{criteria}
"""

[output_schema]
type = "object"
additionalProperties = false
required = ["check_status", "report"]

[output_schema.properties.check_status]
type = "string"
enum = ["consistent", "inconsistent"]

[output_schema.properties.report]
type = "string"

[criteria]
common = [
  "No stale names, missing cases, contradictory defaults, or incompatible examples.",
  "Prefer issues introduced by or made actionable by the current work scope over pre-existing whole-file issues.",
]

[relations.governed_by]
description = "Specifications that apply to the artifact."
criteria = [
  "The implementation or artifact must follow the governing specification's behavior and public contract.",
]

[relations.governs]
description = "Artifacts governed by the specification."
criteria = [
  "The specification must accurately describe the governed artifact's visible behavior and public contract.",
]

[relations.tested_by]
description = "Tests that verify the artifact."
criteria = [
  "The test must assert behavior that the implementation actually provides.",
  "The implementation must satisfy the documented intent of the test.",
]

[relations.tests]
description = "Artifacts verified by the test."
criteria = [
  "The tested artifact must match the expectations and edge cases encoded in the test.",
]

[relations.imports]
description = "Backend Python files imported by the artifact."
criteria = [
  "Imported APIs, names, types, side effects, and call signatures must still be available and compatible.",
]

[relations.imported_by]
description = "Backend Python files that import the artifact."
criteria = [
  "Caller code must use available APIs, names, types, side effects, and call signatures correctly.",
]

[relations.terms_defined_by]
description = "Dictionaries that define terms used by the artifact."
criteria = [
  "Dictionary terms used by the artifact must match the dictionary's spelling and meaning.",
]

[relations.defines_terms_for]
description = "Artifacts that use terms from the dictionary."
criteria = [
  "Artifacts using dictionary terms must match the dictionary's spelling and meaning.",
]

[relations.indexed_by]
description = "Indexes that list the specification."
criteria = [
  "Index references must include the artifact correctly and without stale names.",
]

[relations.indexes]
description = "Specifications listed by the index."
criteria = [
  "Indexed artifacts must exist conceptually in the index and match its references.",
]

[modes.strict]
allowed_file_relations = ["governed_by"]

[modes.strict.prompt]
template = """
You are checking full consistency between project artifacts.

Relation: {pair.relation}
Relation description: {pair.relation_description}

Changed file: {changed.path}
Changed checksum: sha256:{changed.checksum}

Related file: {related.path}
Related checksum: sha256:{related.checksum}

Comparison base: {git.merge_base}

Instructions:
- Read the files yourself from the workspace.
- Verify that current file checksums match the checksums above before analyzing.
- You may read additional project files when necessary.
- Do not edit files.
- Report any inconsistency between the changed file and related file, even if it appears pre-existing.
- Return JSON only.

Consistency criteria:
{criteria}
"""

[modes.diff]
allowed_file_relations = ["governed_by"]

[modes.diff.prompt]
template = """
You are checking whether the current work introduced or exposed an inconsistency.

Relation: {pair.relation}
Relation description: {pair.relation_description}

Changed file: {changed.path}
Changed checksum: sha256:{changed.checksum}

Related file: {related.path}
Related checksum: sha256:{related.checksum}

Comparison base: {git.merge_base}

Instructions:
- Read the files yourself from the workspace.
- Verify that current file checksums match the checksums above before analyzing.
- Use git diff against the comparison base to inspect the changed hunks.
- You may read additional project files when necessary.
- Do not edit files.
- Report only inconsistencies caused by, changed by, or directly actionable because of the current diff.
- Ignore true but unrelated pre-existing inconsistencies.
- Return JSON only.

Consistency criteria:
{criteria}
"""

[modes.diff.output_schema]
type = "object"
additionalProperties = false
required = ["check_status", "scope", "report"]

[modes.diff.output_schema.properties.check_status]
type = "string"
enum = ["consistent", "inconsistent"]

[modes.diff.output_schema.properties.scope]
type = "string"
enum = ["changed", "unchanged", "unclear"]

[modes.diff.output_schema.properties.report]
type = "string"
```

## Implementation Notes

### Loader

Suggested functions/classes:

- `load_consistency_config(path: Path = PROJECT_ROOT / "consistency.toml") -> ConsistencyConfig`
- `resolve_mode_config(raw_config: dict[str, Any], mode_id: str | None) -> dict[str, Any]`
- `validate_config(config: dict[str, Any]) -> ConsistencyConfig`

Python 3.13 includes `tomllib`, so use it for reading TOML.

Mode replacement algorithm:

1. Load root TOML.
2. Extract `modes` table and selected mode id.
3. Build `base = root_config` without `modes`.
4. If selected mode is not `default`, find `modes[mode_id]`.
5. For each key in the mode table, replace `base[key] = mode_value`.
6. Validate final base.

No nested merge.

### Formatting Commands And Prompts

Need two kinds of formatting:

- command arrays and journal commands: placeholder formatting is enough, but can use the same renderer.
- prompt templates: user requested advanced Python formatting, including function calls.

Treat templates as trusted project-local code. Use an explicit context. Do not expose broad globals.

Possible renderer:

- Parse `{...}` placeholders.
- Evaluate expression inside braces with `eval(expr, {"__builtins__": {}}, context)`.
- This supports `pair.relation`, `fenced_content(...)`, string concatenation, etc.
- Because regular `eval` on object attributes needs objects, use `types.SimpleNamespace` or small dataclasses for context.

If literal braces are needed in prompt text, define an escaping rule. If using Python-format-style parsing, `{{` and `}}`
should become literal braces.

### Config-Driven Runtime Constants

Replace hardcoded constants where appropriate:

- `RELATIVE_RUNTIME_DIR`
- `RUNTIME_DIR`
- `TASKRC_PATH`
- `TASK_DATA_DIR`
- `AGENT_OUTPUT_DIR`
- `PROMPT_DIR`
- `SCHEMA_DIR`
- `SELF_CHECK_DIR`
- `PROJECT_JOURNAL_CMD` / `PROJECT_JOURNAL_TAG`
- `comparison_base_refs`
- `ALLOWED_FILE_RELATIONS`
- `OUTPUT_SCHEMA`
- `relation_specific_criteria(...)`
- child Codex command in `run_child_checker(...)`

Keep Taskwarrior binary and UDA details in source.

### Prompt/Schema Storage

Still store rendered prompt and schema:

- `{runtime_dir}/prompts/<sha256(pair_key)>.md`
- `{runtime_dir}/schemas/<sha256(pair_key)>.schema.json`
- `{runtime_dir}/agent-output/<sha256(pair_key)>.json`

### Backward Compatibility / Queue

Adding config does not need to migrate current queue records.

Existing records still contain pair keys, checksums, status, and reports.

### Self-Check Updates

Update `self-check` to verify:

- config can be loaded
- default mode resolves correctly
- non-default mode replaces global prompt/schema as whole tables
- prompt renders with advanced expressions
- output schema is serialized from TOML table to JSON
- agent command placeholders render correctly
- relation criteria are loaded from config
- allowed relations are loaded from config

### CLI

Add a way to choose mode.

Suggested:

```bash
python ./bin/inconsistency-check.py --mode diff run-cycle
```

If easier with current argparse structure, make it available on subcommands that need it:

```bash
python ./bin/inconsistency-check.py run-cycle --mode diff
```

Preferred: global `--mode` before subcommand.

### Verification

After implementation:

```bash
python -m py_compile bin/inconsistency-check.py
python ./bin/inconsistency-check.py self-check
python ./bin/inconsistency-check.py list-pairs --status outdated --no-count
```

Then run project checks according to `AGENTS.md` constraints. Since this script is outside the backend package but uses
project Python, use Docker-backed scripts where development execution is needed. Host-side `py_compile` and script
inspection have been used previously for this helper, but final implementation should prefer the project-approved
checks where practical.
