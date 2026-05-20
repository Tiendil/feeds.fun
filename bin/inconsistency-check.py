#!/usr/bin/env python3
"""Depmesh-backed consistency checker for Donna workflows.

Pair identity is intentionally oriented from the changed artifact to the
depmesh-related artifact. Reverse relations are therefore distinct unless a
future workflow revision documents an explicit canonicalization policy.

Relation pairs with deleted or missing files are skipped. Unsupported binary
files still fail loudly rather than cache a pair as checked when exact current
working-tree text bytes are unavailable.

Project journal logging belongs in ``log_project_journal``. Relation-pair
queue records must use the isolated Taskwarrior database under
``.session/inconsistency-check``; project journal entries must use
``bin/taskwarior.sh`` through ``log_project_journal`` and carry the
``+consistency`` tag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess  # noqa: S404
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELATIVE_RUNTIME_DIR = Path(".session") / "inconsistency-check"
RUNTIME_DIR = PROJECT_ROOT / RELATIVE_RUNTIME_DIR
RELATIVE_TASKRC_PATH = RELATIVE_RUNTIME_DIR / "taskrc"
TASKRC_PATH = RUNTIME_DIR / "taskrc"
TASK_DATA_DIR = RUNTIME_DIR / "taskwarrior"
AGENT_OUTPUT_DIR = RUNTIME_DIR / "agent-output"
PROMPT_DIR = RUNTIME_DIR / "prompts"
SCHEMA_DIR = RUNTIME_DIR / "schemas"
SELF_CHECK_DIR = RUNTIME_DIR / "self-check"
TASKWARRIOR_BIN = "task"
PROJECT_JOURNAL_CMD = "./bin/taskwarior.sh"
PROJECT_JOURNAL_TAG = "consistency"
VALID_CHECK_STATUSES = {"unchecked", "consistent", "inconsistent"}
TASKRC_CONTENT = f"""data.location={RELATIVE_RUNTIME_DIR / "taskwarrior"}
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
"""


class ExitCode(IntEnum):
    SUCCESS = 0
    INCONSISTENCY_FOUND = 10
    CONTINUE_CYCLE = 20
    CHECKER_FAILURE = 1


@dataclass(frozen=True)
class DepmeshRelation:
    relation_id: str
    description: str


@dataclass(frozen=True)
class RelationPair:
    changed_path: str
    related_path: str
    relation: str
    relation_description: str


@dataclass(frozen=True)
class PairIdentity:
    pair_key: str
    file_pair: str
    changed_path: str
    related_path: str
    relation: str
    checksum_changed: str
    checksum_related: str


@dataclass(frozen=True)
class FileSnapshot:
    artifact_path: str
    root_path: str
    content: bytes
    text: str
    checksum: str


@dataclass(frozen=True)
class CheckRecord:
    uuid: str
    pair_key: str
    file_pair: str
    changed_path: str
    related_path: str
    relation: str
    checksum_changed: str
    checksum_related: str
    check_status: str
    report: str
    checked_at: str


@dataclass(frozen=True)
class CurrentPair:
    pair: RelationPair
    identity: PairIdentity
    record: CheckRecord


@dataclass(frozen=True)
class PairSelection:
    inconsistent: CurrentPair | None
    unchecked: CurrentPair | None


@dataclass(frozen=True)
class PreparedChildCheck:
    current_pair: CurrentPair
    prompt_path: Path
    schema_path: Path
    output_path: Path
    prompt: str


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CheckerFailureError(Exception):
    """Raised when checker tooling cannot produce a normal workflow result."""


class MissingArtifactError(CheckerFailureError):
    """Raised when an artifact path has no current file to compare."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"missing or deleted file: {path}")


def format_argv(argv: Iterable[str]) -> str:
    return shlex.join(str(part) for part in argv)


def build_command_failure(context: str, result: CommandResult) -> str:
    details = [
        context,
        f"command: {format_argv(result.argv)}",
        f"exit code: {result.returncode}",
    ]

    if result.stdout:
        details.append(f"stdout:\n{result.stdout}")

    if result.stderr:
        details.append(f"stderr:\n{result.stderr}")

    return "\n".join(details)


def run_command(
    argv: Iterable[str],
    *,
    input_text: str | None = None,
    check: bool = False,
    failure_context: str = "command failed",
) -> CommandResult:
    command = tuple(str(part) for part in argv)

    try:
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=PROJECT_ROOT,
            input=input_text,
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        raise CheckerFailureError(f"{failure_context}: {format_argv(command)}: {error}") from error

    result = CommandResult(
        argv=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )

    if check and result.returncode != 0:
        raise CheckerFailureError(build_command_failure(failure_context, result))

    return result


