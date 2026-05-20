# Plan: Donna Depmesh Consistency Workflow

## Goal

Implement a Donna workflow that repeatedly checks consistency between files changed relative to `main` and their `depmesh`-related files. The workflow should use an isolated Taskwarrior database under `.session` as a pair-check queue, ask separate Codex agents to perform pair reviews, and ask the primary agent to fix the first current inconsistent pair before rerunning the cycle.

## Proposed Artifacts

1. Add a permanent Donna workflow, for example `workflows/inconsistency-check.donna.md`.
2. Add a dedicated script directory `bin/inconsistency-check/` for all helper scripts related to this workflow.
3. Add a primary supporting script, for example `bin/inconsistency-check/main.py`, using only Python standard library plus existing CLIs: `git`, `depmesh`, `task`, and `codex`.
4. Let the script create and maintain `.session/inconsistency-check/` at runtime:
   - `.session/inconsistency-check/taskrc`
   - `.session/inconsistency-check/taskwarrior/`
   - `.session/inconsistency-check/agent-output/`
   - optional temporary prompt/schema files

No Docker configuration, dependency files, lock files, or project structure outside the explicitly declared `bin/inconsistency-check/` script directory should change.

## Project Journal Requirement

The implemented supporting scripts must log each important runtime step or operation with the standard project Taskwarrior journal command from `AGENTS.md`:

```bash
./bin/taskwarior.sh log +journal +agent kind:<kind> "<single-line message>"
```

This logging is only for project journal events. It must not be used for relation-pair records; the pair-check queue must still use the isolated `.session/inconsistency-check/taskwarrior` database.

The script should log at least: command start, changed-file discovery result, depmesh relation query result, queue reconciliation result, existing current inconsistency detection, selected unchecked pair, child checker start and result, pair status update, final run-cycle outcome, progress report invocation, and checker failures.

## Donna Workflow Shape

The workflow can be a small state machine:

1. `run_consistency_cycle`: `donna.lib.run_script`
   - Runs the supporting script from the project root, for example `python ./bin/inconsistency-check/main.py run-cycle`.
   - Saves stdout to a Donna task variable, for example `consistency_check_output`.
   - Uses a long timeout because each invocation may run at most one Codex agent.
   - Exit routing:
     - `0` -> `finish_success`
     - `10` -> `fix_first_inconsistency`
     - `20` -> `run_consistency_cycle`
     - any other non-zero code -> `handle_checker_failure`
2. `fix_first_inconsistency`: `donna.lib.request_action`
   - Shows the first inconsistent pair and markdown report emitted by the script.
   - Orders the primary agent to fix the inconsistency between those two files.
   - After the fix, transitions back to `run_consistency_cycle`.
3. `handle_checker_failure`: `donna.lib.request_action`
   - Shows stdout/stderr from the script and asks the primary agent to fix the workflow/tooling failure.
   - Transitions back to `run_consistency_cycle` after repair, or to an error finish if blocked.
4. `finish_success`: `donna.lib.finish`
   - Reports the script summary: changed files, relation pairs, checked pairs, queue state, and consistency count.

Use `goto_on_code` for exit codes `10` and `20`. This keeps "found inconsistency" distinct from "checked one pair as consistent and should continue" and from "script failed".

## Supporting Script Responsibilities

### 1. Discover Current Changed Files

Resolve the comparison base without network access:

1. Prefer local `main`.
2. Fall back to `origin/main` if local `main` is absent.
3. Compute the merge base with `HEAD`.

Use the merge base against the working tree, not only `HEAD`, so fixes made by the primary agent during the workflow affect the next cycle before any commit exists. The discovery step must include every file changed relative to `main`, whether the change is committed on the current branch, staged, or unstaged. The effective command should behave like:

```bash
git diff --name-status --diff-filter=ACMR <merge-base> --
```

Convert every path to a root-anchored artifact id like `@/README.md`. Deleted files need an explicit policy because their current content and some `depmesh` relations may be unavailable; first implementation can report them as a checker failure or unsupported case rather than silently skipping them.

### 2. Query Depmesh Relations

Use depmesh's automation protocol, not the LLM text protocol, so the script consumes structured JSONL:

```bash
depmesh -p automation relations
depmesh -p automation dependencies --relation <relation-id> @/path/to/file
```

First, read the configured relation list from `depmesh`. Then query each changed file separately for each configured relation because a multi-file depmesh query merges results and loses which changed file produced each dependency. Include all configured relations unless the workflow later adds an explicit allowlist.

