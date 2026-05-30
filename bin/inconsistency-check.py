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

# TODO: depmesh does not support missed files detection => we may miss some inconsistencies
# TODO: we excluded tested_by/tests extensions from the checker for now, need to return them back later

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shlex
import shutil
import subprocess  # noqa: S404
import sys
import time
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "consistency.toml"
TASKWARRIOR_BIN = "task"
VALID_CHECK_STATUSES = {"unchecked", "consistent", "inconsistent", "outdated"}


@dataclass(frozen=True)
class RelationConfig:
    description: str
    criteria: tuple[str, ...]


@dataclass(frozen=True)
class ConsistencyConfig:
    mode: str
    runtime_dir: Path
    comparison_base_refs: tuple[str, ...]
    allowed_file_relations: tuple[str, ...]
    jobs: int
    journal_cmd: tuple[str, ...]
    agent_cmd: tuple[str, ...]
    agent_timeout_seconds: int
    prompt_template: str
    output_schema: dict[str, Any]
    common_criteria: tuple[str, ...]
    relations: dict[str, RelationConfig]


@dataclass(frozen=True)
class RuntimePaths:
    relative_runtime_dir: Path
    runtime_dir: Path
    relative_taskrc_path: Path
    taskrc_path: Path
    task_data_dir: Path
    agent_output_dir: Path
    prompt_dir: Path
    schema_dir: Path
    self_check_dir: Path


ACTIVE_CONFIG: ConsistencyConfig | None = None


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
class ListPairsOptions:
    multi_line: bool = False
    include_report: bool = False
    include_all_fields: bool = False
    statuses: tuple[str, ...] = ()
    include_count: bool = True


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
class RunningChildCheck:
    prepared: PreparedChildCheck
    argv: tuple[str, ...]
    process: subprocess.Popen[str]
    stdout_path: Path
    stderr_path: Path
    started_at: float


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