def parse_json_lines(output: str, *, context: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for line_number, line in enumerate(output.splitlines(), start=1):
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise CheckerFailureError(f"{context}: invalid JSON on line {line_number}: {error}") from error

        if not isinstance(record, dict):
            raise CheckerFailureError(f"{context}: JSON line {line_number} is not an object")

        records.append(record)

    return records


def run_automation_jsonl(argv: Iterable[str], *, failure_context: str) -> list[dict[str, Any]]:
    result = run_command(argv, check=True, failure_context=failure_context)

    try:
        return parse_json_lines(result.stdout, context=failure_context)
    except CheckerFailureError as error:
        diagnostic = build_command_failure(str(error), result)
        raise CheckerFailureError(diagnostic) from error


def root_relative_to_artifact(path: str) -> str:
    normalized = PurePosixPath(path)

    if normalized.is_absolute() or ".." in normalized.parts:
        raise CheckerFailureError(f"unsupported project-relative path from git: {path}")

    if str(normalized) == ".":
        raise CheckerFailureError("unsupported empty project-relative path from git")

    return f"@/{normalized.as_posix()}"


def normalize_input_path(path: str) -> str:
    if path.startswith("@/"):
        artifact_to_root_relative(path)
        return path

    input_path = Path(path)

    if input_path.is_absolute():
        try:
            relative_path = input_path.resolve(strict=False).relative_to(PROJECT_ROOT.resolve())
        except ValueError as error:
            raise CheckerFailureError(f"path is outside project root: {path}") from error

        return root_relative_to_artifact(relative_path.as_posix())

    return root_relative_to_artifact(input_path.as_posix())


def artifact_to_root_relative(path: str) -> PurePosixPath:
    if not path.startswith("@/"):
        raise CheckerFailureError(f"path is not a root-anchored artifact id: {path}")

    relative = PurePosixPath(path[2:])

    if relative.is_absolute() or ".." in relative.parts or str(relative) == ".":
        raise CheckerFailureError(f"unsupported artifact path: {path}")

    return relative


def artifact_to_filesystem_path(path: str) -> Path:
    return PROJECT_ROOT / Path(*artifact_to_root_relative(path).parts)


def artifact_to_root_path(path: str) -> str:
    return artifact_to_root_relative(path).as_posix()


def checksum_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def text_from_bytes(path: str, content: bytes) -> str:
    if b"\0" in content:
        raise CheckerFailureError(f"unsupported binary file content in {path}")

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CheckerFailureError(f"unsupported non-UTF-8 file content in {path}: {error}") from error


def read_artifact_snapshot(path: str) -> FileSnapshot:
    filesystem_path = artifact_to_filesystem_path(path)

    if not filesystem_path.exists():
        raise MissingArtifactError(path)

    if not filesystem_path.is_file():
        raise CheckerFailureError(f"unsupported non-file artifact: {path}")

    content = filesystem_path.read_bytes()

    return FileSnapshot(
        artifact_path=path,
        root_path=artifact_to_root_path(path),
        content=content,
        text=text_from_bytes(path, content),
        checksum=checksum_bytes(content),
    )


def read_pair_snapshots(pair: RelationPair) -> tuple[FileSnapshot, FileSnapshot]:
    return read_artifact_snapshot(pair.changed_path), read_artifact_snapshot(pair.related_path)


def build_file_pair(changed: FileSnapshot, related: FileSnapshot) -> str:
    return f"<{changed.root_path}, sha256:{changed.checksum}>-<{related.root_path}, sha256:{related.checksum}>"


def build_pair_identity(pair: RelationPair) -> PairIdentity:
    changed, related = read_pair_snapshots(pair)
    file_pair = build_file_pair(changed, related)

    return PairIdentity(
        pair_key=f"{pair.relation}|{file_pair}",
        file_pair=file_pair,
        changed_path=pair.changed_path,
        related_path=pair.related_path,
        relation=pair.relation,
        checksum_changed=changed.checksum,
        checksum_related=related.checksum,
    )


def resolve_comparison_base() -> str:
    for ref in ("main", "origin/main"):
        result = run_command(
            ["git", "rev-parse", "--verify", ref],
            failure_context=f"resolving comparison base {ref}",
        )

        if result.returncode == 0:
            return ref

    raise CheckerFailureError("could not resolve comparison base: neither main nor origin/main exists")


def merge_base_with_head(base_ref: str) -> str:
    result = run_command(
        ["git", "merge-base", base_ref, "HEAD"],
        check=True,
        failure_context=f"computing merge base for {base_ref} and HEAD",
    )
    merge_base = result.stdout.strip()

    if not merge_base:
        raise CheckerFailureError(f"git merge-base produced no commit for {base_ref} and HEAD")

    return merge_base


def parse_changed_file_line(line: str) -> str:
    parts = line.split("\t")

    if len(parts) < 2:
        raise CheckerFailureError(f"unexpected git diff --name-status line: {line}")

    status = parts[0]
    status_code = status[:1]

    if status_code == "D":
        raise CheckerFailureError(f"deleted files are unsupported by the consistency checker: {line}")

    if status_code in {"R", "C"}:
        if len(parts) != 3:
            raise CheckerFailureError(f"unexpected rename/copy git diff line: {line}")

        return parts[2]

    if status_code in {"A", "M"}:
        if len(parts) != 2:
            raise CheckerFailureError(f"unexpected changed-file git diff line: {line}")

        return parts[1]

    raise CheckerFailureError(f"unsupported git diff status {status!r}: {line}")


def discover_changed_files() -> list[str]:
    base_ref = resolve_comparison_base()
    merge_base = merge_base_with_head(base_ref)
    result = run_command(
        ["git", "diff", "--name-status", "--diff-filter=ACMR", merge_base, "--"],
        check=True,
        failure_context=f"discovering changed files relative to {merge_base}",
    )
    changed_files = [
        root_relative_to_artifact(parse_changed_file_line(line)) for line in result.stdout.splitlines() if line
    ]
    unique_changed_files = sorted(dict.fromkeys(changed_files))
    log_project_journal("step", f"changed-file discovery found {len(unique_changed_files)} files")

    return unique_changed_files


def load_depmesh_relations() -> list[DepmeshRelation]:
    records = run_automation_jsonl(
        ["depmesh", "-p", "automation", "relations"],
        failure_context="loading depmesh relations",
    )
    relations: list[DepmeshRelation] = []

    for record in records:
        if record.get("type") != "relation":
            raise CheckerFailureError(f"unexpected depmesh relations record: {record}")

        relation_id = record.get("id")
        description = record.get("description")

        if not isinstance(relation_id, str) or not isinstance(description, str):
            raise CheckerFailureError(f"invalid depmesh relation record: {record}")

        relations.append(DepmeshRelation(relation_id=relation_id, description=description))

    sorted_relations = sorted(relations, key=lambda relation: relation.relation_id)
    log_project_journal("step", f"depmesh relation discovery found {len(sorted_relations)} relations")

    return sorted_relations


def parse_depmesh_dependencies(
    records: list[dict[str, Any]],
    *,
    changed_path: str,
    relation: DepmeshRelation,
) -> list[RelationPair]:
    pairs: list[RelationPair] = []

    for record in records:
        record_type = record.get("type")

        if record_type == "warning":
            log_project_journal("thought", f"depmesh warning for {changed_path} {relation.relation_id}: {record}")
            continue

        if record_type != "dependency":
            raise CheckerFailureError(f"unexpected depmesh dependency record: {record}")

        dependency = record.get("dependency")
        record_relation = record.get("relation")

        if record_relation != relation.relation_id:
            raise CheckerFailureError(f"depmesh returned relation {record_relation!r} for {relation.relation_id!r}")

        if not isinstance(dependency, str) or not dependency.startswith("@/"):
            raise CheckerFailureError(f"invalid depmesh dependency record: {record}")

        pairs.append(
            RelationPair(
                changed_path=changed_path,
                related_path=dependency,
                relation=relation.relation_id,
                relation_description=relation.description,
            )
        )

    return pairs


def query_depmesh_pairs(changed_files: list[str]) -> list[RelationPair]:
    relations = load_depmesh_relations()
    pair_map: dict[tuple[str, str, str], RelationPair] = {}

    for changed_path in sorted(changed_files):
        for relation in relations:
            records = run_automation_jsonl(
                ["depmesh", "-p", "automation", "dependencies", "--relation", relation.relation_id, changed_path],
                failure_context=f"querying depmesh relation {relation.relation_id} for {changed_path}",
            )
            pairs = parse_depmesh_dependencies(records, changed_path=changed_path, relation=relation)
            log_project_journal(
                "step",
                f"depmesh query for {changed_path} relation {relation.relation_id} returned {len(pairs)} pairs",
            )

            for pair in pairs:
                pair_map[(pair.changed_path, pair.relation, pair.related_path)] = pair

    return [pair_map[key] for key in sorted(pair_map)]


def single_line(value: str) -> str:
    return " ".join(value.split())


def log_project_journal(kind: str, message: str) -> None:
    """Log project-level script events without touching relation-pair records."""

    clean_kind = single_line(kind)

    if not clean_kind or clean_kind != kind:
        raise CheckerFailureError(f"invalid journal kind: {kind!r}")

    result = run_command(
        [
            PROJECT_JOURNAL_CMD,
            "log",
            "+journal",
            f"+{PROJECT_JOURNAL_TAG}",
            f"kind:{clean_kind}",
            single_line(message),
        ],
        failure_context="project journal logging failed",
    )

    if result.returncode != 0:
        raise CheckerFailureError(build_command_failure("project journal logging failed", result))


def pair_journal_subject(identity: PairIdentity) -> str:
    return (
        f"{identity.changed_path} -> {identity.related_path} "
        f"[{identity.relation}] pair_key:{identity.pair_key}"
    )


def log_pair_queued(identity: PairIdentity, check_status: str) -> None:
    log_project_journal(
        "change",
        f"inconsistency-check queued pair {pair_journal_subject(identity)} status:{check_status}",
    )


def log_pair_state_change(identity: PairIdentity, previous_status: str, next_status: str) -> None:
    if previous_status == next_status:
        return

    log_project_journal(
        "change",
        (
            "inconsistency-check pair state changed "
            f"{pair_journal_subject(identity)} {previous_status}->{next_status}"
        ),
    )


def ensure_runtime_state() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    TASK_DATA_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    SELF_CHECK_DIR.mkdir(parents=True, exist_ok=True)
    TASKRC_PATH.write_text(TASKRC_CONTENT, encoding="utf-8")


def task_command_args(*args: str) -> list[str]:
    return [
        TASKWARRIOR_BIN,
        f"rc:{RELATIVE_TASKRC_PATH.as_posix()}",
        "rc.confirmation:no",
        "rc.verbose:nothing",
        *args,
    ]


def load_taskwarrior_records() -> list[dict[str, Any]]:
    ensure_runtime_state()
    result = run_command(
        task_command_args("export"),
        check=True,
        failure_context="exporting isolated inconsistency-check Taskwarrior records",
    )

    try:
        records = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as error:
        raise CheckerFailureError(f"invalid Taskwarrior export JSON: {error}") from error

    if not isinstance(records, list):
        raise CheckerFailureError("Taskwarrior export did not return a JSON list")

    for record in records:
        if not isinstance(record, dict):
            raise CheckerFailureError(f"Taskwarrior export contained a non-object record: {record}")

    return records


def raw_record_to_check_record(record: dict[str, Any]) -> CheckRecord:
    return CheckRecord(
        uuid=str(record.get("uuid") or ""),
        pair_key=str(record.get("pair_key") or ""),
        file_pair=str(record.get("file_pair") or ""),
        changed_path=str(record.get("changed_path") or ""),
        related_path=str(record.get("related_path") or ""),
        relation=str(record.get("relation") or ""),
        checksum_changed=str(record.get("checksum_changed") or ""),
        checksum_related=str(record.get("checksum_related") or ""),
        check_status=str(record.get("check_status") or ""),
        report=str(record.get("report") or ""),
        checked_at=str(record.get("checked_at") or ""),
    )


def find_raw_record_by_pair_key(records: list[dict[str, Any]], pair_key: str) -> dict[str, Any] | None:
    matches = [record for record in records if record.get("pair_key") == pair_key]

    if len(matches) > 1:
        raise CheckerFailureError(f"isolated Taskwarrior DB has duplicate pair_key records: {pair_key}")

    return matches[0] if matches else None


def identity_task_args(identity: PairIdentity) -> list[str]:
    return [
        f"description:{identity.changed_path} -> {identity.related_path} [{identity.relation}]",
        f"pair_key:{identity.pair_key}",
        f"file_pair:{identity.file_pair}",
        f"changed_path:{identity.changed_path}",
        f"related_path:{identity.related_path}",
        f"relation:{identity.relation}",
        f"checksum_changed:{identity.checksum_changed}",
        f"checksum_related:{identity.checksum_related}",
    ]


def write_task_record(
    identity: PairIdentity,
    *,
    uuid: str | None,
    check_status: str,
    report: str,
    checked_at: str,
) -> CheckRecord:
    status_args = [
        f"check_status:{check_status}",
        f"report:{report}",
        f"checked_at:{checked_at}",
    ]

    if uuid:
        args = [uuid, "modify", *identity_task_args(identity), *status_args]
    else:
        args = ["add", *identity_task_args(identity), *status_args]

    run_command(
        task_command_args(*args),
        check=True,
        failure_context="writing isolated inconsistency-check Taskwarrior record",
    )

    raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), identity.pair_key)

    if raw_record is None:
        raise CheckerFailureError(f"Taskwarrior record was not found after write: {identity.pair_key}")

    return raw_record_to_check_record(raw_record)