Create candidate relation-pairs from `(changed file, related file, relation)`. Treat the relation as part of the check identity, even when the same two files are connected by multiple relations, because each relation can imply different consistency criteria. Use deterministic ordering by changed path, relation id, and related path. The script should upsert all current relation-pairs into the isolated Taskwarrior DB before it validates any pair.

### 3. Build Stable Pair Keys

For every candidate relation-pair:

1. Read exact bytes from the current working tree.
2. Compute `sha256` checksums for both files.
3. Build the required file-pair mapping field as:

```text
<root-based file path, sha256:<checksum>>-<root-based file path, sha256:<checksum>>
```

4. Build the cache identity from the relation plus the file-pair mapping, for example:

```text
<relation>|<root-based file path, sha256:<checksum>>-<root-based file path, sha256:<checksum>>
```

Store separate fields for the relation-inclusive `pair_key`, exact `file_pair`, changed path, related path, relation id, and individual checksums. The `file_pair` field is the required human-readable mapping, not the only query surface. The per-side path fields must be canonical root-anchored paths so future reporting can find every check where a file participates as either the changed file or the related file.

Canonicalize the file-pair path order if duplicate reverse relations should be collapsed; otherwise keep it oriented as changed-file to related-file. The relation must remain part of the identity either way. The implementation should choose the orientation policy explicitly and document it in the script header.

### 4. Use an Isolated Taskwarrior Database

Do not use `./bin/taskwarior.sh` for pair records because that wrapper intentionally targets the project journal database via `.taskrc`.

Instead, the supporting script should create a dedicated Taskwarrior config at `.session/inconsistency-check/taskrc` with its own data location:

```text
data.location=.session/inconsistency-check/taskwarrior
confirmation=no

uda.pair_key.type=string
uda.pair_key.label=Relation Pair Key
uda.file_pair.type=string
uda.file_pair.label=File Pair
uda.changed_path.type=string
uda.changed_path.label=Changed Path
uda.related_path.type=string
uda.related_path.label=Related Path
uda.relation.type=string
uda.relation.label=Relation
uda.checksum_changed.type=string
uda.checksum_changed.label=Changed Checksum
uda.checksum_related.type=string
uda.checksum_related.label=Related Checksum
uda.check_status.type=string
uda.check_status.label=Check Status
uda.check_status.values=unchecked,consistent,inconsistent,
uda.report.type=string
uda.report.label=Report
uda.checked_at.type=string
uda.checked_at.label=Checked At
```

Use direct `task rc:.session/inconsistency-check/taskrc ...` calls, or JSON import/export, so this database cannot interfere with `.session/taskwarrior`. Prefer JSON import/export for records because the markdown report may contain newlines and shell-sensitive characters.

Taskwarrior already has a built-in `status` field, so the implementation should use a custom UDA such as `check_status` rather than overloading Taskwarrior's own lifecycle state.

For each current relation-pair:

1. Query this isolated DB for an existing record with the same `pair_key`.
2. If no record exists, create it with `check_status=unchecked` and an empty report.
3. If a record exists, preserve its current `check_status` and report.
4. Only current-cycle records should drive workflow decisions; old records for old checksums remain as cache/history.

The supporting script should expose a progress report command, for example:

```bash
python ./bin/inconsistency-check/main.py progress --file @/path/to/file
```

The command should normalize the provided path to a root-anchored path and report records where either `changed_path` or `related_path` equals that path. It should summarize counts by `check_status` and list matching relation-pairs with their relation, opposite file, checksums, and current report status. This avoids requiring humans or agents to compose fragile Taskwarrior filters over two path fields.

### 5. Process One Unchecked Relation-Pair

After queue reconciliation, the script must not process all unchecked relation-pairs in one invocation. It should use the isolated Taskwarrior DB as a durable queue and process at most one unchecked relation-pair per `run-cycle` invocation.

Decision order:

1. If any current relation-pair is already `check_status=inconsistent`, print the first one in deterministic order and exit `10` without spawning a child Codex agent.
2. Otherwise, select the first current relation-pair with `check_status=unchecked`.
3. If no current relation-pair is `unchecked`, exit `0`.
4. For the selected unchecked relation-pair only, run one separate non-interactive Codex process, for example:

```bash
codex exec --cd <restricted-session-workdir> --sandbox read-only --ask-for-approval never --output-schema <schema> --output-last-message <output-file> -
```

The prompt should include:

- root-relative paths and checksums for both files;
- relation id that connected them;
- relation-specific consistency instructions derived from the relation id and description;
- full content of both files, or a declared binary-file handling mode;
- instruction to check only consistency between the supplied files;
- instruction to avoid loading more context unless explicitly required for this pair check;
- consistency criteria:
  - specs match implementation behavior and public contracts;
  - tests match implementation and documented behavior;
  - imports/callers match available APIs, names, types, and side effects;
  - README/changelog/docs match specs and code-visible behavior;
  - dictionary/index relations use the same terms and references;
  - no stale names, missing cases, contradictory defaults, or incompatible examples;