class OutdatedPairError(CheckerFailureError):
    """Raised when a pair's stored checksums do not match current files."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def require_table(source: dict[str, Any], key: str, *, context: str) -> dict[str, Any]:
    value = source.get(key)

    if not isinstance(value, dict):
        raise CheckerFailureError(f"{context}: {key} must be a table")

    return value


def require_string(source: dict[str, Any], key: str, *, context: str) -> str:
    value = source.get(key)

    if not isinstance(value, str) or not value:
        raise CheckerFailureError(f"{context}: {key} must be a non-empty string")

    return value


def require_bool(source: dict[str, Any], key: str, *, context: str) -> bool:
    value = source.get(key)

    if not isinstance(value, bool):
        raise CheckerFailureError(f"{context}: {key} must be a boolean")

    return value


def require_int(source: dict[str, Any], key: str, *, context: str) -> int:
    value = source.get(key)

    if not isinstance(value, int):
        raise CheckerFailureError(f"{context}: {key} must be an integer")

    return value


def require_string_list(source: dict[str, Any], key: str, *, context: str) -> tuple[str, ...]:
    value = source.get(key)

    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise CheckerFailureError(f"{context}: {key} must be a list of non-empty strings")

    return tuple(value)


def normalize_runtime_dir(path: str) -> Path:
    runtime_dir = Path(path)

    if runtime_dir.is_absolute():
        try:
            runtime_dir = runtime_dir.resolve(strict=False).relative_to(PROJECT_ROOT.resolve())
        except ValueError as error:
            raise CheckerFailureError(f"consistency.toml: runtime_dir must stay under project root: {path}") from error

    normalized = PurePosixPath(runtime_dir.as_posix())

    if normalized.is_absolute() or ".." in normalized.parts or str(normalized) == ".":
        raise CheckerFailureError(f"consistency.toml: unsupported runtime_dir: {path}")

    return Path(*normalized.parts)


def resolve_mode_config(raw_config: dict[str, Any], mode_id: str | None) -> tuple[str, dict[str, Any]]:
    selected_mode = mode_id or str(raw_config.get("mode") or "default")

    if not selected_mode:
        raise CheckerFailureError("consistency.toml: mode must be a non-empty string")

    modes = raw_config.get("modes", {})

    if modes is None:
        modes = {}

    if not isinstance(modes, dict):
        raise CheckerFailureError("consistency.toml: modes must be a table")

    resolved = copy.deepcopy({key: value for key, value in raw_config.items() if key != "modes"})

    if selected_mode != "default":
        mode_config = modes.get(selected_mode)

        if not isinstance(mode_config, dict):
            valid_modes = ", ".join(["default", *sorted(str(key) for key in modes)]) or "default"
            raise CheckerFailureError(f"consistency.toml: unknown mode {selected_mode!r}; valid modes: {valid_modes}")

        for key, value in mode_config.items():
            if key == "modes":
                raise CheckerFailureError("consistency.toml: mode override may not replace modes")

            resolved[key] = copy.deepcopy(value)

    return selected_mode, resolved


def validate_output_schema(schema: dict[str, Any]) -> None:
    if schema.get("type") != "object":
        raise CheckerFailureError("consistency.toml: output_schema.type must be object")

    required = schema.get("required")
    properties = schema.get("properties")

    if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
        raise CheckerFailureError("consistency.toml: output_schema.required must be a list of strings")

    if not isinstance(properties, dict):
        raise CheckerFailureError("consistency.toml: output_schema.properties must be a table")

    for key in ("check_status", "report"):
        if key not in required or key not in properties:
            raise CheckerFailureError(f"consistency.toml: output_schema must require property {key!r}")


def validate_config(config: dict[str, Any], *, mode: str) -> ConsistencyConfig:
    version = config.get("version")

    if version != 1:
        raise CheckerFailureError("consistency.toml: version must be 1")

    runtime_dir = normalize_runtime_dir(require_string(config, "runtime_dir", context="consistency.toml"))
    comparison_base_refs = require_string_list(config, "comparison_base_refs", context="consistency.toml")
    allowed_file_relations = require_string_list(config, "allowed_file_relations", context="consistency.toml")
    jobs = require_int(config, "jobs", context="consistency.toml")

    if jobs <= 0:
        raise CheckerFailureError("consistency.toml: jobs must be positive")

    journal = require_table(config, "journal", context="consistency.toml")
    journal_cmd = require_string_list(journal, "cmd", context="consistency.toml journal")
    agent = require_table(config, "agent", context="consistency.toml")
    agent_cmd = require_string_list(agent, "cmd", context="consistency.toml agent")
    agent_timeout_seconds = require_int(agent, "timeout_seconds", context="consistency.toml agent")

    if agent_timeout_seconds <= 0:
        raise CheckerFailureError("consistency.toml: agent.timeout_seconds must be positive")

    prompt = require_table(config, "prompt", context="consistency.toml")
    prompt_template = require_string(prompt, "template", context="consistency.toml prompt")
    output_schema = copy.deepcopy(require_table(config, "output_schema", context="consistency.toml"))
    validate_output_schema(output_schema)

    criteria = require_table(config, "criteria", context="consistency.toml")
    common_criteria = require_string_list(criteria, "common", context="consistency.toml criteria")
    raw_relations = require_table(config, "relations", context="consistency.toml")
    relations: dict[str, RelationConfig] = {}

    for relation_id, relation_config in raw_relations.items():
        if not isinstance(relation_id, str) or not relation_id:
            raise CheckerFailureError("consistency.toml: relation ids must be non-empty strings")

        if not isinstance(relation_config, dict):
            raise CheckerFailureError(f"consistency.toml: relations.{relation_id} must be a table")

        relations[relation_id] = RelationConfig(
            description=require_string(
                relation_config,
                "description",
                context=f"consistency.toml relations.{relation_id}",
            ),
            criteria=require_string_list(
                relation_config,
                "criteria",
                context=f"consistency.toml relations.{relation_id}",
            ),
        )

    missing_relations = sorted(set(allowed_file_relations) - set(relations))

    if missing_relations:
        raise CheckerFailureError(
            "consistency.toml: allowed_file_relations missing relation config: "
            + ", ".join(missing_relations)
        )

    return ConsistencyConfig(
        mode=mode,
        runtime_dir=runtime_dir,
        comparison_base_refs=comparison_base_refs,
        allowed_file_relations=allowed_file_relations,
        jobs=jobs,
        journal_cmd=journal_cmd,
        agent_cmd=agent_cmd,
        agent_timeout_seconds=agent_timeout_seconds,
        prompt_template=prompt_template,
        output_schema=output_schema,
        common_criteria=common_criteria,
        relations=relations,
    )


def load_consistency_config(path: Path = CONFIG_PATH, *, mode: str | None = None) -> ConsistencyConfig:
    if not path.exists():
        raise CheckerFailureError(f"missing consistency config: {path}")

    try:
        with path.open("rb") as config_file:
            raw_config = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise CheckerFailureError(f"invalid consistency config TOML: {error}") from error

    selected_mode, resolved_config = resolve_mode_config(raw_config, mode)

    return validate_config(resolved_config, mode=selected_mode)


def load_configured_mode_ids(path: Path = CONFIG_PATH) -> tuple[str, ...]:
    if not path.exists():
        raise CheckerFailureError(f"missing consistency config: {path}")

    try:
        with path.open("rb") as config_file:
            raw_config = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise CheckerFailureError(f"invalid consistency config TOML: {error}") from error

    raw_modes = raw_config.get("modes", {})

    if raw_modes is None:
        raw_modes = {}

    if not isinstance(raw_modes, dict):
        raise CheckerFailureError("consistency.toml: modes must be a table")

    mode_ids = []

    for mode_id in raw_modes:
        if not isinstance(mode_id, str) or not mode_id:
            raise CheckerFailureError("consistency.toml: mode ids must be non-empty strings")

        mode_ids.append(mode_id)

    return tuple(sorted(mode_ids))


def configure_consistency(mode: str | None = None) -> ConsistencyConfig:
    global ACTIVE_CONFIG  # noqa: PLW0603

    ACTIVE_CONFIG = load_consistency_config(mode=mode)

    return ACTIVE_CONFIG


def get_config() -> ConsistencyConfig:
    if ACTIVE_CONFIG is None:
        return configure_consistency()

    return ACTIVE_CONFIG


def runtime_paths() -> RuntimePaths:
    relative_runtime_dir = get_config().runtime_dir
    runtime_dir = PROJECT_ROOT / relative_runtime_dir

    return RuntimePaths(
        relative_runtime_dir=relative_runtime_dir,
        runtime_dir=runtime_dir,
        relative_taskrc_path=relative_runtime_dir / "taskrc",
        taskrc_path=runtime_dir / "taskrc",
        task_data_dir=runtime_dir / "taskwarrior",
        agent_output_dir=runtime_dir / "agent-output",
        prompt_dir=runtime_dir / "prompts",
        schema_dir=runtime_dir / "schemas",
        self_check_dir=runtime_dir / "self-check",
    )


def build_taskrc_content(paths: RuntimePaths) -> str:
    return f"""data.location={paths.relative_runtime_dir / "taskwarrior"}
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
uda.check_status.values=unchecked,consistent,inconsistent,outdated,
uda.report.type=string
uda.report.label=Report
uda.checked_at.type=string
uda.checked_at.label=Checked At
"""


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
    timeout_seconds: int | None = None,
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
            timeout=timeout_seconds,
        )
    except OSError as error:
        raise CheckerFailureError(f"{failure_context}: {format_argv(command)}: {error}") from error
    except subprocess.TimeoutExpired as error:
        raise CheckerFailureError(
            f"{failure_context}: timed out after {timeout_seconds} seconds: {format_argv(command)}"
        ) from error

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
    for ref in get_config().comparison_base_refs:
        result = run_command(
            ["git", "rev-parse", "--verify", ref],
            failure_context=f"resolving comparison base {ref}",
        )

        if result.returncode == 0:
            return ref

    valid_refs = ", ".join(get_config().comparison_base_refs)
    raise CheckerFailureError(f"could not resolve comparison base from configured refs: {valid_refs}")


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
    config = get_config()
    depmesh_relations = {relation.relation_id: relation for relation in load_depmesh_relations()}
    missing_depmesh_relations = sorted(set(config.allowed_file_relations) - set(depmesh_relations))

    if missing_depmesh_relations:
        raise CheckerFailureError(
            "configured allowed_file_relations not found in depmesh: "
            + ", ".join(missing_depmesh_relations)
        )

    relations = [
        DepmeshRelation(
            relation_id=relation_id,
            description=config.relations[relation_id].description,
        )
        for relation_id in config.allowed_file_relations
    ]
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
                f"depmesh query for {changed_path} relation {relation.relation_id} found {len(pairs)} related files",
            )

            for pair in pairs:
                log_project_journal(
                    "step",
                    (
                        "depmesh relation pair found "
                        f"{pair.changed_path} -> {pair.related_path} [{pair.relation}]"
                    ),
                )
                pair_map[(pair.changed_path, pair.relation, pair.related_path)] = pair

    return [pair_map[key] for key in sorted(pair_map)]


def render_expression_template(template: str, context: dict[str, Any]) -> str:
    parts: list[str] = []
    index = 0

    while index < len(template):
        char = template[index]

        if char == "{":
            if index + 1 < len(template) and template[index + 1] == "{":
                parts.append("{")
                index += 2
                continue

            end_index = template.find("}", index + 1)

            if end_index == -1:
                raise CheckerFailureError("template rendering failed: unmatched '{'")

            expression = template[index + 1 : end_index].strip()

            if not expression:
                raise CheckerFailureError("template rendering failed: empty expression")

            try:
                value = eval(expression, {"__builtins__": {}}, context)  # noqa: S307
            except Exception as error:
                raise CheckerFailureError(
                    f"template rendering failed for expression {expression!r}: {error}"
                ) from error

            parts.append(str(value))
            index = end_index + 1
            continue

        if char == "}":
            if index + 1 < len(template) and template[index + 1] == "}":
                parts.append("}")
                index += 2
                continue

            raise CheckerFailureError("template rendering failed: unmatched '}'")

        parts.append(char)
        index += 1

    return "".join(parts)


def render_command_argv(argv: Iterable[str], context: dict[str, Any]) -> tuple[str, ...]:
    return tuple(render_expression_template(part, context) for part in argv)


def single_line(value: str) -> str:
    return " ".join(value.split())


def log_project_journal(kind: str, message: str) -> None:
    """Log project-level script events without touching relation-pair records."""

    clean_kind = single_line(kind)

    if not clean_kind or clean_kind != kind:
        raise CheckerFailureError(f"invalid journal kind: {kind!r}")

    command = render_command_argv(
        get_config().journal_cmd,
        {
            "kind": clean_kind,
            "message": single_line(message),
        },
    )
    result = run_command(
        command,
        failure_context="project journal logging failed",
    )

    if result.returncode != 0:
        raise CheckerFailureError(build_command_failure("project journal logging failed", result))


def pair_journal_subject(identity: PairIdentity) -> str:
    return f"{identity.changed_path} -> {identity.related_path} [{identity.relation}]"


def record_journal_subject(record: CheckRecord) -> str:
    return f"{record.changed_path} -> {record.related_path} [{record.relation}]"


def record_identity(record: CheckRecord) -> PairIdentity:
    return PairIdentity(
        pair_key=record.pair_key,
        file_pair=record.file_pair,
        changed_path=record.changed_path,
        related_path=record.related_path,
        relation=record.relation,
        checksum_changed=record.checksum_changed,
        checksum_related=record.checksum_related,
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
    paths = runtime_paths()
    paths.runtime_dir.mkdir(parents=True, exist_ok=True)
    paths.task_data_dir.mkdir(parents=True, exist_ok=True)
    paths.agent_output_dir.mkdir(parents=True, exist_ok=True)
    paths.prompt_dir.mkdir(parents=True, exist_ok=True)
    paths.schema_dir.mkdir(parents=True, exist_ok=True)
    paths.self_check_dir.mkdir(parents=True, exist_ok=True)
    paths.taskrc_path.write_text(build_taskrc_content(paths), encoding="utf-8")


def task_command_args(*args: str) -> list[str]:
    return [
        TASKWARRIOR_BIN,
        f"rc:{runtime_paths().relative_taskrc_path.as_posix()}",
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
        raise CheckerFailureError("isolated Taskwarrior DB has duplicate pair_key records")

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
        raise CheckerFailureError(f"Taskwarrior record was not found after write: {pair_journal_subject(identity)}")

    return raw_record_to_check_record(raw_record)


def upsert_unchecked_record(identity: PairIdentity) -> CheckRecord:
    raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), identity.pair_key)

    if raw_record is None:
        record = write_task_record(identity, uuid=None, check_status="unchecked", report="", checked_at="")
        log_pair_queued(identity, record.check_status or "unchecked")

        return record

    existing = raw_record_to_check_record(raw_record)
    existing_status = existing.check_status or "unchecked"
    should_reset_outdated = existing_status == "outdated"
    next_status = "unchecked" if should_reset_outdated else existing_status
    next_report = "" if should_reset_outdated else existing.report
    next_checked_at = "" if should_reset_outdated else existing.checked_at

    record = write_task_record(
        identity,
        uuid=existing.uuid,
        check_status=next_status,
        report=next_report,
        checked_at=next_checked_at,
    )

    if should_reset_outdated:
        log_pair_state_change(identity, "outdated", "unchecked")

    return record


def update_check_record(identity: PairIdentity, *, check_status: str, report: str, checked_at: str) -> CheckRecord:
    raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), identity.pair_key)

    if raw_record is None:
        raise CheckerFailureError(f"cannot update missing pair record: {pair_journal_subject(identity)}")

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


def record_outdated_reason(record: CheckRecord) -> str | None:
    try:
        changed = read_artifact_snapshot(record.changed_path)
    except MissingArtifactError:
        return f"changed file is missing: {record.changed_path}"

    try:
        related = read_artifact_snapshot(record.related_path)
    except MissingArtifactError:
        return f"related file is missing: {record.related_path}"

    if changed.checksum != record.checksum_changed:
        return (
            f"changed file checksum differs: {record.changed_path} "
            f"expected sha256:{record.checksum_changed} actual sha256:{changed.checksum}"
        )

    if related.checksum != record.checksum_related:
        return (
            f"related file checksum differs: {record.related_path} "
            f"expected sha256:{record.checksum_related} actual sha256:{related.checksum}"
        )

    return None


def mark_record_outdated(record: CheckRecord, reason: str) -> CheckRecord:
    if normalized_check_status(record) == "outdated":
        return record

    identity = record_identity(record)
    updated_record = write_task_record(
        identity,
        uuid=record.uuid,
        check_status="outdated",
        report=record.report,
        checked_at=utc_timestamp(),
    )
    log_pair_state_change(identity, record.check_status or "unchecked", "outdated")
    log_project_journal("step", f"outdated pair detected for {record_journal_subject(record)}: {single_line(reason)}")

    return updated_record


def mark_record_outdated_if_needed(record: CheckRecord) -> CheckRecord:
    reason = record_outdated_reason(record)

    if reason is None:
        return record

    return mark_record_outdated(record, reason)


def mark_record_outdated_during_processing(record: CheckRecord, reason: str) -> CheckRecord:
    return mark_record_outdated(record, reason)


def mark_current_pair_outdated_if_needed(current_pair: CurrentPair) -> CurrentPair:
    record = mark_record_outdated_if_needed(current_pair.record)

    if record.uuid == current_pair.record.uuid and record.check_status == current_pair.record.check_status:
        return current_pair

    return CurrentPair(pair=current_pair.pair, identity=current_pair.identity, record=record)


def relation_description_for(relation_id: str) -> str:
    descriptions = {
        configured_relation_id: relation.description
        for configured_relation_id, relation in get_config().relations.items()
    }

    if relation_id not in descriptions:
        valid_relations = ", ".join(sorted(descriptions)) or "(none)"
        raise CheckerFailureError(f"unknown configured relation {relation_id!r}; valid relations: {valid_relations}")

    return descriptions[relation_id]


def normalize_explicit_report(check_status: str, report: str | None) -> str:
    if check_status == "consistent":
        return report or ""

    inconsistent_report = report or "No report was provided."

    if any(line.startswith("## ") for line in inconsistent_report.splitlines()):
        return inconsistent_report

    return "\n\n".join(["## Manually marked inconsistent", inconsistent_report])


def set_relation_pair_check_status(
    pair: RelationPair,
    *,
    check_status: str,
    report: str | None,
) -> CurrentPair:
    if check_status not in {"consistent", "inconsistent"}:
        raise CheckerFailureError(f"unsupported explicit check status: {check_status}")

    identity = build_pair_identity(pair)
    upsert_unchecked_record(identity)
    record = update_check_record(
        identity,
        check_status=check_status,
        report=normalize_explicit_report(check_status, report),
        checked_at=utc_timestamp(),
    )
    log_project_journal(
        "step",
        f"explicit pair status set for {pair_journal_subject(identity)}: {check_status}",
    )

    return CurrentPair(pair=pair, identity=identity, record=record)


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
        raise CheckerFailureError(f"unsupported check_status {status!r} for pair {record_journal_subject(record)}")

    return status


def select_current_pair(current_pairs: list[CurrentPair]) -> PairSelection:
    ordered_pairs = sorted(current_pairs, key=current_pair_sort_key)

    for current_pair in ordered_pairs:
        if normalized_check_status(current_pair.record) == "inconsistent":
            log_project_journal(
                "step",
                f"existing current inconsistency found: {pair_journal_subject(current_pair.identity)}",
            )
            return PairSelection(inconsistent=current_pair, unchecked=None)

    for current_pair in ordered_pairs:
        if normalized_check_status(current_pair.record) == "unchecked":
            log_project_journal("step", f"selected unchecked pair: {pair_journal_subject(current_pair.identity)}")
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
    print(f"outdated pairs: {counts.get('outdated', 0)}")

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


def relation_specific_criteria(relation_id: str) -> list[str]:
    config = get_config()
    relation_config = config.relations.get(relation_id)

    if relation_config is None:
        valid_relations = ", ".join(sorted(config.relations)) or "(none)"
        raise CheckerFailureError(f"unknown configured relation {relation_id!r}; valid relations: {valid_relations}")

    return [*relation_config.criteria, *config.common_criteria]


def fenced_content(label: str, content: str) -> str:
    fence = "```"

    while fence in content:
        fence += "`"

    return f"{label}\n{fence}\n{content}\n{fence}"


def sha256_file(path: str) -> str:
    filesystem_path = PROJECT_ROOT / path

    try:
        content = filesystem_path.read_bytes()
    except OSError as error:
        raise CheckerFailureError(f"could not read file for sha256_file({path!r}): {error}") from error

    return checksum_bytes(content)


def identity_hash(identity: PairIdentity) -> str:
    return hashlib.sha256(identity.pair_key.encode("utf-8")).hexdigest()


def validate_prompt_snapshots(current_pair: CurrentPair) -> tuple[FileSnapshot, FileSnapshot]:
    changed, related = read_pair_snapshots(current_pair.pair)

    if changed.checksum != current_pair.identity.checksum_changed:
        raise OutdatedPairError(f"changed file checksum drifted before child check: {changed.artifact_path}")

    if related.checksum != current_pair.identity.checksum_related:
        raise OutdatedPairError(f"related file checksum drifted before child check: {related.artifact_path}")

    return changed, related


def build_child_prompt(current_pair: CurrentPair) -> str:
    changed, related = validate_prompt_snapshots(current_pair)
    base_ref = resolve_comparison_base()
    merge_base = merge_base_with_head(base_ref)
    criteria = "\n".join(f"- {criterion}" for criterion in relation_specific_criteria(current_pair.pair.relation))
    context = {
        "pair": SimpleNamespace(
            relation=current_pair.pair.relation,
            relation_description=current_pair.pair.relation_description,
        ),
        "changed": SimpleNamespace(
            path=changed.root_path,
            artifact_path=changed.artifact_path,
            root_path=changed.root_path,
            checksum=changed.checksum,
            text=changed.text,
        ),
        "related": SimpleNamespace(
            path=related.root_path,
            artifact_path=related.artifact_path,
            root_path=related.root_path,
            checksum=related.checksum,
            text=related.text,
        ),
        "git": SimpleNamespace(merge_base=merge_base),
        "criteria": criteria,
        "fenced_content": fenced_content,
        "sha256_file": sha256_file,
    }

    return render_expression_template(get_config().prompt_template, context)


def prepare_child_check(current_pair: CurrentPair) -> PreparedChildCheck:
    ensure_runtime_state()
    paths = runtime_paths()
    key_hash = identity_hash(current_pair.identity)
    prompt_path = paths.prompt_dir / f"{key_hash}.md"
    schema_path = paths.schema_dir / f"{key_hash}.schema.json"
    output_path = paths.agent_output_dir / f"{key_hash}.json"
    prompt = build_child_prompt(current_pair)
    output_path.unlink(missing_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    schema_path.write_text(json.dumps(get_config().output_schema, indent=2, sort_keys=True), encoding="utf-8")

    return PreparedChildCheck(
        current_pair=current_pair,
        prompt_path=prompt_path,
        schema_path=schema_path,
        output_path=output_path,
        prompt=prompt,
    )


def run_child_checker(prepared: PreparedChildCheck) -> str:
    running = start_child_checker(prepared)

    while running.process.poll() is None:
        if child_checker_timed_out(running):
            kill_running_child(running)
            raise CheckerFailureError(
                "running child Codex checker for "
                f"{pair_journal_subject(prepared.current_pair.identity)}: "
                f"timed out after {get_config().agent_timeout_seconds} seconds: "
                f"{format_argv(running.argv)}"
            )

        time.sleep(0.1)

    return finish_child_checker(running)


def start_child_checker(prepared: PreparedChildCheck) -> RunningChildCheck:
    pair_subject = pair_journal_subject(prepared.current_pair.identity)
    log_project_journal("step", f"child checker start for {pair_subject}")
    command = render_command_argv(
        get_config().agent_cmd,
        {
            "project_root": str(PROJECT_ROOT),
            "prompt_path": str(prepared.prompt_path),
            "schema_path": str(prepared.schema_path),
            "output_path": str(prepared.output_path),
        },
    )

    stdout_path = prepared.output_path.with_suffix(".stdout.txt")
    stderr_path = prepared.output_path.with_suffix(".stderr.txt")

    try:
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
            "w",
            encoding="utf-8",
        ) as stderr_file:
            process = subprocess.Popen(  # noqa: S603
                command,
                cwd=PROJECT_ROOT,
                stdin=subprocess.PIPE,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
            )
    except OSError as error:
        raise CheckerFailureError(
            f"running child Codex checker for {pair_subject}: {format_argv(command)}: {error}"
        ) from error

    if process.stdin is None:
        kill_running_child(
            RunningChildCheck(
                prepared=prepared,
                argv=command,
                process=process,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=time.monotonic(),
            )
        )
        raise CheckerFailureError(f"child Codex checker stdin was unavailable for {pair_subject}")

    try:
        process.stdin.write(prepared.prompt)
        process.stdin.close()
    except OSError as error:
        kill_running_child(
            RunningChildCheck(
                prepared=prepared,
                argv=command,
                process=process,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=time.monotonic(),
            )
        )
        raise CheckerFailureError(f"writing child Codex checker prompt failed for {pair_subject}: {error}") from error

    return RunningChildCheck(
        prepared=prepared,
        argv=command,
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        started_at=time.monotonic(),
    )


def child_checker_timed_out(running: RunningChildCheck) -> bool:
    return time.monotonic() - running.started_at > get_config().agent_timeout_seconds


def kill_running_child(running: RunningChildCheck) -> None:
    if running.process.poll() is not None:
        return

    running.process.kill()
    running.process.wait()


def finish_child_checker(running: RunningChildCheck) -> str:
    pair_subject = pair_journal_subject(running.prepared.current_pair.identity)
    returncode = running.process.wait()
    stdout = running.stdout_path.read_text(encoding="utf-8") if running.stdout_path.exists() else ""
    stderr = running.stderr_path.read_text(encoding="utf-8") if running.stderr_path.exists() else ""
    result = CommandResult(argv=running.argv, returncode=returncode, stdout=stdout, stderr=stderr)

    if result.returncode != 0:
        raise CheckerFailureError(build_command_failure("child Codex checker failed", result))

    if not running.prepared.output_path.exists():
        raise CheckerFailureError(f"child Codex checker did not write output file: {running.prepared.output_path}")

    output = running.prepared.output_path.read_text(encoding="utf-8")
    log_project_journal("step", f"child checker completed for {pair_subject}")

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

    output_schema = get_config().output_schema
    properties = output_schema.get("properties", {})
    allowed_keys = set(properties) if isinstance(properties, dict) else {"check_status", "report"}
    extra_keys = sorted(set(result) - allowed_keys)

    if output_schema.get("additionalProperties") is False and extra_keys:
        return "inconsistent", malformed_child_report(f"unexpected keys: {', '.join(extra_keys)}", output)

    required = output_schema.get("required", [])
    missing_keys = sorted(key for key in required if isinstance(key, str) and key not in result)

    if missing_keys:
        return "inconsistent", malformed_child_report(f"missing required keys: {', '.join(missing_keys)}", output)

    if isinstance(properties, dict):
        for key, property_schema in properties.items():
            if key not in result or not isinstance(property_schema, dict):
                continue

            if property_schema.get("type") == "string" and not isinstance(result[key], str):
                return "inconsistent", malformed_child_report(f"{key} must be a string", output)

            allowed_values = property_schema.get("enum")

            if isinstance(allowed_values, list) and result[key] not in allowed_values:
                return "inconsistent", malformed_child_report(
                    f"{key} must be one of: {', '.join(str(value) for value in allowed_values)}",
                    output,
                )

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
    log_project_journal(
        "step",
        f"pair status update for {pair_journal_subject(current_pair.identity)}: {check_status}",
    )

    return CurrentPair(pair=current_pair.pair, identity=current_pair.identity, record=record)


def first_unchecked_pair(current_pairs: list[CurrentPair], excluded_pair_keys: set[str]) -> CurrentPair | None:
    for current_pair in sorted(current_pairs, key=current_pair_sort_key):
        if current_pair.identity.pair_key in excluded_pair_keys:
            continue

        if normalized_check_status(current_pair.record) == "unchecked":
            return current_pair

    return None


def wait_for_finished_children(running: dict[str, RunningChildCheck]) -> list[RunningChildCheck]:
    while True:
        finished = [child for child in running.values() if child.process.poll() is not None]

        if finished:
            return finished

        timed_out = [child for child in running.values() if child_checker_timed_out(child)]

        if timed_out:
            timed_out_child = sorted(
                timed_out,
                key=lambda child: current_pair_sort_key(child.prepared.current_pair),
            )[0]
            kill_running_child(timed_out_child)
            raise CheckerFailureError(
                "running child Codex checker for "
                f"{pair_journal_subject(timed_out_child.prepared.current_pair.identity)}: "
                f"timed out after {get_config().agent_timeout_seconds} seconds: "
                f"{format_argv(timed_out_child.argv)}"
            )

        time.sleep(0.1)


def terminate_running_children(running: dict[str, RunningChildCheck]) -> None:
    for child in running.values():
        kill_running_child(child)


def process_current_pairs(
    changed_files: list[str],
    current_pairs: list[CurrentPair],
    *,
    command_name: str,
    jobs: int,
) -> ExitCode:
    running: dict[str, RunningChildCheck] = {}
    inconsistency_found = False
    log_project_journal("step", f"{command_name} processing with jobs:{jobs}")

    try:
        while True:
            inconsistent_pair = first_inconsistent_pair(current_pairs)

            if inconsistent_pair is not None:
                inconsistency_found = True

                if not running:
                    print_inconsistent_pair(inconsistent_pair)
                    log_project_journal("step", f"{command_name} outcome: current inconsistency found")
                    return ExitCode.INCONSISTENCY_FOUND

            while not inconsistency_found and len(running) < jobs:
                unchecked_pair = first_unchecked_pair(current_pairs, set(running))

                if unchecked_pair is None:
                    break

                checked_pair = mark_current_pair_outdated_if_needed(unchecked_pair)

                if normalized_check_status(checked_pair.record) == "outdated":
                    current_pairs = replace_current_pair(current_pairs, checked_pair)
                    continue

                try:
                    prepared = prepare_child_check(checked_pair)
                except MissingArtifactError as error:
                    updated_record = mark_record_outdated_during_processing(
                        checked_pair.record,
                        f"file is missing before child check: {error.path}",
                    )
                    current_pairs = replace_current_pair(
                        current_pairs,
                        CurrentPair(pair=checked_pair.pair, identity=checked_pair.identity, record=updated_record),
                    )
                    continue
                except OutdatedPairError as error:
                    updated_record = mark_record_outdated_during_processing(checked_pair.record, error.reason)
                    current_pairs = replace_current_pair(
                        current_pairs,
                        CurrentPair(pair=checked_pair.pair, identity=checked_pair.identity, record=updated_record),
                    )
                    continue

                running[checked_pair.identity.pair_key] = start_child_checker(prepared)

            if not running:
                inconsistent_pair = first_inconsistent_pair(current_pairs)

                if inconsistent_pair is not None:
                    print_inconsistent_pair(inconsistent_pair)
                    log_project_journal("step", f"{command_name} outcome: child found inconsistency")
                    return ExitCode.INCONSISTENCY_FOUND

                print_summary(changed_files, current_pairs)
                log_project_journal("step", f"{command_name} outcome: success")
                return ExitCode.SUCCESS

            for finished_child in wait_for_finished_children(running):
                pair_key = finished_child.prepared.current_pair.identity.pair_key
                running.pop(pair_key)
                child_output = finish_child_checker(finished_child)
                updated_pair = update_record_from_child_output(finished_child.prepared.current_pair, child_output)
                current_pairs = replace_current_pair(current_pairs, updated_pair)

                if normalized_check_status(updated_pair.record) == "inconsistent":
                    inconsistency_found = True
    except CheckerFailureError:
        terminate_running_children(running)
        raise


def effective_jobs(args: argparse.Namespace) -> int:
    jobs = args.jobs if getattr(args, "jobs", None) is not None else get_config().jobs

    if jobs <= 0:
        raise CheckerFailureError("jobs must be positive")

    return jobs


def run_cycle(args: argparse.Namespace) -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "run-cycle command started")
    changed_files = discover_changed_files()
    relation_pairs = query_depmesh_pairs(changed_files)
    current_pairs = reconcile_queue(relation_pairs)

    return process_current_pairs(changed_files, current_pairs, command_name="run-cycle", jobs=effective_jobs(args))


def record_to_current_pair(record: CheckRecord, relation_descriptions: dict[str, str]) -> CurrentPair:
    identity = record_identity(record)
    pair = RelationPair(
        changed_path=record.changed_path,
        related_path=record.related_path,
        relation=record.relation,
        relation_description=relation_descriptions.get(record.relation, "No current depmesh relation description."),
    )

    return CurrentPair(pair=pair, identity=identity, record=record)


def load_queued_current_pairs() -> list[CurrentPair]:
    config = get_config()
    relation_descriptions = {
        relation_id: relation.description for relation_id, relation in config.relations.items()
    }
    records = [
        mark_record_outdated_if_needed(raw_record_to_check_record(record))
        for record in load_taskwarrior_records()
    ]
    current_pairs = [
        record_to_current_pair(record, relation_descriptions)
        for record in records
        if record.pair_key and record.relation in config.allowed_file_relations
    ]
    log_project_journal("step", f"loaded {len(current_pairs)} queued pair records")

    return current_pairs


def process_queue(args: argparse.Namespace) -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "process-queue command started")
    current_pairs = load_queued_current_pairs()
    changed_files = sorted({current_pair.pair.changed_path for current_pair in current_pairs})

    return process_current_pairs(changed_files, current_pairs, command_name="process-queue", jobs=effective_jobs(args))


def mark_outdated_records() -> tuple[int, int]:
    checked_count = 0
    marked_count = 0
    allowed_relations = set(get_config().allowed_file_relations)

    for raw_record in load_taskwarrior_records():
        if not raw_record.get("pair_key") or raw_record.get("relation") not in allowed_relations:
            continue

        checked_count += 1
        record = raw_record_to_check_record(raw_record)
        reason = record_outdated_reason(record)

        if reason is None:
            continue

        updated_record = mark_record_outdated(record, reason)

        if updated_record.check_status == "outdated" and record.check_status != "outdated":
            marked_count += 1

    return checked_count, marked_count


def mark_outdated() -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "mark-outdated command started")
    checked_count, marked_count = mark_outdated_records()
    log_project_journal(
        "step",
        f"mark-outdated command completed checked:{checked_count} marked:{marked_count}",
    )
    print(f"checked records: {checked_count}")
    print(f"marked outdated: {marked_count}")

    return ExitCode.SUCCESS


def build_progress_report(path: str) -> str:
    artifact_path = normalize_input_path(path)
    allowed_relations = set(get_config().allowed_file_relations)
    records = [
        raw_record_to_check_record(record)
        for record in load_taskwarrior_records()
        if record.get("changed_path") == artifact_path or record.get("related_path") == artifact_path
        if record.get("relation") in allowed_relations
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


def load_list_pair_records(statuses: Iterable[str] = ()) -> list[CheckRecord]:
    status_filter = set(statuses)
    allowed_relations = set(get_config().allowed_file_relations)
    records = [
        raw_record_to_check_record(record)
        for record in load_taskwarrior_records()
        if record.get("pair_key") and record.get("relation") in allowed_relations
    ]
    if status_filter:
        records = [record for record in records if (record.check_status or "unknown") in status_filter]

    records.sort(key=lambda record: (record.changed_path, record.relation, record.related_path, record.pair_key))

    return records


def list_pair_record_fields(record: CheckRecord, options: ListPairsOptions) -> list[tuple[str, str]]:
    fields = [
        ("changed file", record.changed_path),
        ("related file", record.related_path),
        ("status", record.check_status or "unknown"),
    ]

    if options.include_all_fields:
        fields = [
            ("uuid", record.uuid),
            ("pair key", record.pair_key),
            ("file pair", record.file_pair),
            ("changed file", record.changed_path),
            ("related file", record.related_path),
            ("relation", record.relation),
            ("changed checksum", record.checksum_changed),
            ("related checksum", record.checksum_related),
            ("status", record.check_status or "unknown"),
            ("report", "present" if record.report else "empty"),
            ("checked at", record.checked_at),
        ]

    return fields


def format_list_pair_record_single_line(record: CheckRecord, options: ListPairsOptions) -> list[str]:
    fields = list_pair_record_fields(record, options)
    status = record.check_status or "unknown"
    fields_without_status = [(name, value) for name, value in fields if name != "status"]
    lines = [" | ".join([status, *(f"{name}: {value}" for name, value in fields_without_status)])]

    if options.include_report:
        lines.append("report:")
        lines.append(record.report or "(empty report)")

    return lines


def format_list_pair_record_multi_line(record: CheckRecord, options: ListPairsOptions) -> list[str]:
    lines = [f"{name}: {value}" for name, value in list_pair_record_fields(record, options)]

    if options.include_report:
        lines.append("report:")
        lines.append(record.report or "(empty report)")

    return lines


def build_list_pairs_report(options: ListPairsOptions | None = None) -> str:
    options = options or ListPairsOptions()
    records = load_list_pair_records(options.statuses)
    lines: list[str] = []

    for index, record in enumerate(records):
        if index and options.multi_line:
            lines.append("")

        if options.multi_line:
            lines.extend(format_list_pair_record_multi_line(record, options))
        else:
            lines.extend(format_list_pair_record_single_line(record, options))

    if options.include_count:
        if lines:
            lines.append("")

        lines.append(f"records: {len(records)}")

    return "\n".join(lines)


def list_pairs(args: argparse.Namespace) -> ExitCode:
    ensure_runtime_state()
    options = ListPairsOptions(
        multi_line=bool(args.multi_line),
        include_report=bool(args.report),
        include_all_fields=bool(args.all),
        statuses=tuple(args.statuses or ()),
        include_count=not bool(args.no_count),
    )
    log_project_journal(
        "step",
        f"list-pairs command started statuses:{','.join(options.statuses) or 'all'}",
    )
    report = build_list_pairs_report(options)

    if report:
        print(report)

    return ExitCode.SUCCESS


def print_status_update(current_pair: CurrentPair) -> None:
    record = current_pair.record
    print("Updated relation pair status")
    print(f"changed file: {record.changed_path}")
    print(f"related file: {record.related_path}")
    print(f"relation: {record.relation}")
    print(f"status: {record.check_status}")
    print(f"checked at: {record.checked_at}")
    print(f"pair key: {record.pair_key}")


def mark_pair_status(args: argparse.Namespace, *, check_status: str) -> ExitCode:
    ensure_runtime_state()
    changed_path = normalize_input_path(args.changed)
    related_path = normalize_input_path(args.related)
    relation = str(args.relation)

    if relation not in get_config().allowed_file_relations:
        log_project_journal(
            "step",
            f"skipped explicit pair status for disallowed relation {changed_path} -> {related_path} [{relation}]",
        )
        print("Skipped relation pair")
        print(f"changed file: {changed_path}")
        print(f"related file: {related_path}")
        print(f"relation: {relation}")
        print("reason: relation is not allowed")
        return ExitCode.SUCCESS

    pair = RelationPair(
        changed_path=changed_path,
        related_path=related_path,
        relation=relation,
        relation_description=relation_description_for(relation),
    )
    current_pair = set_relation_pair_check_status(
        pair,
        check_status=check_status,
        report=args.report,
    )
    print_status_update(current_pair)

    return ExitCode.SUCCESS


def print_enqueue_summary(artifact_path: str, current_pairs: list[CurrentPair]) -> None:
    counts = status_counts(current_pairs)
    print(f"Enqueued relation pairs for {artifact_path}")
    print(f"relation pairs: {len(current_pairs)}")
    print(f"consistent pairs: {counts.get('consistent', 0)}")
    print(f"inconsistent pairs: {counts.get('inconsistent', 0)}")
    print(f"unchecked pairs: {counts.get('unchecked', 0)}")
    print(f"outdated pairs: {counts.get('outdated', 0)}")

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


def clear_queue() -> ExitCode:
    ensure_runtime_state()
    records = load_taskwarrior_records()
    count = len(records)
    paths = runtime_paths()

    if paths.task_data_dir.exists():
        shutil.rmtree(paths.task_data_dir)

    ensure_runtime_state()
    log_project_journal("change", f"inconsistency-check cleared queue records:{count}")
    print(f"Cleared inconsistency-check queue records: {count}")

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


def runtime_artifact_path(*parts: str) -> str:
    return f"@/{(get_config().runtime_dir / Path(*parts)).as_posix()}"


def self_check_child_output(check_status: str, report: str) -> str:
    payload: dict[str, Any] = {
        "check_status": check_status,
        "report": report,
    }
    output_schema = get_config().output_schema
    properties = output_schema.get("properties", {})

    if isinstance(properties, dict):
        for key in output_schema.get("required", []):
            if not isinstance(key, str) or key in payload:
                continue

            property_schema = properties.get(key, {})

            if isinstance(property_schema, dict) and property_schema.get("type") == "string":
                enum = property_schema.get("enum")
                payload[key] = str(enum[0]) if isinstance(enum, list) and enum else "self-check"
            else:
                payload[key] = None

    return json.dumps(payload)


def run_self_check() -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "self-check command started")

    for mode_id in load_configured_mode_ids():
        mode_config = load_consistency_config(mode=mode_id)
        assert_self_check(mode_config.mode == mode_id, f"configured mode {mode_id!r} must load")

    active_config = get_config()
    assert_self_check(
        active_config.allowed_file_relations == ("governed_by",),
        "allowed relations must load from config",
    )
    assert_self_check(active_config.jobs > 0, "jobs must load from config")
    assert_self_check(
        relation_specific_criteria("governed_by")[0].startswith("The implementation"),
        "relation criteria must load from config",
    )
    changed_files = discover_changed_files()
    assert_self_check(all(path.startswith("@/") for path in changed_files), "changed files must be artifact ids")

    paths = runtime_paths()
    allowed_relation = get_config().allowed_file_relations[0]
    changed_path = runtime_artifact_path("self-check", "changed.txt")
    related_path = runtime_artifact_path("self-check", "related.txt")
    second_related_path = runtime_artifact_path("self-check", "second-related.txt")
    changed_file = paths.self_check_dir / "changed.txt"
    related_file = paths.self_check_dir / "related.txt"
    second_related_file = paths.self_check_dir / "second-related.txt"
    changed_file.write_text("changed self-check content\n", encoding="utf-8")
    related_file.write_text("related self-check content\n", encoding="utf-8")
    second_related_file.write_text("second related self-check content\n", encoding="utf-8")
    pair = RelationPair(
        changed_path=changed_path,
        related_path=related_path,
        relation=allowed_relation,
        relation_description="Self-check relation",
    )
    second_pair = RelationPair(
        changed_path=changed_path,
        related_path=second_related_path,
        relation=allowed_relation,
        relation_description="Self-check relation",
    )
    missing_pair = RelationPair(
        changed_path=changed_path,
        related_path=runtime_artifact_path("self-check", "missing.txt"),
        relation=allowed_relation,
        relation_description="Self-check relation",
    )
    identity = build_pair_identity(pair)
    second_identity = build_pair_identity(second_pair)
    assert_self_check(
        identity.pair_key == f"{allowed_relation}|{identity.file_pair}",
        "pair key must include relation",
    )
    assert_self_check(
        identity.file_pair.startswith(f"<{get_config().runtime_dir.as_posix()}/"),
        "file_pair must use root-relative paths",
    )
    reset_self_check_record(identity)
    reset_self_check_record(second_identity)
    current_pairs = reconcile_queue([pair, second_pair])
    assert_self_check(len(current_pairs) == 2, "queue reconciliation must return current pairs")
    assert_self_check(
        all(current_pair.record.check_status == "unchecked" for current_pair in current_pairs),
        "new current pairs must be unchecked",
    )
    prepared_self_check = prepare_child_check(current_pairs[0])
    serialized_schema = json.loads(prepared_self_check.schema_path.read_text(encoding="utf-8"))
    rendered_agent_cmd = render_command_argv(
        get_config().agent_cmd,
        {
            "project_root": str(PROJECT_ROOT),
            "prompt_path": str(prepared_self_check.prompt_path),
            "schema_path": str(prepared_self_check.schema_path),
            "output_path": str(prepared_self_check.output_path),
        },
    )
    changed_snapshot, _related_snapshot = read_pair_snapshots(pair)
    advanced_render = render_expression_template(
        "{fenced_content('Self-check file', changed.text)}",
        {"fenced_content": fenced_content, "changed": SimpleNamespace(text=changed_snapshot.text)},
    )
    assert_self_check(serialized_schema == get_config().output_schema, "output schema must serialize from config")
    assert_self_check(str(prepared_self_check.schema_path) in rendered_agent_cmd, "agent schema path must render")
    assert_self_check("Self-check file" in advanced_render, "prompt renderer must support function calls")
    assert_self_check(
        "changed self-check content" not in prepared_self_check.prompt,
        "default prompt must not embed full file contents",
    )
    missing_pairs = reconcile_queue([missing_pair])
    assert_self_check(not missing_pairs, "missing-file pairs must be skipped")
    selection = select_current_pair(current_pairs)
    assert_self_check(selection.unchecked is not None, "one unchecked pair must be selected")
    assert_self_check(selection.inconsistent is None, "unchecked selection must not report inconsistency")
    consistent_pair = update_record_from_child_output(
        selection.unchecked,
        self_check_child_output("consistent", ""),
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
        self_check_child_output("inconsistent", "## Self-check inconsistency\n\nSynthetic issue."),
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
    checked_count, marked_count = mark_outdated_records()
    outdated_raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), identity.pair_key)
    assert_self_check(outdated_raw_record is not None, "outdated source pair record must still exist")
    outdated_record = raw_record_to_check_record(outdated_raw_record)
    assert_self_check(checked_count > 0, "mark-outdated helper must check pair records")
    assert_self_check(marked_count > 0, "mark-outdated helper must mark stale pair records")
    assert_self_check(outdated_record.check_status == "outdated", "changed checksum must mark old pair outdated")
    changed_file.write_text("changed self-check content\n", encoding="utf-8")
    restored_pair = reconcile_queue([pair])[0]
    assert_self_check(
        restored_pair.record.check_status == "unchecked",
        "restored outdated pair must be reset to unchecked",
    )
    changed_file.write_text("changed self-check content v2\n", encoding="utf-8")
    changed_identity = build_pair_identity(pair)
    assert_self_check(changed_identity.pair_key != identity.pair_key, "editing one file must change the pair key")
    reset_self_check_record(changed_identity)
    changed_current_pair = reconcile_queue([pair])[0]
    assert_self_check(changed_current_pair.record.check_status == "unchecked", "changed checksum must force unchecked")
    explicitly_consistent_pair = set_relation_pair_check_status(
        pair,
        check_status="consistent",
        report="Manual self-check consistency note.",
    )
    assert_self_check(
        explicitly_consistent_pair.record.check_status == "consistent",
        "explicit status command helper must set consistent",
    )
    explicitly_inconsistent_pair = set_relation_pair_check_status(
        pair,
        check_status="inconsistent",
        report="Manual self-check inconsistency note.",
    )
    assert_self_check(
        explicitly_inconsistent_pair.record.check_status == "inconsistent",
        "explicit status command helper must set inconsistent",
    )
    assert_self_check(
        explicitly_inconsistent_pair.record.report.startswith("## Manually marked inconsistent"),
        "explicit inconsistent reports without a section must be normalized",
    )
    changed_report = build_progress_report(changed_path)
    related_report = build_progress_report(related_path)
    list_pairs_report = build_list_pairs_report(ListPairsOptions(statuses=("inconsistent",)))
    list_pairs_all_report = build_list_pairs_report(
        ListPairsOptions(include_all_fields=True, statuses=("inconsistent",))
    )
    list_pairs_report_report = build_list_pairs_report(
        ListPairsOptions(include_report=True, statuses=("inconsistent",))
    )
    list_pairs_multiline_report = build_list_pairs_report(
        ListPairsOptions(multi_line=True, statuses=("inconsistent",))
    )
    list_pairs_no_count_report = build_list_pairs_report(
        ListPairsOptions(statuses=("inconsistent",), include_count=False)
    )
    assert_self_check(changed_identity.pair_key in changed_report, "progress must match changed_path side")
    assert_self_check(changed_identity.pair_key in related_report, "progress must match related_path side")
    assert_self_check(changed_path in list_pairs_report, "list-pairs default report must include changed file")
    assert_self_check(related_path in list_pairs_report, "list-pairs default report must include related file")
    assert_self_check(
        list_pairs_report.startswith("inconsistent | "),
        "list-pairs default report must start with status",
    )
    assert_self_check(
        "status: inconsistent" not in list_pairs_report,
        "list-pairs default report must omit status label",
    )
    assert_self_check(
        changed_identity.pair_key not in list_pairs_report,
        "list-pairs default report must omit pair key",
    )
    assert_self_check(changed_identity.pair_key in list_pairs_all_report, "list-pairs --all must include pair key")
    assert_self_check(
        "## Manually marked inconsistent" in list_pairs_report_report,
        "list-pairs --report must include full report",
    )
    assert_self_check(
        "\nrelated file:" in list_pairs_multiline_report,
        "list-pairs --multi-line must place fields on separate lines",
    )
    assert_self_check(
        not list_pairs_no_count_report.splitlines()[-1].startswith("records:"),
        "list-pairs --no-count must omit output count",
    )
    assert_self_check(
        build_list_pairs_report(ListPairsOptions(statuses=("self-check-missing-status",))).strip()
        == "records: 0",
        "list-pairs status filter must filter records",
    )
    pair_records = load_taskwarrior_records()
    project_journal = json.loads(
        run_command(
            ["./bin/taskwarior.sh", "rc.verbose:nothing", "+journal", "export"],
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


def add_pair_status_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--changed",
        required=True,
        help="changed-side project path or root-anchored artifact id",
    )
    parser.add_argument(
        "--related",
        required=True,
        help="related-side project path or root-anchored artifact id",
    )
    parser.add_argument(
        "--relation",
        required=True,
        help="depmesh relation id for this oriented file pair",
    )
    parser.add_argument(
        "--report",
        help="optional markdown report to store with the explicit status",
    )


def add_jobs_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--jobs",
        type=int,
        help="number of child agent checks to keep running; defaults to consistency.toml jobs",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run depmesh-backed consistency checks.")
    parser.add_argument(
        "--mode",
        help="consistency.toml mode to use; defaults to the config's mode value",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_cycle_parser = subparsers.add_parser(
        "run-cycle",
        help="reconcile and check relation pairs until completion or inconsistency",
    )
    add_jobs_argument(run_cycle_parser)

    process_queue_parser = subparsers.add_parser(
        "process-queue",
        help="process queued relation pairs until completion or inconsistency",
    )
    add_jobs_argument(process_queue_parser)

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

    list_pairs_parser = subparsers.add_parser("list-pairs", help="list all queued relation pairs")
    list_pairs_parser.add_argument(
        "--multi-line",
        action="store_true",
        help="print each relation-pair record across multiple lines",
    )
    list_pairs_parser.add_argument(
        "--report",
        action="store_true",
        help="include the full markdown report for each relation-pair record",
    )
    list_pairs_parser.add_argument(
        "--all",
        action="store_true",
        help="include all stored relation-pair fields",
    )
    list_pairs_parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="include only records with this status; may be repeated",
    )
    list_pairs_parser.add_argument(
        "--no-count",
        action="store_true",
        help="do not print the number of output records",
    )

    mark_consistent_parser = subparsers.add_parser(
        "mark-consistent",
        help="explicitly mark one current-checksum relation pair as consistent",
    )
    add_pair_status_arguments(mark_consistent_parser)

    mark_inconsistent_parser = subparsers.add_parser(
        "mark-inconsistent",
        help="explicitly mark one current-checksum relation pair as inconsistent",
    )
    add_pair_status_arguments(mark_inconsistent_parser)

    subparsers.add_parser(
        "mark-outdated",
        help="mark registered relation pairs whose files are missing or have different checksums as outdated",
    )

    subparsers.add_parser("clear-queue", help="delete all isolated relation-pair queue records")

    subparsers.add_parser("self-check", help="run deterministic helper-script checks without spawning Codex")

    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        configure_consistency(mode=args.mode)

        if args.command == "run-cycle":
            return int(run_cycle(args))

        if args.command == "process-queue":
            return int(process_queue(args))

        if args.command == "enqueue":
            return int(enqueue_files(parse_enqueue_files(args)))

        if args.command == "progress":
            return int(report_progress(args.file))

        if args.command == "list-pairs":
            return int(list_pairs(args))

        if args.command == "mark-consistent":
            return int(mark_pair_status(args, check_status="consistent"))

        if args.command == "mark-inconsistent":
            return int(mark_pair_status(args, check_status="inconsistent"))

        if args.command == "mark-outdated":
            return int(mark_outdated())

        if args.command == "clear-queue":
            return int(clear_queue())

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