def upsert_unchecked_record(identity: PairIdentity) -> CheckRecord:
    raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), identity.pair_key)

    if raw_record is None:
        record = write_task_record(identity, uuid=None, check_status="unchecked", report="", checked_at="")
        log_pair_queued(identity, record.check_status or "unchecked")

        return record

    existing = raw_record_to_check_record(raw_record)
    existing_status = existing.check_status or "unchecked"

    return write_task_record(
        identity,
        uuid=existing.uuid,
        check_status=existing_status,
        report=existing.report,
        checked_at=existing.checked_at,
    )


def update_check_record(identity: PairIdentity, *, check_status: str, report: str, checked_at: str) -> CheckRecord:
    raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), identity.pair_key)

    if raw_record is None:
        raise CheckerFailureError(f"cannot update missing pair record: {identity.pair_key}")

    existing = raw_record_to_check_record(raw_record)
    previous_status = existing.check_status or "unchecked"
    record = write_task_record(
        identity,
        uuid=existing.uuid,
        check_status=check_status,
        report=report,
        checked_at=checked_at,
    )
    log_pair_state_change(identity, previous_status, check_status)

    return record


def reconcile_queue(pairs: list[RelationPair]) -> list[CurrentPair]:
    current_pairs: list[CurrentPair] = []
    skipped_missing = 0

    for pair in sorted(pairs, key=lambda item: (item.changed_path, item.relation, item.related_path)):
        try:
            identity = build_pair_identity(pair)
        except MissingArtifactError as error:
            skipped_missing += 1
            log_project_journal(
                "step",
                (
                    "skipped missing-file pair "
                    f"{pair.changed_path} -> {pair.related_path} [{pair.relation}]: {error.path}"
                ),
            )
            continue

        record = upsert_unchecked_record(identity)
        current_pairs.append(CurrentPair(pair=pair, identity=identity, record=record))

    if skipped_missing:
        log_project_journal("step", f"queue reconciliation skipped {skipped_missing} missing-file pair records")

    log_project_journal("step", f"queue reconciliation produced {len(current_pairs)} current pair records")

    return current_pairs