- required output:
  - `check_status`: `consistent` or `inconsistent`;
  - `report`: markdown;
  - when inconsistent, each inconsistency must be one `##` section;
  - when consistent, report may be empty or a short no-issues note.

Use an output JSON schema so the script can parse the result reliably. If a child agent returns malformed output, update the pair to `check_status=inconsistent` with a generated markdown section such as `## Checker output was malformed`.

Binary files need a deliberate handling rule. For images, Codex can receive image attachments if the CLI invocation supports it; for unsupported binaries, the script should produce an explicit failed or blocked report rather than pretending the content was checked.

### 6. Update Pair Status

After the child-agent check, update the existing isolated Taskwarrior record for that `pair_key` with:

- `pair_key`;
- `file_pair`;
- changed and related paths;
- checksums;
- relation id;
- `check_status=consistent` or `check_status=inconsistent`;
- markdown `report`;
- timestamp.

The workflow should only consider records whose `pair_key` is present in the current cycle. Old inconsistent records for old checksums remain in the DB as cache/history but must not block success after files change.

### 7. Select Next Workflow Outcome

After queue reconciliation and, if applicable, checking one unchecked relation-pair:

1. Iterate the current cycle's pair keys in deterministic order.
2. If the first current record with `check_status=inconsistent` exists, print a human-readable block containing:
   - pair key;
   - changed file;
   - related file;
   - relation;
   - report.
3. Exit `10` so Donna routes to `fix_first_inconsistency`.
4. If the processed relation-pair was marked `consistent` and unchecked current records remain, exit `20` so Donna loops back to `run_consistency_cycle`.
5. If no current inconsistent or unchecked records exist, exit `0`.

This makes the Taskwarrior DB the durable queue: first all current relation-pairs are represented as `unchecked`, then each script invocation validates only the first unchecked relation-pair and updates it to `consistent` or `inconsistent`. The workflow stops as soon as it finds an inconsistency, so it does not spend tokens checking pairs that may become stale after the primary agent fixes the first reported issue.

## Primary Agent Fix Request

The Donna `fix_first_inconsistency` action should instruct the primary agent to:

1. Read the two files from the reported pair.
2. Fix the inconsistency with the smallest coherent source change.
3. Use `depmesh` for supported dependency checks if the fix touches project artifacts.
4. Use existing Docker-backed project scripts or the `@/workflows/polish.donna.md` workflow for verification when the codebase is expected to be working.
5. Complete the action request by transitioning back to `run_consistency_cycle`.

The action should also mention a false-positive escape hatch. Without one, the workflow can loop forever when the checker marks a pair as inconsistent but the primary agent determines the report is invalid.

## Validation Plan

After implementation:

1. Validate the Donna workflow:

```bash
donna -p llm validate @/workflows/inconsistency-check.donna.md
```

2. Render it in view mode and check that the action request gives clear instructions:

```bash
donna -p llm render @/workflows/inconsistency-check.donna.md --mode view
```

3. Unit-test or dry-run the supporting script against a tiny controlled pair if possible.
4. Run the workflow on a branch with one known consistent pair and one known inconsistent pair.
5. Confirm that rerunning does not recheck same-checksum pairs already marked `consistent` or `inconsistent`.
6. Confirm that editing one file changes the pair key and forces a fresh check.
7. Confirm `.session/taskwarrior` journal records and `.session/inconsistency-check/taskwarrior` pair records remain separate.
8. Confirm `python ./bin/inconsistency-check/main.py progress --file <path>` reports records where the file appears as either `changed_path` or `related_path`.
9. Confirm one `run-cycle` invocation processes at most one unchecked relation-pair and spawns no child Codex agent when a current inconsistent relation-pair already exists.

## Risks and Open Decisions

- Decide whether pair keys are oriented or canonicalized. Canonicalization reduces duplicate checks; orientation preserves relation direction.
- Decide how deleted files and unsupported binary files should be represented.
- Batch checking can be considered later, but the initial workflow should process exactly one unchecked relation-pair per script invocation to avoid stale reports and unnecessary child-agent token use.
- Decide how to handle false positives: manual DB override, prompt update, or workflow error finish.
- Long markdown reports in Taskwarrior UDAs should be tested early. If Taskwarrior cannot reliably store multiline reports, the requirement may need a small adjustment or the script must use JSON import/export carefully.
