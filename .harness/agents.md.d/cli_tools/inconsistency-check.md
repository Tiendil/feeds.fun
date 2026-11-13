
### `inconsistency-check.py`

`./bin/inconsistency-check.py` — a direct helper script for managing the depmesh-backed consistency-check queue.

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

- `python ./bin/inconsistency-check.py enqueue @/path/to/file` — manually add one file and all configured depmesh relation pairs for that file to the isolated queue.
- `python ./bin/inconsistency-check.py enqueue @/first @/second` — enqueue multiple files.
- `python ./bin/inconsistency-check.py enqueue-changed` — enqueue all relation pairs for files changed relative to `main` without processing unchecked pairs or spawning child checkers.
- `python ./bin/inconsistency-check.py sync-queue` — reconcile the mode-eligible queue without processing pairs.
- `python ./bin/inconsistency-check.py list-pairs --current` — show only current-checksum records for relations still returned by `depmesh`.
- `python ./bin/inconsistency-check.py list-operations --last 20` — show the latest pair operations oldest-to-newest within the selected tail.
- `python ./bin/inconsistency-check.py progress --file @/path/to/file` — show queued records where the file is either the changed side or the related side.
- `python ./bin/inconsistency-check.py mark-consistent --changed @/changed --related @/related --relation <relation>` — explicitly mark the current-checksum relation pair as consistent.
- `python ./bin/inconsistency-check.py mark-unchecked --changed @/changed --related @/related --relation <relation>` — reset the current-checksum relation pair to unchecked, clear its previous reviewer result, and require checker reevaluation.
- `python ./bin/inconsistency-check.py mark-inconsistent --changed @/changed --related @/related --relation <relation> --report "<markdown>"` — explicitly mark the current-checksum relation pair as inconsistent.
- `python ./bin/inconsistency-check.py clear-queue` — delete all records from the isolated relation-pair queue without deleting pair-operation history.
- `python ./bin/inconsistency-check.py run-cycle` — reconcile the queue and process one mode-eligible dependency frontier.
- `python ./bin/inconsistency-check.py process-queue` — process one mode-eligible dependency frontier.
- `python ./bin/inconsistency-check.py self-check` — run deterministic script verification without spawning a child Codex checker.

The script stores its relation-pair queue and runtime files only under `@/.session/inconsistency-check/`.
Relation-pair state and structured pair-operation history are stored in
`@/.session/inconsistency-check/state.sqlite3`. The previously migrated `taskwarrior/` database and `operations.jsonl`
remain as recoverable artifacts; the script does not read, write, or delete them.