def current_pair_sort_key(current_pair: CurrentPair) -> tuple[str, str, str]:
    return (
        current_pair.identity.changed_path,
        current_pair.identity.relation,
        current_pair.identity.related_path,
    )


def normalized_check_status(record: CheckRecord) -> str:
    status = record.check_status or "unchecked"

    if status not in VALID_CHECK_STATUSES:
        raise CheckerFailureError(f"unsupported check_status {status!r} for pair {record.pair_key}")

    return status


def select_current_pair(current_pairs: list[CurrentPair]) -> PairSelection:
    ordered_pairs = sorted(current_pairs, key=current_pair_sort_key)

    for current_pair in ordered_pairs:
        if normalized_check_status(current_pair.record) == "inconsistent":
            log_project_journal("step", f"existing current inconsistency found: {current_pair.identity.pair_key}")
            return PairSelection(inconsistent=current_pair, unchecked=None)

    for current_pair in ordered_pairs:
        if normalized_check_status(current_pair.record) == "unchecked":
            log_project_journal("step", f"selected unchecked pair: {current_pair.identity.pair_key}")
            return PairSelection(inconsistent=None, unchecked=current_pair)

    log_project_journal("step", "no current unchecked or inconsistent pairs remain")

    return PairSelection(inconsistent=None, unchecked=None)


def print_inconsistent_pair(current_pair: CurrentPair) -> None:
    record = current_pair.record
    print("Current inconsistent relation pair")
    print(f"pair key: {record.pair_key}")
    print(f"changed file: {record.changed_path}")
    print(f"related file: {record.related_path}")
    print(f"relation: {record.relation}")
    print("report:")
    print(record.report or "(empty report)")


def status_counts(current_pairs: list[CurrentPair]) -> Counter[str]:
    return Counter(normalized_check_status(current_pair.record) for current_pair in current_pairs)


def print_summary(changed_files: list[str], current_pairs: list[CurrentPair]) -> None:
    counts = status_counts(current_pairs)
    print("Consistency check summary")
    print(f"changed files: {len(changed_files)}")
    print(f"relation pairs: {len(current_pairs)}")
    print(f"consistent pairs: {counts.get('consistent', 0)}")
    print(f"inconsistent pairs: {counts.get('inconsistent', 0)}")
    print(f"unchecked pairs: {counts.get('unchecked', 0)}")

    if changed_files:
        print("changed file list:")

        for changed_file in changed_files:
            print(f"- {changed_file}")


def replace_current_pair(current_pairs: list[CurrentPair], updated_pair: CurrentPair) -> list[CurrentPair]:
    return [
        updated_pair if current_pair.identity.pair_key == updated_pair.identity.pair_key else current_pair
        for current_pair in current_pairs
    ]


def remove_current_pair(current_pairs: list[CurrentPair], removed_pair: CurrentPair) -> list[CurrentPair]:
    return [
        current_pair
        for current_pair in current_pairs
        if current_pair.identity.pair_key != removed_pair.identity.pair_key
    ]


def first_inconsistent_pair(current_pairs: list[CurrentPair]) -> CurrentPair | None:
    for current_pair in sorted(current_pairs, key=current_pair_sort_key):
        if normalized_check_status(current_pair.record) == "inconsistent":
            return current_pair

    return None


def has_unchecked_pair(current_pairs: list[CurrentPair]) -> bool:
    return any(normalized_check_status(current_pair.record) == "unchecked" for current_pair in current_pairs)


OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["check_status", "report"],
    "properties": {
        "check_status": {"type": "string", "enum": ["consistent", "inconsistent"]},
        "report": {"type": "string"},
    },
}


def relation_specific_criteria(relation_id: str) -> list[str]:
    common = [
        "No stale names, missing cases, contradictory defaults, or incompatible examples.",
        "Compare only the two supplied files unless their own text proves extra context is necessary.",
    ]
    relation_checks = {
        "governed_by": [
            "The implementation or artifact must follow the governing specification's behavior and public contract.",
        ],
        "governs": [
            "The specification must accurately describe the governed artifact's visible behavior and public contract.",
        ],
        "tested_by": [
            "The test must assert behavior that the implementation actually provides.",
            "The implementation must satisfy the documented intent of the test.",
        ],
        "tests": [
            "The tested artifact must match the expectations and edge cases encoded in the test.",
        ],
        "imports": [
            "Imported APIs, names, types, side effects, and call signatures must still be available and compatible.",
        ],
        "imported_by": [
            "Caller code must use available APIs, names, types, side effects, and call signatures correctly.",
        ],
        "terms_defined_by": [
            "Dictionary terms used by the artifact must match the dictionary's spelling and meaning.",
        ],
        "defines_terms_for": [
            "Artifacts using dictionary terms must match the dictionary's spelling and meaning.",
        ],
        "indexed_by": [
            "Index references must include the artifact correctly and without stale names.",
        ],
        "indexes": [
            "Indexed artifacts must exist conceptually in the index and match its references.",
        ],
    }

    return [*relation_checks.get(relation_id, []), *common]


def fenced_content(label: str, content: str) -> str:
    fence = "```"

    while fence in content:
        fence += "`"

    return f"{label}\n{fence}\n{content}\n{fence}"


def identity_hash(identity: PairIdentity) -> str:
    return hashlib.sha256(identity.pair_key.encode("utf-8")).hexdigest()


def validate_prompt_snapshots(current_pair: CurrentPair) -> tuple[FileSnapshot, FileSnapshot]:
    changed, related = read_pair_snapshots(current_pair.pair)

    if changed.checksum != current_pair.identity.checksum_changed:
        raise CheckerFailureError(f"changed file checksum drifted before child check: {changed.artifact_path}")

    if related.checksum != current_pair.identity.checksum_related:
        raise CheckerFailureError(f"related file checksum drifted before child check: {related.artifact_path}")

    return changed, related


def build_child_prompt(current_pair: CurrentPair) -> str:
    changed, related = validate_prompt_snapshots(current_pair)
    criteria = "\n".join(f"- {criterion}" for criterion in relation_specific_criteria(current_pair.pair.relation))

    return "\n\n".join(
        [
            "You are checking consistency between exactly two project files.",
            "Do not edit files. Do not report issues outside this pair.",
            (
                f"Relation: {current_pair.pair.relation}\n"
                f"Relation description: {current_pair.pair.relation_description}"
            ),
            (
                f"Changed file: {changed.root_path}\n"
                f"Changed checksum: sha256:{changed.checksum}\n"
                f"Related file: {related.root_path}\n"
                f"Related checksum: sha256:{related.checksum}"
            ),
            "Consistency criteria:\n" + criteria,
            (
                "The parent checker skips missing or deleted pair files, and rejects binary and "
                "non-UTF-8 files before this prompt is built. "
                "Treat the file contents below as the exact current text bytes decoded as UTF-8."
            ),
            fenced_content(f"Changed file content ({changed.root_path})", changed.text),
            fenced_content(f"Related file content ({related.root_path})", related.text),
            (
                "Return JSON only. Use check_status=\"consistent\" when no pair inconsistency exists. "
                "Use check_status=\"inconsistent\" when the two files disagree. "
                "When inconsistent, report each separate issue as one markdown section beginning with '## '. "
                "When consistent, report may be empty or a short no-issues note."
            ),
        ]
    )


def prepare_child_check(current_pair: CurrentPair) -> PreparedChildCheck:
    ensure_runtime_state()
    key_hash = identity_hash(current_pair.identity)
    prompt_path = PROMPT_DIR / f"{key_hash}.md"
    schema_path = SCHEMA_DIR / f"{key_hash}.schema.json"
    output_path = AGENT_OUTPUT_DIR / f"{key_hash}.json"
    prompt = build_child_prompt(current_pair)
    prompt_path.write_text(prompt, encoding="utf-8")
    schema_path.write_text(json.dumps(OUTPUT_SCHEMA, indent=2, sort_keys=True), encoding="utf-8")

    return PreparedChildCheck(
        current_pair=current_pair,
        prompt_path=prompt_path,
        schema_path=schema_path,
        output_path=output_path,
        prompt=prompt,
    )


def run_child_checker(prepared: PreparedChildCheck) -> str:
    log_project_journal("step", f"child checker start for {prepared.current_pair.identity.pair_key}")
    result = run_command(
        [
            "codex",
            "exec",
            "--cd",
            str(PROJECT_ROOT),
            "--sandbox",
            "read-only",
            "-c",
            'approval_policy="never"',
            "--ephemeral",
            "--output-schema",
            str(prepared.schema_path),
            "--output-last-message",
            str(prepared.output_path),
            "-",
        ],
        input_text=prepared.prompt,
        failure_context=f"running child Codex checker for {prepared.current_pair.identity.pair_key}",
    )

    if result.returncode != 0:
        raise CheckerFailureError(build_command_failure("child Codex checker failed", result))

    if not prepared.output_path.exists():
        raise CheckerFailureError(f"child Codex checker did not write output file: {prepared.output_path}")

    output = prepared.output_path.read_text(encoding="utf-8")
    log_project_journal("step", f"child checker completed for {prepared.current_pair.identity.pair_key}")

    return output


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def malformed_child_report(reason: str, output: str) -> str:
    return "\n\n".join(
        [
            "## Checker output was malformed",
            f"Reason: {reason}",
            fenced_content("Raw child checker output", output),
        ]
    )


def validate_child_result(output: str) -> tuple[str, str]:
    try:
        result = json.loads(output)
    except json.JSONDecodeError as error:
        return "inconsistent", malformed_child_report(str(error), output)

    if not isinstance(result, dict):
        return "inconsistent", malformed_child_report("output JSON is not an object", output)

    extra_keys = sorted(set(result) - {"check_status", "report"})

    if extra_keys:
        return "inconsistent", malformed_child_report(f"unexpected keys: {', '.join(extra_keys)}", output)

    check_status = result.get("check_status")
    report = result.get("report")

    if check_status not in {"consistent", "inconsistent"}:
        return "inconsistent", malformed_child_report("check_status must be consistent or inconsistent", output)

    if not isinstance(report, str):
        return "inconsistent", malformed_child_report("report must be a string", output)

    if check_status == "inconsistent" and not any(line.startswith("## ") for line in report.splitlines()):
        return "inconsistent", malformed_child_report(
            "inconsistent reports must contain at least one ## section",
            output,
        )

    return check_status, report


def update_record_from_child_output(current_pair: CurrentPair, output: str) -> CurrentPair:
    check_status, report = validate_child_result(output)
    record = update_check_record(
        current_pair.identity,
        check_status=check_status,
        report=report,
        checked_at=utc_timestamp(),
    )
    log_project_journal("step", f"pair status update for {current_pair.identity.pair_key}: {check_status}")

    return CurrentPair(pair=current_pair.pair, identity=current_pair.identity, record=record)


def run_cycle() -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "run-cycle command started")
    changed_files = discover_changed_files()
    relation_pairs = query_depmesh_pairs(changed_files)
    current_pairs = reconcile_queue(relation_pairs)

    while True:
        selection = select_current_pair(current_pairs)

        if selection.inconsistent is not None:
            print_inconsistent_pair(selection.inconsistent)
            log_project_journal("step", "run-cycle outcome: current inconsistency found")
            return ExitCode.INCONSISTENCY_FOUND

        if selection.unchecked is None:
            print_summary(changed_files, current_pairs)
            log_project_journal("step", "run-cycle outcome: success")
            return ExitCode.SUCCESS

        try:
            prepared = prepare_child_check(selection.unchecked)
        except MissingArtifactError as error:
            log_project_journal(
                "step",
                (
                    "skipped selected missing-file pair "
                    f"{selection.unchecked.identity.changed_path} -> "
                    f"{selection.unchecked.identity.related_path} "
                    f"[{selection.unchecked.identity.relation}]: {error.path}"
                ),
            )
            current_pairs = remove_current_pair(current_pairs, selection.unchecked)
            continue

        break

    child_output = run_child_checker(prepared)
    updated_pair = update_record_from_child_output(selection.unchecked, child_output)
    current_pairs = replace_current_pair(current_pairs, updated_pair)

    inconsistent_pair = first_inconsistent_pair(current_pairs)

    if inconsistent_pair is not None:
        print_inconsistent_pair(inconsistent_pair)
        log_project_journal("step", "run-cycle outcome: child found inconsistency")
        return ExitCode.INCONSISTENCY_FOUND

    if normalized_check_status(updated_pair.record) == "consistent" and has_unchecked_pair(current_pairs):
        print_summary(changed_files, current_pairs)
        log_project_journal("step", "run-cycle outcome: continue cycle")
        return ExitCode.CONTINUE_CYCLE

    print_summary(changed_files, current_pairs)
    log_project_journal("step", "run-cycle outcome: success")
    return ExitCode.SUCCESS


def build_progress_report(path: str) -> str:
    artifact_path = normalize_input_path(path)
    records = [
        raw_record_to_check_record(record)
        for record in load_taskwarrior_records()
        if record.get("changed_path") == artifact_path or record.get("related_path") == artifact_path
    ]
    records.sort(key=lambda record: (record.changed_path, record.relation, record.related_path, record.pair_key))
    counts = Counter(record.check_status or "unknown" for record in records)
    lines = [
        f"Progress for {artifact_path}",
        f"matching records: {len(records)}",
    ]

    if counts:
        lines.append("status counts:")

        for status, count in sorted(counts.items()):
            lines.append(f"- {status}: {count}")

    if not records:
        return "\n".join(lines)

    lines.append("records:")

    for record in records:
        opposite_path = record.related_path if record.changed_path == artifact_path else record.changed_path
        report_status = "present" if record.report else "empty"
        lines.extend(
            [
                f"- relation: {record.relation}",
                f"  opposite file: {opposite_path}",
                f"  changed checksum: {record.checksum_changed}",
                f"  related checksum: {record.checksum_related}",
                f"  status: {record.check_status or 'unknown'}",
                f"  report: {report_status}",
                f"  pair key: {record.pair_key}",
            ]
        )

    return "\n".join(lines)


def report_progress(path: str) -> ExitCode:
    ensure_runtime_state()
    artifact_path = normalize_input_path(path)
    log_project_journal("step", f"progress report requested for {artifact_path}")
    print(build_progress_report(artifact_path))

    return ExitCode.SUCCESS


def print_enqueue_summary(artifact_path: str, current_pairs: list[CurrentPair]) -> None:
    counts = status_counts(current_pairs)
    print(f"Enqueued relation pairs for {artifact_path}")
    print(f"relation pairs: {len(current_pairs)}")
    print(f"consistent pairs: {counts.get('consistent', 0)}")
    print(f"inconsistent pairs: {counts.get('inconsistent', 0)}")
    print(f"unchecked pairs: {counts.get('unchecked', 0)}")

    if not current_pairs:
        return

    print("pairs:")

    for current_pair in sorted(current_pairs, key=current_pair_sort_key):
        print(f"- relation: {current_pair.identity.relation}")
        print(f"  related file: {current_pair.identity.related_path}")
        print(f"  status: {normalized_check_status(current_pair.record)}")
        print(f"  pair key: {current_pair.identity.pair_key}")


def enqueue_file(path: str) -> ExitCode:
    ensure_runtime_state()
    artifact_path = normalize_input_path(path)
    log_project_journal("step", f"manual enqueue requested for {artifact_path}")
    relation_pairs = query_depmesh_pairs([artifact_path])
    current_pairs = reconcile_queue(relation_pairs)
    log_project_journal("step", f"manual enqueue for {artifact_path} produced {len(current_pairs)} pair records")
    print_enqueue_summary(artifact_path, current_pairs)

    return ExitCode.SUCCESS


def enqueue_files(paths: list[str]) -> ExitCode:
    for path in paths:
        enqueue_file(path)

    return ExitCode.SUCCESS


def assert_self_check(condition: bool, message: str) -> None:
    if not condition:
        raise CheckerFailureError(f"self-check failed: {message}")


def reset_self_check_record(identity: PairIdentity) -> None:
    raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), identity.pair_key)

    if raw_record is None:
        return

    existing = raw_record_to_check_record(raw_record)
    previous_status = existing.check_status or "unchecked"
    write_task_record(identity, uuid=existing.uuid, check_status="unchecked", report="", checked_at="")
    log_pair_state_change(identity, previous_status, "unchecked")


def run_self_check() -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "self-check command started")
    changed_files = discover_changed_files()
    assert_self_check(all(path.startswith("@/") for path in changed_files), "changed files must be artifact ids")

    changed_path = "@/.session/inconsistency-check/self-check/changed.txt"
    related_path = "@/.session/inconsistency-check/self-check/related.txt"
    second_related_path = "@/.session/inconsistency-check/self-check/second-related.txt"
    changed_file = SELF_CHECK_DIR / "changed.txt"
    related_file = SELF_CHECK_DIR / "related.txt"
    second_related_file = SELF_CHECK_DIR / "second-related.txt"
    changed_file.write_text("changed self-check content\n", encoding="utf-8")
    related_file.write_text("related self-check content\n", encoding="utf-8")
    second_related_file.write_text("second related self-check content\n", encoding="utf-8")
    pair = RelationPair(
        changed_path=changed_path,
        related_path=related_path,
        relation="self_check",
        relation_description="Self-check relation",
    )
    second_pair = RelationPair(
        changed_path=changed_path,
        related_path=second_related_path,
        relation="self_check",
        relation_description="Self-check relation",
    )
    missing_pair = RelationPair(
        changed_path=changed_path,
        related_path="@/.session/inconsistency-check/self-check/missing.txt",
        relation="self_check",
        relation_description="Self-check relation",
    )
    identity = build_pair_identity(pair)
    second_identity = build_pair_identity(second_pair)
    assert_self_check(identity.pair_key == f"self_check|{identity.file_pair}", "pair key must include relation")
    assert_self_check(identity.file_pair.startswith("<.session/"), "file_pair must use root-relative paths")
    reset_self_check_record(identity)
    reset_self_check_record(second_identity)
    current_pairs = reconcile_queue([pair, second_pair])
    assert_self_check(len(current_pairs) == 2, "queue reconciliation must return current pairs")
    assert_self_check(
        all(current_pair.record.check_status == "unchecked" for current_pair in current_pairs),
        "new current pairs must be unchecked",
    )
    missing_pairs = reconcile_queue([missing_pair])
    assert_self_check(not missing_pairs, "missing-file pairs must be skipped")
    selection = select_current_pair(current_pairs)
    assert_self_check(selection.unchecked is not None, "one unchecked pair must be selected")
    assert_self_check(selection.inconsistent is None, "unchecked selection must not report inconsistency")
    consistent_pair = update_record_from_child_output(
        selection.unchecked,
        json.dumps({"check_status": "consistent", "report": ""}),
    )
    current_pairs = replace_current_pair(current_pairs, consistent_pair)
    assert_self_check(
        has_unchecked_pair(current_pairs),
        "one processed pair must leave later unchecked pairs for exit 20",
    )
    preserved_pairs = reconcile_queue([pair, second_pair])
    preserved_record = next(
        item.record for item in preserved_pairs if item.identity.pair_key == consistent_pair.identity.pair_key
    )
    assert_self_check(preserved_record.check_status == "consistent", "unchanged pair key must preserve cached status")
    inconsistent_pair = update_record_from_child_output(
        consistent_pair,
        json.dumps({"check_status": "inconsistent", "report": "## Self-check inconsistency\n\nSynthetic issue."}),
    )
    current_pairs = replace_current_pair(preserved_pairs, inconsistent_pair)
    inconsistent_selection = select_current_pair(current_pairs)
    assert_self_check(
        inconsistent_selection.inconsistent is not None,
        "current inconsistency must be selected before any child check",
    )
    malformed_pair = update_record_from_child_output(current_pairs[1], "{not json")
    assert_self_check(malformed_pair.record.check_status == "inconsistent", "malformed output must be inconsistent")
    assert_self_check(
        "## Checker output was malformed" in malformed_pair.record.report,
        "malformed output must produce a markdown issue section",
    )
    changed_file.write_text("changed self-check content v2\n", encoding="utf-8")
    changed_identity = build_pair_identity(pair)
    assert_self_check(changed_identity.pair_key != identity.pair_key, "editing one file must change the pair key")
    reset_self_check_record(changed_identity)
    changed_current_pair = reconcile_queue([pair])[0]
    assert_self_check(changed_current_pair.record.check_status == "unchecked", "changed checksum must force unchecked")
    changed_report = build_progress_report(changed_path)
    related_report = build_progress_report(related_path)
    assert_self_check(changed_identity.pair_key in changed_report, "progress must match changed_path side")
    assert_self_check(changed_identity.pair_key in related_report, "progress must match related_path side")
    pair_records = load_taskwarrior_records()
    project_journal = json.loads(
        run_command(
            [PROJECT_JOURNAL_CMD, "rc.verbose:nothing", "+journal", "export"],
            check=True,
            failure_context="exporting project journal during self-check",
        ).stdout
    )
    assert_self_check(
        any(record.get("pair_key") == changed_identity.pair_key for record in pair_records),
        "pair record must exist in isolated Taskwarrior DB",
    )
    assert_self_check(
        not any(record.get("pair_key") == changed_identity.pair_key for record in project_journal),
        "pair record must not be written to project journal DB",
    )
    assert_self_check(
        any(record.get("description") == "self-check command started" for record in project_journal),
        "script operations must log to the project journal",
    )
    assert_self_check(
        all("journal" not in record.get("tags", []) for record in pair_records if record.get("pair_key")),
        "relation-pair records must not use project journal tags",
    )
    log_project_journal("step", "self-check command completed")
    print("Self-check passed")

    return ExitCode.SUCCESS


def parse_enqueue_files(args: argparse.Namespace) -> list[str]:
    paths = [str(path) for path in getattr(args, "files", [])]
    paths.extend(str(path) for path in getattr(args, "file_options", []) or [])

    if not paths:
        raise CheckerFailureError("enqueue requires at least one file path")

    return sorted(dict.fromkeys(paths))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run depmesh-backed consistency checks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run-cycle", help="reconcile and check at most one relation pair")

    enqueue_parser = subparsers.add_parser("enqueue", help="manually enqueue one file's depmesh relation pairs")
    enqueue_parser.add_argument("files", nargs="*", help="project paths or root-anchored artifact ids")
    enqueue_parser.add_argument(
        "--file",
        action="append",
        dest="file_options",
        help="project path or root-anchored artifact id; may be repeated",
    )

    progress_parser = subparsers.add_parser("progress", help="show cached relation-pair progress")
    progress_parser.add_argument("--file", required=True, help="project path or root-anchored artifact id")

    subparsers.add_parser("self-check", help="run deterministic helper-script checks without spawning Codex")

    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()

        if args.command == "run-cycle":
            return int(run_cycle())

        if args.command == "enqueue":
            return int(enqueue_files(parse_enqueue_files(args)))

        if args.command == "progress":
            return int(report_progress(args.file))

        if args.command == "self-check":
            return int(run_self_check())

        print(f"Unsupported command: {args.command}", file=sys.stderr)
        return int(ExitCode.CHECKER_FAILURE)
    except CheckerFailureError as error:
        try:
            log_project_journal("step", f"checker failure: {error}")
        except CheckerFailureError as journal_error:
            print(f"Checker failure logging also failed:\n{journal_error}", file=sys.stderr)

        print(f"Checker failure:\n{error}", file=sys.stderr)
        return int(ExitCode.CHECKER_FAILURE)


if __name__ == "__main__":
    raise SystemExit(main())
