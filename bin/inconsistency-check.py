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
``+consistency`` tag. Structured pair-operation history is stored separately
in ``.session/inconsistency-check/operations.jsonl``.
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
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path, PurePosixPath
from threading import Barrier, Lock
from types import SimpleNamespace
from typing import Any, Callable, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "consistency.toml"
TASKWARRIOR_BIN = "task"
VALID_CHECK_STATUSES = {"unchecked", "consistent", "inconsistent", "outdated"}
VALID_PAIR_OPERATIONS = {"queued", "dispatched", "checked", "marked", "status_changed"}


@dataclass(frozen=True)
class RelationConfig:
    description: str
    criteria: tuple[str, ...]


@dataclass(frozen=True)
class AgentConfig:
    cmd: tuple[str, ...]
    timeout_seconds: int
    prompt_template: str
    output_schema: dict[str, Any]


@dataclass(frozen=True)
class ConsistencyConfig:
    mode: str
    runtime_dir: Path
    comparison_base_refs: tuple[str, ...]
    allowed_file_relations: tuple[str, ...]
    requires_branch_change: bool
    agent_jobs: int
    discovery_jobs: int
    journal_cmd: tuple[str, ...] | None
    agent_validator: AgentConfig
    agent_reviewer: AgentConfig
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
    operation_log_path: Path


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
class PairOperation:
    occurred_at: str
    operation: str
    pair_key: str
    changed_path: str
    related_path: str
    relation: str
    previous_status: str
    next_status: str
    source: str


@dataclass(frozen=True)
class ListPairsOptions:
    multi_line: bool = False
    include_report: bool = False
    include_all_fields: bool = False
    current_only: bool = False
    statuses: tuple[str, ...] = ()
    include_count: bool = True


@dataclass(frozen=True)
class CurrentPair:
    pair: RelationPair
    identity: PairIdentity
    record: CheckRecord


@dataclass(frozen=True)
class QueueSyncResult:
    tracked_files: tuple[str, ...]
    current_pairs: tuple[CurrentPair, ...]
    graphs: DependencyGraphs
    checked_records: int
    marked_outdated_records: int


GraphComponent = tuple[str, ...]


@dataclass(frozen=True)
class DependencyGraphs:
    traversal_vertices: tuple[str, ...]
    traversal_edges: tuple[tuple[str, str], ...]
    scheduling_components: tuple[GraphComponent, ...]
    scheduling_edges: tuple[tuple[GraphComponent, GraphComponent], ...]
    cycles: tuple[tuple[str, ...], ...]
    ignored_self_edges: int


@dataclass(frozen=True)
class DependencyState:
    changed_files: tuple[str, ...]
    direct_pairs: tuple[RelationPair, ...]
    graphs: DependencyGraphs


@dataclass(frozen=True)
class FrontierSelection:
    component_statuses: tuple[tuple[GraphComponent, str], ...]
    frontier_components: tuple[GraphComponent, ...]
    resolved_files: tuple[str, ...]
    pending_files: tuple[str, ...]
    blocked_files: tuple[str, ...]
    deferred_inconsistencies: int


@dataclass(frozen=True)
class PairSelection:
    inconsistent: CurrentPair | None
    unchecked: CurrentPair | None


@dataclass(frozen=True)
class PreparedChildCheck:
    current_pair: CurrentPair
    agent_name: str
    agent_config: AgentConfig
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


def merge_config_tables(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)

    for key, value in override.items():
        existing = merged.get(key)

        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = merge_config_tables(existing, value)
        else:
            merged[key] = copy.deepcopy(value)

    return merged


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

        if "modes" in mode_config:
            raise CheckerFailureError("consistency.toml: mode override may not replace modes")

        resolved = merge_config_tables(resolved, mode_config)

    return selected_mode, resolved


def validate_output_schema(
    schema: dict[str, Any],
    *,
    context: str,
    status_property: str,
    allowed_statuses: set[str],
) -> None:
    if schema.get("type") != "object":
        raise CheckerFailureError(f"{context}.type must be object")

    required = schema.get("required")
    properties = schema.get("properties")

    if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
        raise CheckerFailureError(f"{context}.required must be a list of strings")

    if not isinstance(properties, dict):
        raise CheckerFailureError(f"{context}.properties must be a table")

    for key in (status_property, "report"):
        if key not in required or key not in properties:
            raise CheckerFailureError(f"{context} must require property {key!r}")

    status_schema = properties[status_property]
    report_schema = properties["report"]

    if not isinstance(status_schema, dict) or status_schema.get("type") != "string":
        raise CheckerFailureError(f"{context}.properties.{status_property}.type must be string")

    status_values = status_schema.get("enum")

    if (
        not isinstance(status_values, list)
        or any(not isinstance(value, str) for value in status_values)
        or set(status_values) != allowed_statuses
    ):
        expected = ", ".join(sorted(allowed_statuses))
        raise CheckerFailureError(f"{context}.properties.{status_property}.enum must contain: {expected}")

    if not isinstance(report_schema, dict) or report_schema.get("type") != "string":
        raise CheckerFailureError(f"{context}.properties.report.type must be string")


def validate_agent_config(
    config: dict[str, Any],
    *,
    key: str,
    status_property: str,
    allowed_statuses: set[str],
) -> AgentConfig:
    context = f"consistency.toml {key}"
    agent = require_table(config, key, context="consistency.toml")
    cmd = require_string_list(agent, "cmd", context=context)
    timeout_seconds = require_int(agent, "timeout_seconds", context=context)

    if timeout_seconds <= 0:
        raise CheckerFailureError(f"{context}.timeout_seconds must be positive")

    prompt = require_table(agent, "prompt", context=context)
    prompt_template = require_string(prompt, "template", context=f"{context} prompt")
    output_schema = copy.deepcopy(require_table(agent, "output_schema", context=context))
    validate_output_schema(
        output_schema,
        context=f"{context}.output_schema",
        status_property=status_property,
        allowed_statuses=allowed_statuses,
    )

    return AgentConfig(
        cmd=cmd,
        timeout_seconds=timeout_seconds,
        prompt_template=prompt_template,
        output_schema=output_schema,
    )


def validate_config(config: dict[str, Any], *, mode: str) -> ConsistencyConfig:
    version = config.get("version")

    if version != 2:
        raise CheckerFailureError("consistency.toml: version must be 2")

    runtime_dir = normalize_runtime_dir(require_string(config, "runtime_dir", context="consistency.toml"))
    comparison_base_refs = require_string_list(config, "comparison_base_refs", context="consistency.toml")
    allowed_file_relations = require_string_list(config, "allowed_file_relations", context="consistency.toml")
    requires_branch_change = require_bool(config, "requires_branch_change", context="consistency.toml")
    agent_jobs = require_int(config, "agent_jobs", context="consistency.toml")
    discovery_jobs = require_int(config, "discovery_jobs", context="consistency.toml")

    if agent_jobs <= 0:
        raise CheckerFailureError("consistency.toml: agent_jobs must be positive")

    if discovery_jobs <= 0:
        raise CheckerFailureError("consistency.toml: discovery_jobs must be positive")

    journal = require_table(config, "journal", context="consistency.toml")
    journal_cmd = (
        None
        if journal.get("cmd") is None
        else require_string_list(journal, "cmd", context="consistency.toml journal")
    )
    agent_validator = validate_agent_config(
        config,
        key="agent_validator",
        status_property="check_status",
        allowed_statuses={"consistent", "inconsistent"},
    )
    agent_reviewer = validate_agent_config(
        config,
        key="agent_reviewer",
        status_property="review_status",
        allowed_statuses={"confirmed", "rejected"},
    )

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
        requires_branch_change=requires_branch_change,
        agent_jobs=agent_jobs,
        discovery_jobs=discovery_jobs,
        journal_cmd=journal_cmd,
        agent_validator=agent_validator,
        agent_reviewer=agent_reviewer,
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
        operation_log_path=runtime_dir / "operations.jsonl",
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


def resolved_allowed_relations() -> tuple[DepmeshRelation, ...]:
    config = get_config()
    depmesh_relations = {relation.relation_id: relation for relation in load_depmesh_relations()}
    missing_depmesh_relations = sorted(set(config.allowed_file_relations) - set(depmesh_relations))

    if missing_depmesh_relations:
        raise CheckerFailureError(
            "configured allowed_file_relations not found in depmesh: "
            + ", ".join(missing_depmesh_relations)
        )

    return tuple(
        DepmeshRelation(
            relation_id=relation_id,
            description=config.relations[relation_id].description,
        )
        for relation_id in config.allowed_file_relations
    )


def query_depmesh_dependency_records(
    changed_path: str,
    relation: DepmeshRelation,
) -> list[dict[str, Any]]:
    return run_automation_jsonl(
        ["depmesh", "-p", "automation", "dependencies", "--relation", relation.relation_id, changed_path],
        failure_context=f"querying depmesh relation {relation.relation_id} for {changed_path}",
    )


def query_artifacts_pairs(
    changed_files: Iterable[str],
    relations: Iterable[DepmeshRelation],
    *,
    discovery_jobs: int,
    query_records: Callable[[str, DepmeshRelation], list[dict[str, Any]]] = query_depmesh_dependency_records,
) -> dict[str, list[RelationPair]]:
    if discovery_jobs <= 0:
        raise CheckerFailureError("discovery_jobs must be positive")

    changed_paths = tuple(sorted(set(changed_files)))
    ordered_relations = tuple(sorted(relations, key=lambda item: item.relation_id))
    queries = tuple(
        (changed_path, relation)
        for changed_path in changed_paths
        for relation in ordered_relations
    )
    pairs_by_artifact: dict[str, list[RelationPair]] = {changed_path: [] for changed_path in changed_paths}

    if not queries:
        return pairs_by_artifact

    worker_count = min(discovery_jobs, len(queries))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        records_by_query = {
            (changed_path, relation): executor.submit(
                query_records,
                changed_path,
                relation,
            )
            for changed_path, relation in queries
        }

        for changed_path, relation in queries:
            records = records_by_query[(changed_path, relation)].result()
            pairs = parse_depmesh_dependencies(records, changed_path=changed_path, relation=relation)
            log_project_journal(
                "step",
                f"depmesh query for {changed_path} relation {relation.relation_id} found {len(pairs)} related files",
            )
            pairs_by_artifact[changed_path].extend(pairs)

            for pair in pairs:
                log_project_journal(
                    "step",
                    (
                        "depmesh relation pair found "
                        f"{pair.changed_path} -> {pair.related_path} [{pair.relation}]"
                    ),
                )

    return {
        changed_path: sorted(
            {
                (pair.changed_path, pair.relation, pair.related_path): pair
                for pair in pairs
            }.values(),
            key=lambda pair: (pair.changed_path, pair.relation, pair.related_path),
        )
        for changed_path, pairs in sorted(pairs_by_artifact.items())
    }


def query_depmesh_pairs(changed_files: list[str]) -> list[RelationPair]:
    relations = resolved_allowed_relations()
    pair_map: dict[tuple[str, str, str], RelationPair] = {}
    pairs_by_artifact = query_artifacts_pairs(
        changed_files,
        relations,
        discovery_jobs=get_config().discovery_jobs,
    )

    for changed_path in sorted(changed_files):
        for pair in pairs_by_artifact[changed_path]:
            pair_map[(pair.changed_path, pair.relation, pair.related_path)] = pair

    return [pair_map[key] for key in sorted(pair_map)]


def strongly_connected_components(
    vertices: Iterable[str],
    edges: Iterable[tuple[str, str]],
) -> tuple[tuple[GraphComponent, ...], dict[str, GraphComponent]]:
    ordered_vertices = tuple(sorted(set(vertices)))
    adjacency = {vertex: [] for vertex in ordered_vertices}

    for source, target in sorted(set(edges)):
        adjacency[source].append(target)

    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[GraphComponent] = []

    def visit(vertex: str) -> None:
        nonlocal index
        indices[vertex] = index
        lowlinks[vertex] = index
        index += 1
        stack.append(vertex)
        on_stack.add(vertex)

        for target in adjacency[vertex]:
            if target not in indices:
                visit(target)
                lowlinks[vertex] = min(lowlinks[vertex], lowlinks[target])
            elif target in on_stack:
                lowlinks[vertex] = min(lowlinks[vertex], indices[target])

        if lowlinks[vertex] != indices[vertex]:
            return

        members: list[str] = []

        while True:
            member = stack.pop()
            on_stack.remove(member)
            members.append(member)

            if member == vertex:
                break

        components.append(tuple(sorted(members)))

    for vertex in ordered_vertices:
        if vertex not in indices:
            visit(vertex)

    ordered_components = tuple(sorted(components))
    component_by_artifact = {
        artifact: component
        for component in ordered_components
        for artifact in component
    }

    return ordered_components, component_by_artifact


def build_dependency_graphs(
    changed_files: Iterable[str],
    dependency_adjacency: dict[str, Iterable[str]],
) -> DependencyGraphs:
    changed_set = set(changed_files)
    vertices = set(changed_set)
    traversal_edges: set[tuple[str, str]] = set()
    ignored_self_edges = 0

    for queried_path in sorted(dependency_adjacency):
        vertices.add(queried_path)

        for related_path in sorted(set(dependency_adjacency[queried_path])):
            vertices.add(related_path)

            if related_path == queried_path:
                ignored_self_edges += 1
                continue

            traversal_edges.add((related_path, queried_path))

    components, component_by_artifact = strongly_connected_components(vertices, traversal_edges)
    component_edges: set[tuple[GraphComponent, GraphComponent]] = set()

    for source, target in traversal_edges:
        source_component = component_by_artifact[source]
        target_component = component_by_artifact[target]

        if source_component != target_component:
            component_edges.add((source_component, target_component))

    changed_components = tuple(
        sorted(
            tuple(sorted(changed_set.intersection(component)))
            for component in components
            if changed_set.intersection(component)
        )
    )
    changed_component_by_full_component = {
        component: tuple(sorted(changed_set.intersection(component)))
        for component in components
        if changed_set.intersection(component)
    }
    component_successors: dict[GraphComponent, set[GraphComponent]] = {
        component: set() for component in components
    }

    for source_component, target_component in component_edges:
        component_successors[source_component].add(target_component)

    scheduling_edges: set[tuple[GraphComponent, GraphComponent]] = set()

    for full_source, scheduling_source in sorted(changed_component_by_full_component.items()):
        pending = sorted(component_successors[full_source])
        visited: set[GraphComponent] = set()

        while pending:
            component = pending.pop(0)

            if component in visited:
                continue

            visited.add(component)
            scheduling_target = changed_component_by_full_component.get(component)

            if scheduling_target is not None:
                scheduling_edges.add((scheduling_source, scheduling_target))
                continue

            pending.extend(sorted(component_successors[component]))
            pending.sort()

    cycles = tuple(component for component in components if len(component) > 1)

    return DependencyGraphs(
        traversal_vertices=tuple(sorted(vertices)),
        traversal_edges=tuple(sorted(traversal_edges)),
        scheduling_components=changed_components,
        scheduling_edges=tuple(sorted(scheduling_edges)),
        cycles=cycles,
        ignored_self_edges=ignored_self_edges,
    )


def discover_dependency_state(changed_files: Iterable[str]) -> DependencyState:
    changed_paths = tuple(sorted(set(changed_files)))
    relations = resolved_allowed_relations()
    pending = list(changed_paths)
    visited: set[str] = set()
    dependency_adjacency: dict[str, tuple[str, ...]] = {}
    direct_pair_map: dict[tuple[str, str, str], RelationPair] = {}
    log_project_journal("step", "dependency graph construction started")

    while pending:
        wave = tuple(sorted(set(pending) - visited))
        pending = []

        if not wave:
            break

        visited.update(wave)
        pairs_by_artifact = query_artifacts_pairs(
            wave,
            relations,
            discovery_jobs=get_config().discovery_jobs,
        )
        next_wave: set[str] = set()

        for queried_path in wave:
            pairs = pairs_by_artifact[queried_path]
            dependencies = tuple(sorted({pair.related_path for pair in pairs}))
            dependency_adjacency[queried_path] = dependencies

            if queried_path in changed_paths:
                for pair in pairs:
                    direct_pair_map[(pair.changed_path, pair.relation, pair.related_path)] = pair

            next_wave.update(path for path in dependencies if path not in visited)

        pending = sorted(next_wave)

    graphs = build_dependency_graphs(changed_paths, dependency_adjacency)
    log_project_journal(
        "step",
        (
            "dependency graph construction completed "
            f"traversal-vertices:{len(graphs.traversal_vertices)} "
            f"traversal-edges:{len(graphs.traversal_edges)} "
            f"scheduling-vertices:{len(graphs.scheduling_components)} "
            f"scheduling-edges:{len(graphs.scheduling_edges)} "
            f"ignored-self-edges:{graphs.ignored_self_edges}"
        ),
    )

    for cycle in graphs.cycles:
        log_project_journal("thought", f"collapsed dependency cycle: {', '.join(cycle)}")

    return DependencyState(
        changed_files=changed_paths,
        direct_pairs=tuple(direct_pair_map[key] for key in sorted(direct_pair_map)),
        graphs=graphs,
    )


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

    journal_cmd = get_config().journal_cmd

    if journal_cmd is None:
        return

    clean_kind = single_line(kind)

    if not clean_kind or clean_kind != kind:
        raise CheckerFailureError(f"invalid journal kind: {kind!r}")

    command = render_command_argv(
        journal_cmd,
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


def pair_operation_values(record: PairOperation) -> dict[str, str]:
    return {
        "occurred_at": record.occurred_at,
        "operation": record.operation,
        "pair_key": record.pair_key,
        "changed_path": record.changed_path,
        "related_path": record.related_path,
        "relation": record.relation,
        "previous_status": record.previous_status,
        "next_status": record.next_status,
        "source": record.source,
    }


def raw_pair_operation(record: dict[str, Any], *, context: str) -> PairOperation:
    expected_fields = {
        "occurred_at",
        "operation",
        "pair_key",
        "changed_path",
        "related_path",
        "relation",
        "previous_status",
        "next_status",
        "source",
    }

    if set(record) != expected_fields:
        missing = ", ".join(sorted(expected_fields - set(record))) or "(none)"
        unexpected = ", ".join(sorted(set(record) - expected_fields)) or "(none)"
        raise CheckerFailureError(
            f"{context}: operation fields differ; missing: {missing}; unexpected: {unexpected}"
        )

    if any(not isinstance(record[field], str) for field in expected_fields):
        raise CheckerFailureError(f"{context}: every operation field must be a string")

    operation = PairOperation(
        occurred_at=record["occurred_at"],
        operation=record["operation"],
        pair_key=record["pair_key"],
        changed_path=record["changed_path"],
        related_path=record["related_path"],
        relation=record["relation"],
        previous_status=record["previous_status"],
        next_status=record["next_status"],
        source=record["source"],
    )

    if operation.operation not in VALID_PAIR_OPERATIONS:
        raise CheckerFailureError(f"{context}: unsupported operation: {operation.operation!r}")

    if operation.previous_status and operation.previous_status not in VALID_CHECK_STATUSES:
        raise CheckerFailureError(f"{context}: unsupported previous status: {operation.previous_status!r}")

    if operation.next_status not in VALID_CHECK_STATUSES:
        raise CheckerFailureError(f"{context}: unsupported next status: {operation.next_status!r}")

    required_values = {
        "occurred_at": operation.occurred_at,
        "pair_key": operation.pair_key,
        "changed_path": operation.changed_path,
        "related_path": operation.related_path,
        "relation": operation.relation,
        "source": operation.source,
    }

    for field, value in required_values.items():
        if not value or single_line(value) != value:
            raise CheckerFailureError(f"{context}: {field} must be a non-empty single-line string")

    return operation


def append_pair_operation_record(path: Path, record: PairOperation) -> None:
    raw_pair_operation(pair_operation_values(record), context="writing pair operation")
    serialized = json.dumps(pair_operation_values(record), separators=(",", ":"), sort_keys=True) + "\n"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("a", encoding="utf-8") as operation_log:
            operation_log.write(serialized)
    except OSError as error:
        raise CheckerFailureError(f"writing pair-operation log failed: {path}: {error}") from error


def record_pair_operation(
    identity: PairIdentity,
    *,
    operation: str,
    previous_status: str,
    next_status: str,
    source: str,
) -> None:
    record = PairOperation(
        occurred_at=utc_timestamp(),
        operation=operation,
        pair_key=identity.pair_key,
        changed_path=identity.changed_path,
        related_path=identity.related_path,
        relation=identity.relation,
        previous_status=previous_status,
        next_status=next_status,
        source=source,
    )
    append_pair_operation_record(runtime_paths().operation_log_path, record)


def load_pair_operations(path: Path, *, last: int) -> list[PairOperation]:
    if last <= 0:
        raise CheckerFailureError("list-operations --last must be positive")

    if not path.is_file():
        return []

    recent_operations: deque[PairOperation] = deque(maxlen=last)

    try:
        with path.open(encoding="utf-8") as operation_log:
            for line_number, line in enumerate(operation_log, start=1):
                if not line.strip():
                    continue

                try:
                    raw_record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise CheckerFailureError(
                        f"reading pair-operation log: invalid JSON on line {line_number}: {error}"
                    ) from error

                if not isinstance(raw_record, dict):
                    raise CheckerFailureError(
                        f"reading pair-operation log: JSON line {line_number} is not an object"
                    )

                recent_operations.append(
                    raw_pair_operation(raw_record, context=f"reading pair-operation log line {line_number}")
                )
    except OSError as error:
        raise CheckerFailureError(f"reading pair-operation log failed: {path}: {error}") from error

    return list(recent_operations)


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


def load_allowed_check_records() -> list[CheckRecord]:
    allowed_relations = set(get_config().allowed_file_relations)

    return [
        raw_record_to_check_record(record)
        for record in load_taskwarrior_records()
        if record.get("pair_key") and record.get("relation") in allowed_relations
    ]


def load_allowed_check_records_read_only() -> list[CheckRecord]:
    paths = runtime_paths()

    if not paths.taskrc_path.is_file() or not paths.task_data_dir.is_dir():
        return []

    result = run_command(
        task_command_args("export"),
        check=True,
        failure_context="exporting isolated inconsistency-check Taskwarrior records read-only",
    )

    try:
        records = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as error:
        raise CheckerFailureError(f"invalid Taskwarrior export JSON: {error}") from error

    if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
        raise CheckerFailureError("Taskwarrior export did not return a JSON object list")

    allowed_relations = set(get_config().allowed_file_relations)

    return [
        raw_record_to_check_record(record)
        for record in records
        if record.get("pair_key") and record.get("relation") in allowed_relations
    ]


def virtual_unchecked_record(identity: PairIdentity) -> CheckRecord:
    return CheckRecord(
        uuid="",
        pair_key=identity.pair_key,
        file_pair=identity.file_pair,
        changed_path=identity.changed_path,
        related_path=identity.related_path,
        relation=identity.relation,
        checksum_changed=identity.checksum_changed,
        checksum_related=identity.checksum_related,
        check_status="unchecked",
        report="",
        checked_at="",
    )


def current_pairs_read_only(
    pairs: Iterable[RelationPair],
    records: Iterable[CheckRecord],
) -> list[CurrentPair]:
    records_by_key: dict[str, CheckRecord] = {}

    for record in records:
        if record.pair_key in records_by_key:
            raise CheckerFailureError("isolated Taskwarrior DB has duplicate pair_key records")

        records_by_key[record.pair_key] = record

    current_pairs: list[CurrentPair] = []

    for pair in sorted(pairs, key=lambda item: (item.changed_path, item.relation, item.related_path)):
        try:
            identity = build_pair_identity(pair)
        except MissingArtifactError:
            continue

        record = records_by_key.get(identity.pair_key)
        matching_record = (
            record is not None
            and record.checksum_changed == identity.checksum_changed
            and record.checksum_related == identity.checksum_related
            and normalized_check_status(record) != "outdated"
        )
        current_pairs.append(
            CurrentPair(
                pair=pair,
                identity=identity,
                record=record if matching_record and record is not None else virtual_unchecked_record(identity),
            )
        )

    return current_pairs


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


def upsert_unchecked_record(
    identity: PairIdentity,
    records_by_pair_key: dict[str, CheckRecord],
) -> CheckRecord:
    existing = records_by_pair_key.get(identity.pair_key)

    if existing is None:
        record = write_task_record(identity, uuid=None, check_status="unchecked", report="", checked_at="")
        records_by_pair_key[identity.pair_key] = record
        record_pair_operation(
            identity,
            operation="queued",
            previous_status="",
            next_status=record.check_status or "unchecked",
            source="queue",
        )
        log_pair_queued(identity, record.check_status or "unchecked")

        return record

    existing_status = existing.check_status or "unchecked"
    should_reset_outdated = existing_status == "outdated"

    if not should_reset_outdated:
        return existing

    record = write_task_record(
        identity,
        uuid=existing.uuid,
        check_status="unchecked",
        report="",
        checked_at="",
    )
    records_by_pair_key[identity.pair_key] = record

    record_pair_operation(
        identity,
        operation="status_changed",
        previous_status="outdated",
        next_status="unchecked",
        source="reconciliation",
    )
    log_pair_state_change(identity, "outdated", "unchecked")

    return record


def update_check_record(
    identity: PairIdentity,
    *,
    check_status: str,
    report: str,
    checked_at: str,
    operation: str,
    source: str,
) -> CheckRecord:
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
    record_pair_operation(
        identity,
        operation=operation,
        previous_status=previous_status,
        next_status=check_status,
        source=source,
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
    record_pair_operation(
        identity,
        operation="status_changed",
        previous_status=record.check_status or "unchecked",
        next_status="outdated",
        source="reconciliation",
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


def mark_superseded_pair_versions(identity: PairIdentity, records: Iterable[CheckRecord]) -> int:
    marked_count = 0

    for record in records:
        same_oriented_pair = (
            record.changed_path == identity.changed_path
            and record.related_path == identity.related_path
            and record.relation == identity.relation
        )

        if not same_oriented_pair or record.pair_key == identity.pair_key:
            continue

        if normalized_check_status(record) == "outdated":
            continue

        mark_record_outdated(
            record,
            f"superseded by current relation-pair checksums: {identity.pair_key}",
        )
        marked_count += 1

    return marked_count


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
    if check_status not in {"unchecked", "consistent", "inconsistent"}:
        raise CheckerFailureError(f"unsupported explicit check status: {check_status}")

    identity = build_pair_identity(pair)
    existing_records = load_allowed_check_records()
    upsert_unchecked_record(identity, {record.pair_key: record for record in existing_records})
    normalized_report = "" if check_status == "unchecked" else normalize_explicit_report(check_status, report)
    checked_at = "" if check_status == "unchecked" else utc_timestamp()
    record = update_check_record(
        identity,
        check_status=check_status,
        report=normalized_report,
        checked_at=checked_at,
        operation="marked",
        source="explicit-command",
    )
    log_project_journal(
        "step",
        f"explicit pair status set for {pair_journal_subject(identity)}: {check_status}",
    )

    return CurrentPair(pair=pair, identity=identity, record=record)


def reconcile_queue(pairs: list[RelationPair]) -> list[CurrentPair]:
    current_pairs: list[CurrentPair] = []
    existing_records = load_allowed_check_records()
    records_by_pair_key = {record.pair_key: record for record in existing_records}
    skipped_missing = 0
    superseded_records = 0

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

        record = upsert_unchecked_record(identity, records_by_pair_key)
        superseded_records += mark_superseded_pair_versions(identity, existing_records)
        current_pairs.append(CurrentPair(pair=pair, identity=identity, record=record))

    if skipped_missing:
        log_project_journal("step", f"queue reconciliation skipped {skipped_missing} missing-file pair records")

    if superseded_records:
        log_project_journal(
            "step",
            f"queue reconciliation marked {superseded_records} superseded pair records outdated",
        )

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


def artifact_statuses(
    changed_files: Iterable[str],
    current_pairs: Iterable[CurrentPair],
) -> dict[str, str]:
    statuses_by_artifact: dict[str, list[str]] = {path: [] for path in changed_files}

    for current_pair in current_pairs:
        if current_pair.pair.changed_path not in statuses_by_artifact:
            continue

        status = normalized_check_status(current_pair.record)

        if status == "outdated":
            status = "unchecked"

        statuses_by_artifact[current_pair.pair.changed_path].append(status)

    result: dict[str, str] = {}

    for artifact, statuses in statuses_by_artifact.items():
        if "inconsistent" in statuses:
            result[artifact] = "inconsistent"
        elif "unchecked" in statuses:
            result[artifact] = "unchecked"
        elif statuses:
            result[artifact] = "resolved"
        else:
            result[artifact] = "resolved-without-pairs"

    return result


def select_frontier(
    graphs: DependencyGraphs,
    current_pairs: Iterable[CurrentPair],
) -> FrontierSelection:
    current_pairs = list(current_pairs)
    changed_files = tuple(sorted(path for component in graphs.scheduling_components for path in component))
    statuses_by_artifact = artifact_statuses(changed_files, current_pairs)
    component_statuses: dict[GraphComponent, str] = {}

    for component in graphs.scheduling_components:
        member_statuses = [statuses_by_artifact[path] for path in component]

        if "inconsistent" in member_statuses:
            component_statuses[component] = "inconsistent"
        elif "unchecked" in member_statuses:
            component_statuses[component] = "unchecked"
        else:
            component_statuses[component] = "resolved"

    predecessors: dict[GraphComponent, set[GraphComponent]] = {
        component: set() for component in graphs.scheduling_components
    }

    for source, target in graphs.scheduling_edges:
        predecessors[target].add(source)

    def all_predecessors(component: GraphComponent) -> set[GraphComponent]:
        result: set[GraphComponent] = set()
        pending = sorted(predecessors[component])

        while pending:
            predecessor = pending.pop(0)

            if predecessor in result:
                continue

            result.add(predecessor)
            pending.extend(sorted(predecessors[predecessor]))
            pending.sort()

        return result

    pending_components = {
        component
        for component, status in component_statuses.items()
        if status in {"unchecked", "inconsistent"}
    }
    frontier_components = tuple(
        sorted(
            component
            for component in pending_components
            if all(component_statuses[predecessor] == "resolved" for predecessor in all_predecessors(component))
        )
    )

    if pending_components and not frontier_components:
        pending_text = ", ".join(path for component in sorted(pending_components) for path in component)
        raise CheckerFailureError(f"pending dependency components have no selectable frontier: {pending_text}")

    frontier_files = {path for component in frontier_components for path in component}
    resolved_files = tuple(
        sorted(path for path, status in statuses_by_artifact.items() if status.startswith("resolved"))
    )
    pending_files = tuple(
        sorted(path for path, status in statuses_by_artifact.items() if status in {"unchecked", "inconsistent"})
    )
    blocked_files = tuple(sorted(set(pending_files) - frontier_files))
    deferred_inconsistencies = sum(
        1
        for current_pair in current_pairs
        if current_pair.pair.changed_path not in frontier_files
        and normalized_check_status(current_pair.record) == "inconsistent"
    )

    return FrontierSelection(
        component_statuses=tuple(sorted(component_statuses.items())),
        frontier_components=frontier_components,
        resolved_files=resolved_files,
        pending_files=pending_files,
        blocked_files=blocked_files,
        deferred_inconsistencies=deferred_inconsistencies,
    )


def frontier_files(selection: FrontierSelection) -> tuple[str, ...]:
    return tuple(sorted({path for component in selection.frontier_components for path in component}))


def build_frontier_report(changed_files: Iterable[str], selection: FrontierSelection) -> str:
    changed_files = tuple(changed_files)
    selected_files = frontier_files(selection)
    lines = [
        "Current frontier",
        f"changed files: {len(changed_files)}",
        f"frontier files: {len(selected_files)}",
    ]
    lines.extend(f"- {selected_file}" for selected_file in selected_files)

    return "\n".join(lines)


def ordered_frontier_pairs(
    selection: FrontierSelection,
    current_pairs: Iterable[CurrentPair],
) -> list[CurrentPair]:
    component_index = {
        path: index
        for index, component in enumerate(selection.frontier_components)
        for path in component
    }

    return sorted(
        (
            current_pair
            for current_pair in current_pairs
            if current_pair.pair.changed_path in component_index
        ),
        key=lambda current_pair: (
            component_index[current_pair.pair.changed_path],
            *current_pair_sort_key(current_pair),
        ),
    )


def first_frontier_pair_with_status(
    frontier_pairs: Iterable[CurrentPair],
    status: str,
    *,
    excluded_pair_keys: set[str] | None = None,
) -> CurrentPair | None:
    excluded_pair_keys = excluded_pair_keys or set()

    for current_pair in frontier_pairs:
        if current_pair.identity.pair_key in excluded_pair_keys:
            continue

        if normalized_check_status(current_pair.record) == status:
            return current_pair

    return None


def next_frontier_candidate(
    frontier_pairs: Iterable[CurrentPair],
    running_pair_keys: set[str],
    *,
    agent_jobs: int,
    stop_launching: bool,
) -> CurrentPair | None:
    if stop_launching or len(running_pair_keys) >= agent_jobs:
        return None

    return first_frontier_pair_with_status(
        frontier_pairs,
        "unchecked",
        excluded_pair_keys=running_pair_keys,
    )


def completed_frontier_exit_code(
    frontier_pairs: Iterable[CurrentPair],
    *,
    launched_child: bool,
    stale_found: bool,
) -> ExitCode:
    if stale_found:
        return ExitCode.CONTINUE_CYCLE

    if first_frontier_pair_with_status(frontier_pairs, "inconsistent") is not None:
        return ExitCode.INCONSISTENCY_FOUND

    if launched_child:
        return ExitCode.CONTINUE_CYCLE

    raise CheckerFailureError("pending frontier completed without a child launch or workflow outcome")


def print_frontier_summary(
    tracked_files: Iterable[str],
    current_pairs: list[CurrentPair],
    selection: FrontierSelection,
    *,
    fresh_cycle_required: bool,
) -> None:
    counts = status_counts(current_pairs)
    print("Consistency frontier summary")
    print(f"tracked artifacts: {len(tuple(tracked_files))}")
    print(f"resolved artifacts: {len(selection.resolved_files)}")
    print(f"pending artifacts: {len(selection.pending_files)}")
    print(f"blocked artifacts: {len(selection.blocked_files)}")
    print(f"active frontier artifacts: {len(frontier_files(selection))}")
    print(f"consistent pairs: {counts.get('consistent', 0)}")
    print(f"inconsistent pairs: {counts.get('inconsistent', 0)}")
    print(f"unchecked pairs: {counts.get('unchecked', 0)}")
    print(f"fresh cycle required: {'yes' if fresh_cycle_required else 'no'}")


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


def build_child_prompt(
    current_pair: CurrentPair,
    agent_config: AgentConfig,
    *,
    validator_report: str = "",
) -> str:
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
        "mode": get_config().mode,
        "validation": SimpleNamespace(report=validator_report),
        "criteria": criteria,
        "fenced_content": fenced_content,
        "sha256_file": sha256_file,
    }

    return render_expression_template(agent_config.prompt_template, context)


def prepare_child_check(
    current_pair: CurrentPair,
    *,
    agent_name: str,
    agent_config: AgentConfig,
    validator_report: str = "",
) -> PreparedChildCheck:
    ensure_runtime_state()
    paths = runtime_paths()
    key_hash = identity_hash(current_pair.identity)
    prompt_path = paths.prompt_dir / f"{key_hash}.{agent_name}.md"
    schema_path = paths.schema_dir / f"{key_hash}.{agent_name}.schema.json"
    output_path = paths.agent_output_dir / f"{key_hash}.{agent_name}.json"
    prompt = build_child_prompt(
        current_pair,
        agent_config,
        validator_report=validator_report,
    )
    output_path.unlink(missing_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    schema_path.write_text(json.dumps(agent_config.output_schema, indent=2, sort_keys=True), encoding="utf-8")

    return PreparedChildCheck(
        current_pair=current_pair,
        agent_name=agent_name,
        agent_config=agent_config,
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
                f"running {prepared.agent_name} child Codex checker for "
                f"{pair_journal_subject(prepared.current_pair.identity)}: "
                f"timed out after {prepared.agent_config.timeout_seconds} seconds: "
                f"{format_argv(running.argv)}"
            )

        time.sleep(0.1)

    return finish_child_checker(running)


def start_child_checker(prepared: PreparedChildCheck) -> RunningChildCheck:
    pair_subject = pair_journal_subject(prepared.current_pair.identity)
    log_project_journal("step", f"{prepared.agent_name} child checker start for {pair_subject}")
    command = render_command_argv(
        prepared.agent_config.cmd,
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
            f"running {prepared.agent_name} child Codex checker for "
            f"{pair_subject}: {format_argv(command)}: {error}"
        ) from error

    running = RunningChildCheck(
        prepared=prepared,
        argv=command,
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        started_at=time.monotonic(),
    )

    if process.stdin is None:
        kill_running_child(running)
        raise CheckerFailureError(
            f"{prepared.agent_name} child Codex checker stdin was unavailable for {pair_subject}"
        )

    try:
        process.stdin.write(prepared.prompt)
        process.stdin.close()
    except OSError as error:
        kill_running_child(running)
        raise CheckerFailureError(
            f"writing {prepared.agent_name} child Codex checker prompt failed for {pair_subject}: {error}"
        ) from error

    status = normalized_check_status(prepared.current_pair.record)

    try:
        record_pair_operation(
            prepared.current_pair.identity,
            operation="dispatched",
            previous_status=status,
            next_status=status,
            source=prepared.agent_name,
        )
    except CheckerFailureError:
        kill_running_child(running)
        raise

    return running


def child_checker_timed_out(running: RunningChildCheck) -> bool:
    return time.monotonic() - running.started_at > running.prepared.agent_config.timeout_seconds


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
        raise CheckerFailureError(
            build_command_failure(f"{running.prepared.agent_name} child Codex checker failed", result)
        )

    if not running.prepared.output_path.exists():
        raise CheckerFailureError(
            f"{running.prepared.agent_name} child Codex checker did not write output file: "
            f"{running.prepared.output_path}"
        )

    output = running.prepared.output_path.read_text(encoding="utf-8")
    log_project_journal(
        "step",
        f"{running.prepared.agent_name} child checker completed for {pair_subject}",
    )

    return output


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def local_timestamp(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp).astimezone().isoformat()


def malformed_child_error(agent_name: str, reason: str, output: str) -> CheckerFailureError:
    details = "\n\n".join(
        [
            f"{agent_name} child checker output was malformed: {reason}",
            fenced_content("Raw child checker output", output),
        ]
    )

    return CheckerFailureError(details)


def validate_child_result(
    output: str,
    *,
    agent_name: str,
    agent_config: AgentConfig,
    status_property: str,
    allowed_statuses: set[str],
    heading_required_statuses: set[str],
) -> tuple[str, str]:
    try:
        result = json.loads(output)
    except json.JSONDecodeError as error:
        raise malformed_child_error(agent_name, str(error), output) from error

    if not isinstance(result, dict):
        raise malformed_child_error(agent_name, "output JSON is not an object", output)

    output_schema = agent_config.output_schema
    properties = output_schema.get("properties", {})
    allowed_keys = set(properties) if isinstance(properties, dict) else {status_property, "report"}
    extra_keys = sorted(set(result) - allowed_keys)

    if output_schema.get("additionalProperties") is False and extra_keys:
        raise malformed_child_error(agent_name, f"unexpected keys: {', '.join(extra_keys)}", output)

    required = output_schema.get("required", [])
    missing_keys = sorted(key for key in required if isinstance(key, str) and key not in result)

    if missing_keys:
        raise malformed_child_error(agent_name, f"missing required keys: {', '.join(missing_keys)}", output)

    if isinstance(properties, dict):
        for key, property_schema in properties.items():
            if key not in result or not isinstance(property_schema, dict):
                continue

            if property_schema.get("type") == "string" and not isinstance(result[key], str):
                raise malformed_child_error(agent_name, f"{key} must be a string", output)

            allowed_values = property_schema.get("enum")

            if isinstance(allowed_values, list) and result[key] not in allowed_values:
                raise malformed_child_error(
                    agent_name,
                    f"{key} must be one of: {', '.join(str(value) for value in allowed_values)}",
                    output,
                )

    status = result.get(status_property)
    report = result.get("report")

    if status not in allowed_statuses:
        expected = " or ".join(sorted(allowed_statuses))
        raise malformed_child_error(agent_name, f"{status_property} must be {expected}", output)

    if not isinstance(report, str):
        raise malformed_child_error(agent_name, "report must be a string", output)

    if status in heading_required_statuses and not any(line.startswith("## ") for line in report.splitlines()):
        raise malformed_child_error(
            agent_name,
            f"{status_property}={status!r} reports must contain at least one ## section",
            output,
        )

    return status, report


def update_record_from_decision(
    current_pair: CurrentPair,
    *,
    check_status: str,
    report: str,
    decision_source: str,
) -> CurrentPair:
    record = update_check_record(
        current_pair.identity,
        check_status=check_status,
        report=report,
        checked_at=utc_timestamp(),
        operation="checked",
        source=decision_source,
    )
    log_project_journal(
        "step",
        (
            f"pair status update from {decision_source} for "
            f"{pair_journal_subject(current_pair.identity)}: {check_status}"
        ),
    )

    return CurrentPair(pair=current_pair.pair, identity=current_pair.identity, record=record)


def reviewed_report(
    *,
    review_status: str,
    validator_report: str,
    reviewer_report: str,
) -> str:
    decision = "confirmed" if review_status == "confirmed" else "rejected"

    return "\n\n".join(
        [
            f"## Reviewer {decision} the validator candidate",
            reviewer_report.strip(),
            "## Validator candidate report",
            validator_report.strip(),
        ]
    ).strip()


def update_record_from_reviewer_output(
    current_pair: CurrentPair,
    *,
    validator_report: str,
    reviewer_output: str,
) -> CurrentPair:
    config = get_config()
    review_status, reviewer_report = validate_child_result(
        reviewer_output,
        agent_name="reviewer",
        agent_config=config.agent_reviewer,
        status_property="review_status",
        allowed_statuses={"confirmed", "rejected"},
        heading_required_statuses={"confirmed", "rejected"},
    )
    check_status = "inconsistent" if review_status == "confirmed" else "consistent"

    return update_record_from_decision(
        current_pair,
        check_status=check_status,
        report=reviewed_report(
            review_status=review_status,
            validator_report=validator_report,
            reviewer_report=reviewer_report,
        ),
        decision_source="reviewer",
    )


def update_record_from_validator_output(current_pair: CurrentPair, output: str) -> CurrentPair:
    config = get_config()
    check_status, validator_report = validate_child_result(
        output,
        agent_name="validator",
        agent_config=config.agent_validator,
        status_property="check_status",
        allowed_statuses={"consistent", "inconsistent"},
        heading_required_statuses={"inconsistent"},
    )

    if check_status == "consistent":
        return update_record_from_decision(
            current_pair,
            check_status="consistent",
            report=validator_report,
            decision_source="validator",
        )

    prepared_reviewer = prepare_child_check(
        current_pair,
        agent_name="reviewer",
        agent_config=config.agent_reviewer,
        validator_report=validator_report,
    )
    reviewer_output = run_child_checker(prepared_reviewer)
    stale_reason = record_outdated_reason(current_pair.record)

    if stale_reason is not None:
        record = mark_record_outdated_during_processing(
            current_pair.record,
            f"pair changed during reviewer adjudication: {stale_reason}",
        )
        return CurrentPair(pair=current_pair.pair, identity=current_pair.identity, record=record)

    return update_record_from_reviewer_output(
        current_pair,
        validator_report=validator_report,
        reviewer_output=reviewer_output,
    )


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
                f"running {timed_out_child.prepared.agent_name} child Codex checker for "
                f"{pair_journal_subject(timed_out_child.prepared.current_pair.identity)}: "
                f"timed out after {timed_out_child.prepared.agent_config.timeout_seconds} seconds: "
                f"{format_argv(timed_out_child.argv)}"
            )

        time.sleep(0.1)


def terminate_running_children(running: dict[str, RunningChildCheck]) -> None:
    for child in running.values():
        kill_running_child(child)


def process_current_frontier(
    tracked_files: list[str],
    current_pairs: list[CurrentPair],
    graphs: DependencyGraphs,
    *,
    command_name: str,
    agent_jobs: int,
) -> ExitCode:
    selection = select_frontier(graphs, current_pairs)
    selected_files = frontier_files(selection)
    frontier_pairs = ordered_frontier_pairs(selection, current_pairs)
    unchecked_job_count = sum(
        normalized_check_status(current_pair.record) == "unchecked" for current_pair in frontier_pairs
    )
    log_project_journal(
        "step",
        f"{command_name} selected frontier artifacts: {', '.join(selected_files) or '(none)'}",
    )
    log_project_journal("step", f"{command_name} frontier pair-job count:{unchecked_job_count}")
    log_project_journal(
        "step",
        f"{command_name} deferred non-frontier inconsistencies:{selection.deferred_inconsistencies}",
    )

    inconsistent_pair = first_frontier_pair_with_status(frontier_pairs, "inconsistent")

    if inconsistent_pair is not None:
        print_inconsistent_pair(inconsistent_pair)
        log_project_journal("step", f"{command_name} outcome: current frontier inconsistency found")
        return ExitCode.INCONSISTENCY_FOUND

    if not selection.frontier_components:
        print_frontier_summary(tracked_files, current_pairs, selection, fresh_cycle_required=False)
        log_project_journal("step", f"{command_name} outcome: success after fresh no-work cycle")
        return ExitCode.SUCCESS

    running: dict[str, RunningChildCheck] = {}
    inconsistency_found = False
    stale_found = False
    launched_child = False
    log_project_journal("step", f"{command_name} processing with agent-jobs:{agent_jobs}")

    try:
        while True:
            while True:
                unchecked_pair = next_frontier_candidate(
                    frontier_pairs,
                    set(running),
                    agent_jobs=agent_jobs,
                    stop_launching=inconsistency_found or stale_found,
                )

                if unchecked_pair is None:
                    break

                checked_pair = mark_current_pair_outdated_if_needed(unchecked_pair)

                if normalized_check_status(checked_pair.record) == "outdated":
                    current_pairs = replace_current_pair(current_pairs, checked_pair)
                    frontier_pairs = replace_current_pair(frontier_pairs, checked_pair)
                    stale_found = True
                    log_project_journal(
                        "step",
                        (
                            f"{command_name} stale frontier detected before launch: "
                            f"{pair_journal_subject(checked_pair.identity)}"
                        ),
                    )
                    break

                try:
                    prepared = prepare_child_check(
                        checked_pair,
                        agent_name="validator",
                        agent_config=get_config().agent_validator,
                    )
                except MissingArtifactError as error:
                    updated_record = mark_record_outdated_during_processing(
                        checked_pair.record,
                        f"file is missing before child check: {error.path}",
                    )
                    current_pairs = replace_current_pair(
                        current_pairs,
                        CurrentPair(pair=checked_pair.pair, identity=checked_pair.identity, record=updated_record),
                    )
                    frontier_pairs = replace_current_pair(
                        frontier_pairs,
                        CurrentPair(pair=checked_pair.pair, identity=checked_pair.identity, record=updated_record),
                    )
                    stale_found = True
                    log_project_journal("step", f"{command_name} stale frontier detected before launch")
                    break
                except OutdatedPairError as error:
                    updated_record = mark_record_outdated_during_processing(checked_pair.record, error.reason)
                    current_pairs = replace_current_pair(
                        current_pairs,
                        CurrentPair(pair=checked_pair.pair, identity=checked_pair.identity, record=updated_record),
                    )
                    frontier_pairs = replace_current_pair(
                        frontier_pairs,
                        CurrentPair(pair=checked_pair.pair, identity=checked_pair.identity, record=updated_record),
                    )
                    stale_found = True
                    log_project_journal("step", f"{command_name} stale frontier detected before launch")
                    break

                running[checked_pair.identity.pair_key] = start_child_checker(prepared)
                launched_child = True

            if not running:
                outcome = completed_frontier_exit_code(
                    frontier_pairs,
                    launched_child=launched_child,
                    stale_found=stale_found,
                )

                if outcome == ExitCode.CONTINUE_CYCLE and stale_found:
                    current_selection = select_frontier(graphs, current_pairs)
                    print_frontier_summary(tracked_files, current_pairs, current_selection, fresh_cycle_required=True)
                    log_project_journal("step", f"{command_name} outcome: stale frontier requires rediscovery")
                    return outcome

                if outcome == ExitCode.INCONSISTENCY_FOUND:
                    inconsistent_pair = first_frontier_pair_with_status(frontier_pairs, "inconsistent")

                    if inconsistent_pair is None:
                        raise CheckerFailureError("frontier inconsistency outcome has no inconsistent pair")

                    print_inconsistent_pair(inconsistent_pair)
                    log_project_journal("step", f"{command_name} outcome: frontier child found inconsistency")
                    return outcome

                if outcome == ExitCode.CONTINUE_CYCLE:
                    current_selection = select_frontier(graphs, current_pairs)
                    print_frontier_summary(tracked_files, current_pairs, current_selection, fresh_cycle_required=True)
                    log_project_journal("step", f"{command_name} frontier completed; fresh cycle required")
                    log_project_journal("step", f"{command_name} outcome: continue after successful frontier")
                    return outcome

                raise CheckerFailureError(f"{command_name} produced unsupported frontier outcome: {outcome}")

            for finished_child in wait_for_finished_children(running):
                pair_key = finished_child.prepared.current_pair.identity.pair_key
                running.pop(pair_key)
                child_output = finish_child_checker(finished_child)
                finished_pair = finished_child.prepared.current_pair
                stale_reason = record_outdated_reason(finished_pair.record)

                if stale_reason is not None:
                    updated_record = mark_record_outdated_during_processing(finished_pair.record, stale_reason)
                    updated_pair = CurrentPair(
                        pair=finished_pair.pair,
                        identity=finished_pair.identity,
                        record=updated_record,
                    )
                    stale_found = True
                    log_project_journal(
                        "step",
                        (
                            f"{command_name} stale frontier detected after child completion: "
                            f"{pair_journal_subject(finished_pair.identity)}"
                        ),
                    )
                else:
                    updated_pair = update_record_from_validator_output(finished_pair, child_output)

                current_pairs = replace_current_pair(current_pairs, updated_pair)
                frontier_pairs = replace_current_pair(frontier_pairs, updated_pair)

                updated_status = normalized_check_status(updated_pair.record)

                if updated_status == "inconsistent":
                    inconsistency_found = True
                elif updated_status == "outdated":
                    stale_found = True
    except CheckerFailureError:
        terminate_running_children(running)
        raise


def effective_agent_jobs(args: argparse.Namespace) -> int:
    agent_jobs = (
        args.agent_jobs
        if getattr(args, "agent_jobs", None) is not None
        else get_config().agent_jobs
    )

    if agent_jobs <= 0:
        raise CheckerFailureError("agent_jobs must be positive")

    return agent_jobs


def reconcile_direct_changed_files() -> tuple[list[str], list[CurrentPair]]:
    changed_files = discover_changed_files()
    current_pairs = reconcile_queue(query_depmesh_pairs(changed_files))

    return changed_files, current_pairs


def existing_file_artifacts(paths: Iterable[str]) -> list[str]:
    return sorted(
        path
        for path in set(paths)
        if artifact_to_filesystem_path(path).is_file()
    )


def tracked_artifacts_for_mode(
    changed_files: Iterable[str],
    records: Iterable[CheckRecord],
    *,
    requires_branch_change: bool,
) -> tuple[str, ...]:
    tracked_files = set(changed_files)

    if not requires_branch_change:
        tracked_files.update(
            record.changed_path
            for record in records
            if normalized_check_status(record) != "outdated"
        )

    return tuple(sorted(tracked_files))


def current_pair_keys_for_records(records: Iterable[CheckRecord]) -> set[str]:
    records = list(records)
    changed_paths = existing_file_artifacts(record.changed_path for record in records)

    if not changed_paths:
        return set()

    relation_pairs = query_depmesh_pairs(changed_paths)
    current_pair_keys: set[str] = set()

    for pair in relation_pairs:
        try:
            current_pair_keys.add(build_pair_identity(pair).pair_key)
        except MissingArtifactError:
            continue

    return current_pair_keys


def filter_current_records(records: Iterable[CheckRecord], current_pair_keys: set[str]) -> list[CheckRecord]:
    return [record for record in records if record.pair_key in current_pair_keys]


def mark_records_outside_current_pairs(
    records: Iterable[CheckRecord],
    current_pair_keys: set[str],
    *,
    branch_changed_paths: set[str] | None = None,
) -> tuple[int, int]:
    checked_count = 0
    marked_count = 0

    for record in records:
        if normalized_check_status(record) == "outdated":
            continue

        checked_count += 1

        if record.pair_key in current_pair_keys:
            continue

        reason = (
            (
                f"changed file is outside the branch diff required by mode {get_config().mode!r}"
            )
            if (
                get_config().requires_branch_change
                and branch_changed_paths is not None
                and record.changed_path not in branch_changed_paths
            )
            else record_outdated_reason(record)
        )

        if reason is None:
            reason = "relation pair is no longer returned by current depmesh relations"

        mark_record_outdated(record, reason)
        marked_count += 1

    return checked_count, marked_count


def synchronize_queue_state() -> QueueSyncResult:
    changed_files = discover_changed_files()
    queued_records = load_allowed_check_records()
    tracked_files = existing_file_artifacts(
        tracked_artifacts_for_mode(
            changed_files,
            queued_records,
            requires_branch_change=get_config().requires_branch_change,
        )
    )
    dependency_state = discover_dependency_state(tracked_files)
    current_pairs = reconcile_queue(list(dependency_state.direct_pairs))
    current_pair_keys = {current_pair.identity.pair_key for current_pair in current_pairs}
    checked_records, marked_outdated_records = mark_records_outside_current_pairs(
        load_allowed_check_records(),
        current_pair_keys,
        branch_changed_paths=set(changed_files),
    )

    return QueueSyncResult(
        tracked_files=tuple(tracked_files),
        current_pairs=tuple(current_pairs),
        graphs=dependency_state.graphs,
        checked_records=checked_records,
        marked_outdated_records=marked_outdated_records,
    )


def print_sync_summary(result: QueueSyncResult) -> None:
    counts = status_counts(list(result.current_pairs))
    print("Queue synchronization summary")
    print(f"tracked files: {len(result.tracked_files)}")
    print(f"current relation pairs: {len(result.current_pairs)}")
    print(f"consistent pairs: {counts.get('consistent', 0)}")
    print(f"inconsistent pairs: {counts.get('inconsistent', 0)}")
    print(f"unchecked pairs: {counts.get('unchecked', 0)}")
    print(f"records checked for currentness: {result.checked_records}")
    print(f"records marked outdated: {result.marked_outdated_records}")

    if result.tracked_files:
        print("tracked file list:")

        for tracked_file in result.tracked_files:
            print(f"- {tracked_file}")


def sync_queue() -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "sync-queue command started")
    result = synchronize_queue_state()
    print_sync_summary(result)
    log_project_journal(
        "step",
        (
            "sync-queue command completed "
            f"current:{len(result.current_pairs)} marked-outdated:{result.marked_outdated_records}"
        ),
    )

    return ExitCode.SUCCESS


def enqueue_changed() -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "enqueue-changed command started")
    changed_files, current_pairs = reconcile_direct_changed_files()
    print_summary(changed_files, current_pairs)
    log_project_journal("step", "enqueue-changed outcome: queue reconciled without processing")

    return ExitCode.SUCCESS


def run_cycle(args: argparse.Namespace) -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "run-cycle command started")
    result = synchronize_queue_state()

    return process_current_frontier(
        list(result.tracked_files),
        list(result.current_pairs),
        result.graphs,
        command_name="run-cycle",
        agent_jobs=effective_agent_jobs(args),
    )


def show_frontier() -> ExitCode:
    log_project_journal("step", "frontier diagnostic command started")
    changed_files = discover_changed_files()
    queued_records = load_allowed_check_records_read_only()
    tracked_files = existing_file_artifacts(
        tracked_artifacts_for_mode(
            changed_files,
            queued_records,
            requires_branch_change=get_config().requires_branch_change,
        )
    )
    dependency_state = discover_dependency_state(tracked_files)
    current_pairs = current_pairs_read_only(
        dependency_state.direct_pairs,
        queued_records,
    )
    selection = select_frontier(dependency_state.graphs, current_pairs)
    selected_files = frontier_files(selection)
    print(build_frontier_report(changed_files, selection))

    log_project_journal("step", f"frontier diagnostic selected-file count:{len(selected_files)}")
    log_project_journal("step", "frontier diagnostic outcome: success")

    return ExitCode.SUCCESS


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
    records = [mark_record_outdated_if_needed(record) for record in load_allowed_check_records()]
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
    result = synchronize_queue_state()

    return process_current_frontier(
        list(result.tracked_files),
        list(result.current_pairs),
        result.graphs,
        command_name="process-queue",
        agent_jobs=effective_agent_jobs(args),
    )


def mark_outdated_records() -> tuple[int, int]:
    checked_count = 0
    marked_count = 0
    for record in load_allowed_check_records():
        checked_count += 1
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


def load_list_pair_records(
    statuses: Iterable[str] = (),
    *,
    current_only: bool = False,
) -> list[CheckRecord]:
    status_filter = set(statuses)
    records = load_allowed_check_records()

    if current_only:
        records = filter_current_records(records, current_pair_keys_for_records(records))

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
    records = load_list_pair_records(options.statuses, current_only=options.current_only)
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
        current_only=bool(args.current),
        statuses=tuple(args.statuses or ()),
        include_count=not bool(args.no_count),
    )
    log_project_journal(
        "step",
        (
            f"list-pairs command started statuses:{','.join(options.statuses) or 'all'} "
            f"current-only:{options.current_only}"
        ),
    )
    report = build_list_pairs_report(options)

    if report:
        print(report)

    return ExitCode.SUCCESS


def build_pair_operations_report(operations: Iterable[PairOperation]) -> str:
    operation_records = list(operations)
    headers = [
        "occurred at",
        "operation",
        "previous status",
        "next status",
        "source",
        "changed file",
        "relation",
        "related file",
    ]
    operation_rows = [
        [
            local_timestamp(record.occurred_at),
            record.operation,
            record.previous_status or "(none)",
            record.next_status,
            record.source,
            record.changed_path,
            record.relation,
            record.related_path,
        ]
        for record in operation_records
    ]
    table_rows = [headers, *operation_rows]
    column_widths = [
        max(len(value) for value in column)
        for column in zip(*table_rows, strict=True)
    ]
    lines = [
        " | ".join(
            value.ljust(width)
            for value, width in zip(row, column_widths, strict=True)
        )
        for row in table_rows
    ]
    lines.insert(1, " | ".join("-" * width for width in column_widths))

    if lines:
        lines.append("")

    lines.append(f"operations: {len(operation_records)}")

    return "\n".join(lines)


def list_operations(args: argparse.Namespace) -> ExitCode:
    ensure_runtime_state()
    last = int(args.last)
    log_project_journal("step", f"list-operations command started last:{last}")
    operations = load_pair_operations(runtime_paths().operation_log_path, last=last)
    print(build_pair_operations_report(operations))

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
        report=getattr(args, "report", None),
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

    if previous_status != "unchecked":
        record_pair_operation(
            identity,
            operation="status_changed",
            previous_status=previous_status,
            next_status="unchecked",
            source="self-check",
        )

    log_pair_state_change(identity, previous_status, "unchecked")


def runtime_artifact_path(*parts: str) -> str:
    return f"@/{(get_config().runtime_dir / Path(*parts)).as_posix()}"


def self_check_child_output(
    agent_config: AgentConfig,
    *,
    status_property: str,
    status: str,
    report: str,
) -> str:
    payload: dict[str, Any] = {
        status_property: status,
        "report": report,
    }
    output_schema = agent_config.output_schema
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


def synthetic_current_pair(
    changed_path: str,
    *,
    status: str,
    relation: str = "synthetic-relation",
    related_path: str | None = None,
) -> CurrentPair:
    related_path = related_path or f"@/validation/{changed_path.removeprefix('@/')}"
    checksum_changed = f"checksum:{changed_path}"
    checksum_related = f"checksum:{related_path}"
    file_pair = f"<{changed_path}|{checksum_changed}>:<{related_path}|{checksum_related}>"
    identity = PairIdentity(
        pair_key=f"{relation}|{file_pair}",
        file_pair=file_pair,
        changed_path=changed_path,
        related_path=related_path,
        relation=relation,
        checksum_changed=checksum_changed,
        checksum_related=checksum_related,
    )
    pair = RelationPair(
        changed_path=changed_path,
        related_path=related_path,
        relation=relation,
        relation_description="Synthetic self-check relation",
    )
    record = CheckRecord(
        uuid="synthetic",
        pair_key=identity.pair_key,
        file_pair=file_pair,
        changed_path=changed_path,
        related_path=related_path,
        relation=relation,
        checksum_changed=checksum_changed,
        checksum_related=checksum_related,
        check_status=status,
        report="## Synthetic inconsistency" if status == "inconsistent" else "",
        checked_at="",
    )

    return CurrentPair(pair=pair, identity=identity, record=record)


def run_dependency_scheduler_self_checks() -> None:
    root = "@/changed/root"
    middle = "@/changed/middle"
    leaf = "@/changed/leaf"
    chain_graph = build_dependency_graphs(
        [leaf, root, middle],
        {leaf: [middle], root: [], middle: [root]},
    )
    chain_pairs = [
        synthetic_current_pair(path, status="unchecked")
        for path in [leaf, root, middle]
    ]
    chain_selection = select_frontier(chain_graph, chain_pairs)
    assert_self_check(frontier_files(chain_selection) == (root,), "simple chain must select only its root")

    advanced_pairs = [
        synthetic_current_pair(root, status="consistent"),
        synthetic_current_pair(middle, status="unchecked"),
        synthetic_current_pair(leaf, status="unchecked"),
    ]
    assert_self_check(
        frontier_files(select_frontier(chain_graph, advanced_pairs)) == (middle,),
        "a resolved root must advance the next cycle to the middle",
    )

    independent = "@/changed/independent"
    independent_graph = build_dependency_graphs([root, independent], {root: [], independent: []})
    independent_pairs = [
        synthetic_current_pair(root, status="unchecked"),
        synthetic_current_pair(independent, status="unchecked"),
    ]
    assert_self_check(
        frontier_files(select_frontier(independent_graph, independent_pairs)) == tuple(sorted((root, independent))),
        "independent roots must share a frontier",
    )

    left = "@/changed/left"
    right = "@/changed/right"
    descendant = "@/changed/descendant"
    diamond_graph = build_dependency_graphs(
        [descendant, left, right],
        {descendant: [right, left], left: [], right: []},
    )
    diamond_pairs = [
        synthetic_current_pair(left, status="consistent"),
        synthetic_current_pair(right, status="unchecked"),
        synthetic_current_pair(descendant, status="unchecked"),
    ]
    assert_self_check(
        frontier_files(select_frontier(diamond_graph, diamond_pairs)) == (right,),
        "a diamond descendant must wait for both parents",
    )

    intermediary = "@/unchanged/intermediary"
    intermediary_graph = build_dependency_graphs(
        [root, leaf],
        {root: [], intermediary: [root], leaf: [intermediary]},
    )
    assert_self_check(
        intermediary_graph.scheduling_edges == (((root,), (leaf,)),),
        "unchanged intermediaries must contract into derived scheduling edges",
    )
    assert_self_check(
        intermediary not in {path for component in intermediary_graph.scheduling_components for path in component},
        "unchanged intermediaries must not become scheduling work",
    )

    unchanged_upstream_graph = build_dependency_graphs(
        [leaf],
        {intermediary: [], leaf: [intermediary]},
    )
    assert_self_check(
        frontier_files(
            select_frontier(
                unchanged_upstream_graph,
                [synthetic_current_pair(leaf, status="unchecked")],
            )
        )
        == (leaf,),
        "an unchanged upstream dependency must not block the first changed descendant",
    )

    self_edge_graph = build_dependency_graphs([root], {root: [root]})
    assert_self_check(self_edge_graph.ignored_self_edges == 1, "self-edges must be counted and ignored")
    assert_self_check(
        frontier_files(select_frontier(self_edge_graph, [synthetic_current_pair(root, status="unchecked")]))
        == (root,),
        "a self-edge must not deadlock frontier selection",
    )

    cycle_a = "@/changed/cycle-a"
    cycle_b = "@/changed/cycle-b"
    cycle_graph = build_dependency_graphs(
        [cycle_b, cycle_a],
        {cycle_a: [cycle_b], cycle_b: [cycle_a]},
    )
    cycle_selection = select_frontier(
        cycle_graph,
        [
            synthetic_current_pair(cycle_b, status="unchecked"),
            synthetic_current_pair(cycle_a, status="unchecked"),
        ],
    )
    assert_self_check(
        cycle_graph.scheduling_components == ((cycle_a, cycle_b),),
        "changed cycle members must collapse into one scheduling component",
    )
    assert_self_check(
        frontier_files(cycle_selection) == (cycle_a, cycle_b),
        "cycle members must be scheduled atomically and reported lexically",
    )
    cycle_report = build_frontier_report([cycle_b, cycle_a], cycle_selection)
    assert_self_check(
        cycle_report.splitlines()[-2:] == [f"- {cycle_a}", f"- {cycle_b}"],
        "frontier output must flatten cycle members into unique lexical paths",
    )

    deferred_pairs = [
        synthetic_current_pair(root, status="unchecked"),
        synthetic_current_pair(middle, status="consistent"),
        synthetic_current_pair(leaf, status="inconsistent"),
    ]
    deferred_selection = select_frontier(chain_graph, deferred_pairs)
    assert_self_check(
        frontier_files(deferred_selection) == (root,) and deferred_selection.deferred_inconsistencies == 1,
        (
            "a descendant inconsistency must be deferred behind its pending predecessor "
            f"frontier={frontier_files(deferred_selection)} "
            f"deferred={deferred_selection.deferred_inconsistencies}"
        ),
    )

    frontier_inconsistent_pairs = [
        synthetic_current_pair(root, status="inconsistent"),
        synthetic_current_pair(middle, status="unchecked"),
        synthetic_current_pair(leaf, status="unchecked"),
    ]
    frontier_inconsistent_selection = select_frontier(chain_graph, frontier_inconsistent_pairs)
    frontier_pair_set = [
        pair
        for pair in frontier_inconsistent_pairs
        if pair.pair.changed_path in set(frontier_files(frontier_inconsistent_selection))
    ]
    assert_self_check(
        first_inconsistent_pair(frontier_pair_set) is not None,
        "an existing frontier inconsistency must be found before a child launch",
    )

    cycle_order_a = "@/changed/a-cycle"
    cycle_order_z = "@/changed/z-cycle"
    independent_order_b = "@/changed/b-independent"
    component_order_graph = build_dependency_graphs(
        [cycle_order_a, cycle_order_z, independent_order_b],
        {
            cycle_order_a: [cycle_order_z],
            cycle_order_z: [cycle_order_a],
            independent_order_b: [],
        },
    )
    component_order_pairs = [
        synthetic_current_pair(cycle_order_a, status="consistent"),
        synthetic_current_pair(cycle_order_z, status="inconsistent"),
        synthetic_current_pair(independent_order_b, status="inconsistent"),
    ]
    component_order_selection = select_frontier(component_order_graph, component_order_pairs)
    ordered_pairs = ordered_frontier_pairs(component_order_selection, component_order_pairs)
    first_component_inconsistency = first_frontier_pair_with_status(ordered_pairs, "inconsistent")
    assert_self_check(
        first_component_inconsistency is not None
        and first_component_inconsistency.pair.changed_path == cycle_order_z,
        "frontier inconsistency order must prioritize component order before artifact path",
    )

    concurrency_candidates = sorted(independent_pairs, key=current_pair_sort_key)
    first_batch = concurrency_candidates[: get_config().agent_jobs]
    assert_self_check(
        len(first_batch) <= get_config().agent_jobs,
        "frontier concurrency must not exceed the resolved agent_jobs value",
    )
    assert_self_check(
        next_frontier_candidate(
            concurrency_candidates,
            {concurrency_candidates[0].identity.pair_key},
            agent_jobs=1,
            stop_launching=False,
        )
        is None,
        "the scheduler must not launch above its resolved concurrency limit",
    )
    assert_self_check(
        next_frontier_candidate(
            concurrency_candidates,
            set(),
            agent_jobs=get_config().agent_jobs,
            stop_launching=True,
        )
        is None,
        "an inconsistency or stale result must stop later frontier launches",
    )
    assert_self_check(
        root in frontier_files(chain_selection) and middle not in frontier_files(chain_selection),
        "a descendant must not cross the invocation frontier boundary",
    )

    no_pair_graph = build_dependency_graphs([root, leaf], {root: [], leaf: [root]})
    no_pair_selection = select_frontier(
        no_pair_graph,
        [synthetic_current_pair(leaf, status="unchecked")],
    )
    assert_self_check(
        frontier_files(no_pair_selection) == (leaf,),
        "a changed artifact without validation pairs must be resolved for scheduling",
    )
    all_resolved_selection = select_frontier(
        chain_graph,
        [synthetic_current_pair(path, status="consistent") for path in [leaf, middle, root]],
    )
    assert_self_check(
        not frontier_files(all_resolved_selection),
        "a fresh all-resolved pass must have no frontier",
    )
    assert_self_check(
        build_frontier_report([leaf, middle, root], all_resolved_selection).endswith("frontier files: 0"),
        "an empty frontier report must succeed without path entries",
    )
    deferred_report = build_frontier_report([leaf, middle, root], deferred_selection)
    assert_self_check(
        f"- {leaf}" not in deferred_report,
        "frontier output must omit blocked descendants",
    )
    completed_pairs = [synthetic_current_pair(root, status="consistent")]
    assert_self_check(
        completed_frontier_exit_code(completed_pairs, launched_child=True, stale_found=False)
        == ExitCode.CONTINUE_CYCLE,
        "a successful frontier must require one fresh cycle",
    )
    assert_self_check(
        completed_frontier_exit_code(
            [synthetic_current_pair(root, status="inconsistent")],
            launched_child=True,
            stale_found=False,
        )
        == ExitCode.INCONSISTENCY_FOUND,
        "a valid frontier inconsistency must return the repair exit code",
    )
    assert_self_check(
        completed_frontier_exit_code(
            [synthetic_current_pair(root, status="inconsistent")],
            launched_child=True,
            stale_found=True,
        )
        == ExitCode.CONTINUE_CYCLE,
        "stale frontier work must force rediscovery before reporting a concurrent inconsistency",
    )

    shuffled_graph = build_dependency_graphs(
        [middle, leaf, root],
        {middle: [root], leaf: [middle], root: []},
    )
    shuffled_pairs = list(reversed(chain_pairs))
    assert_self_check(shuffled_graph == chain_graph, "shuffled graph inputs must be deterministic")
    assert_self_check(
        frontier_files(select_frontier(shuffled_graph, shuffled_pairs)) == frontier_files(chain_selection),
        "shuffled queue inputs must select the same frontier",
    )

    configured_relation_ids = get_config().allowed_file_relations
    assert_self_check(configured_relation_ids, "the resolved allowed relation list must not be empty")
    assert_self_check(
        all(relation_id in get_config().relations for relation_id in configured_relation_ids),
        "every mode-resolved allowed relation must have config-defined criteria",
    )
    synthetic_relations = ["synthetic-alpha", "synthetic-beta"]
    synthetic_relation_pairs = [
        synthetic_current_pair(root, status="unchecked", relation=relation_id, related_path=intermediary)
        for relation_id in synthetic_relations
    ]
    synthetic_adjacency = {
        root: sorted({pair.pair.related_path for pair in synthetic_relation_pairs}),
        intermediary: [],
    }
    assert_self_check(
        build_dependency_graphs([root], synthetic_adjacency).traversal_edges == ((intermediary, root),),
        "synthetic configured relation ids must contribute uniformly to one deduplicated graph edge",
    )

    discovery_relation = DepmeshRelation(
        relation_id="synthetic-discovery",
        description="Synthetic parallel discovery relation",
    )
    discovery_paths = ("@/discovery/a", "@/discovery/b")
    discovery_barrier = Barrier(len(discovery_paths))
    discovery_lock = Lock()
    active_discovery_queries = 0
    maximum_discovery_queries = 0

    def synthetic_discovery_query(
        changed_path: str,
        relation: DepmeshRelation,
    ) -> list[dict[str, Any]]:
        nonlocal active_discovery_queries, maximum_discovery_queries

        with discovery_lock:
            active_discovery_queries += 1
            maximum_discovery_queries = max(maximum_discovery_queries, active_discovery_queries)

        try:
            discovery_barrier.wait(timeout=2)
        finally:
            with discovery_lock:
                active_discovery_queries -= 1

        return [
            {
                "type": "dependency",
                "relation": relation.relation_id,
                "dependency": f"@/dependency/{changed_path.removeprefix('@/').replace('/', '-')}",
            }
        ]

    parallel_discovery_pairs = query_artifacts_pairs(
        reversed(discovery_paths),
        [discovery_relation],
        discovery_jobs=len(discovery_paths),
        query_records=synthetic_discovery_query,
    )
    assert_self_check(
        maximum_discovery_queries == len(discovery_paths),
        "depmesh discovery must execute concurrently up to discovery_jobs",
    )

    def deterministic_discovery_query(
        changed_path: str,
        relation: DepmeshRelation,
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": "dependency",
                "relation": relation.relation_id,
                "dependency": f"@/dependency/{changed_path.removeprefix('@/').replace('/', '-')}",
            }
        ]

    sequential_discovery_pairs = query_artifacts_pairs(
        discovery_paths,
        [discovery_relation],
        discovery_jobs=1,
        query_records=deterministic_discovery_query,
    )
    assert_self_check(
        parallel_discovery_pairs == sequential_discovery_pairs,
        "parallel depmesh discovery must preserve deterministic pair results",
    )


def run_self_check() -> ExitCode:
    ensure_runtime_state()
    log_project_journal("step", "self-check command started")

    mode_configs: dict[str, ConsistencyConfig] = {}

    for mode_id in load_configured_mode_ids():
        mode_config = load_consistency_config(mode=mode_id)
        mode_configs[mode_id] = mode_config
        assert_self_check(mode_config.mode == mode_id, f"configured mode {mode_id!r} must load")
        assert_self_check(
            bool(mode_config.agent_validator.cmd),
            f"configured mode {mode_id!r} must inherit the validator command",
        )
        assert_self_check(
            bool(mode_config.agent_reviewer.cmd),
            f"configured mode {mode_id!r} must inherit the reviewer command",
        )

    assert_self_check(
        mode_configs["incremental"].requires_branch_change,
        "incremental mode must require the pair's changed file to be changed in the branch",
    )
    assert_self_check(
        not mode_configs["strict"].requires_branch_change,
        "strict mode must retain queued pairs whose changed file is outside the branch diff",
    )

    active_config = get_config()
    assert_self_check(
        bool(active_config.allowed_file_relations),
        "allowed relations must load from config without a source-code relation allowlist",
    )
    assert_self_check(active_config.agent_jobs > 0, "agent_jobs must load from config")
    assert_self_check(active_config.discovery_jobs > 0, "discovery_jobs must load from config")
    assert_self_check(
        active_config.agent_validator.timeout_seconds > 0,
        "validator timeout must load from config",
    )
    assert_self_check(
        active_config.agent_reviewer.timeout_seconds > 0,
        "reviewer timeout must load from config",
    )
    allowed_relation = active_config.allowed_file_relations[0]
    assert_self_check(
        bool(relation_specific_criteria(allowed_relation)),
        "configured relation criteria must load from config",
    )
    branch_changed_path = "@/self-check/branch-changed.py"
    queued_path = "@/self-check/queued.py"
    outdated_path = "@/self-check/outdated.py"
    queued_record = synthetic_current_pair(queued_path, status="unchecked").record
    outdated_record = synthetic_current_pair(outdated_path, status="outdated").record
    assert_self_check(
        tracked_artifacts_for_mode(
            [branch_changed_path],
            [queued_record, outdated_record],
            requires_branch_change=True,
        )
        == (branch_changed_path,),
        "branch-scoped modes must exclude queued pairs whose changed file is outside the branch diff",
    )
    assert_self_check(
        tracked_artifacts_for_mode(
            [branch_changed_path],
            [queued_record, outdated_record],
            requires_branch_change=False,
        )
        == tuple(sorted((branch_changed_path, queued_path))),
        "non-branch-scoped modes must process every non-outdated queued pair",
    )
    run_dependency_scheduler_self_checks()
    changed_files = discover_changed_files()
    assert_self_check(all(path.startswith("@/") for path in changed_files), "changed files must be artifact ids")

    paths = runtime_paths()
    self_check_operation_log = paths.self_check_dir / "operations.jsonl"
    self_check_operation_log.unlink(missing_ok=True)
    self_check_operations = (
        PairOperation(
            occurred_at="2026-01-01T00:00:00+00:00",
            operation="queued",
            pair_key="self-check-operation-1",
            changed_path="@/self-check/operation-changed.py",
            related_path="@/self-check/operation-related.md",
            relation=allowed_relation,
            previous_status="",
            next_status="unchecked",
            source="queue",
        ),
        PairOperation(
            occurred_at="2026-01-01T00:00:01+00:00",
            operation="marked",
            pair_key="self-check-operation-1",
            changed_path="@/self-check/operation-changed.py",
            related_path="@/self-check/operation-related.md",
            relation=allowed_relation,
            previous_status="unchecked",
            next_status="inconsistent",
            source="explicit-command",
        ),
        PairOperation(
            occurred_at="2026-01-01T00:00:02+00:00",
            operation="dispatched",
            pair_key="self-check-operation-2",
            changed_path="@/self-check/second-operation-changed.py",
            related_path="@/self-check/second-operation-related.md",
            relation=allowed_relation,
            previous_status="unchecked",
            next_status="unchecked",
            source="reviewer",
        ),
        PairOperation(
            occurred_at="2026-01-01T00:00:03+00:00",
            operation="checked",
            pair_key="self-check-operation-2",
            changed_path="@/self-check/second-operation-changed.py",
            related_path="@/self-check/second-operation-related.md",
            relation=allowed_relation,
            previous_status="unchecked",
            next_status="consistent",
            source="validator",
        ),
        PairOperation(
            occurred_at="2026-01-01T00:00:04+00:00",
            operation="status_changed",
            pair_key="self-check-operation-2",
            changed_path="@/self-check/second-operation-changed.py",
            related_path="@/self-check/second-operation-related.md",
            relation=allowed_relation,
            previous_status="consistent",
            next_status="outdated",
            source="reconciliation",
        ),
    )

    for operation_record in self_check_operations:
        append_pair_operation_record(self_check_operation_log, operation_record)

    recent_self_check_operations = load_pair_operations(self_check_operation_log, last=4)
    assert_self_check(
        recent_self_check_operations == list(self_check_operations[-3:]),
        "operation log must retain the requested tail in chronological order",
    )
    operation_report = build_pair_operations_report(recent_self_check_operations)
    report_lines = operation_report.splitlines()
    rendered_header_columns = report_lines[0].split(" | ")
    separator_columns = report_lines[1].split(" | ")
    header_columns = [value.strip() for value in rendered_header_columns]
    operation_lines = report_lines[2 : len(recent_self_check_operations) + 2]
    operation_columns = [line.split(" | ") for line in operation_lines]
    table_columns = [rendered_header_columns, *operation_columns]
    assert_self_check(
        header_columns
        == [
            "occurred at",
            "operation",
            "previous status",
            "next status",
            "source",
            "changed file",
            "relation",
            "related file",
        ],
        "operation report must show the expected column headers",
    )
    assert_self_check(
        all(
            separator == "-" * len(header)
            for separator, header in zip(separator_columns, rendered_header_columns, strict=True)
        ),
        "operation report must separate its header from its body with a width-aligned line",
    )
    assert_self_check(
        operation_columns[0][0] == local_timestamp("2026-01-01T00:00:01+00:00")
        and operation_columns[0][1].strip() == "marked"
        and operation_columns[0][2].strip() == "unchecked"
        and operation_columns[0][3].strip() == "inconsistent",
        "operation report must show time, operation, previous status, and next status separately",
    )
    assert_self_check(
        operation_columns[0][5].strip() == "@/self-check/operation-changed.py"
        and operation_columns[0][6].strip() == allowed_relation
        and operation_columns[0][7].strip() == "@/self-check/operation-related.md",
        "operation report must show changed file, relation, and related file separately",
    )
    assert_self_check(
        operation_columns[1][1].strip() == "dispatched"
        and operation_columns[1][2].strip() == "unchecked"
        and operation_columns[1][3].strip() == "unchecked"
        and operation_columns[1][4].strip() == "reviewer",
        "operation report must show a same-status agent dispatch",
    )
    assert_self_check(
        all(
            len({len(columns[column_index]) for columns in table_columns}) == 1
            for column_index in range(len(header_columns))
        ),
        "operation report columns must use widths derived from the headers and selected operations",
    )
    assert_self_check(
        operation_report.endswith("operations: 4"),
        "operation report must show the selected operation count",
    )
    self_check_operation_log.write_text("{not json}\n", encoding="utf-8")

    try:
        load_pair_operations(self_check_operation_log, last=1)
    except CheckerFailureError as error:
        malformed_operation_error = str(error)
    else:
        raise CheckerFailureError("self-check failed: malformed operation JSON must fail")

    assert_self_check(
        "invalid JSON on line 1" in malformed_operation_error,
        "malformed operation JSON must identify its line",
    )
    self_check_operation_log.unlink(missing_ok=True)
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
    records_before_read_only = load_allowed_check_records_read_only()
    child_runtime_files_before = tuple(
        sorted(
            path.relative_to(paths.runtime_dir).as_posix()
            for directory in [paths.agent_output_dir, paths.prompt_dir, paths.schema_dir]
            for path in directory.rglob("*")
            if path.is_file()
        )
    )
    read_only_pairs = current_pairs_read_only([pair, second_pair], [current_pairs[0].record])
    records_after_read_only = load_allowed_check_records_read_only()
    child_runtime_files_after = tuple(
        sorted(
            path.relative_to(paths.runtime_dir).as_posix()
            for directory in [paths.agent_output_dir, paths.prompt_dir, paths.schema_dir]
            for path in directory.rglob("*")
            if path.is_file()
        )
    )
    virtual_pair = next(item for item in read_only_pairs if item.identity.pair_key == second_identity.pair_key)
    assert_self_check(
        virtual_pair.record.check_status == "unchecked" and not virtual_pair.record.uuid,
        "a current pair missing from the queue must be virtual unchecked",
    )
    assert_self_check(
        records_before_read_only == records_after_read_only,
        "read-only current-pair derivation must not mutate queue records",
    )
    assert_self_check(
        child_runtime_files_before == child_runtime_files_after,
        "read-only frontier derivation must not create child-runtime artifacts",
    )
    read_only_graph = build_dependency_graphs([changed_path], {changed_path: []})
    assert_self_check(
        frontier_files(select_frontier(read_only_graph, read_only_pairs)) == (changed_path,),
        "read-only frontier selection must match reconciled unchecked status",
    )
    prepared_validator = prepare_child_check(
        current_pairs[0],
        agent_name="validator",
        agent_config=active_config.agent_validator,
    )
    validator_report = "## Candidate inconsistency\n\nSynthetic validator finding."
    prepared_reviewer = prepare_child_check(
        current_pairs[0],
        agent_name="reviewer",
        agent_config=active_config.agent_reviewer,
        validator_report=validator_report,
    )
    serialized_schema = json.loads(prepared_validator.schema_path.read_text(encoding="utf-8"))
    rendered_agent_cmd = render_command_argv(
        active_config.agent_validator.cmd,
        {
            "project_root": str(PROJECT_ROOT),
            "prompt_path": str(prepared_validator.prompt_path),
            "schema_path": str(prepared_validator.schema_path),
            "output_path": str(prepared_validator.output_path),
        },
    )
    changed_snapshot, _related_snapshot = read_pair_snapshots(pair)
    advanced_render = render_expression_template(
        "{fenced_content('Self-check file', changed.text)}",
        {"fenced_content": fenced_content, "changed": SimpleNamespace(text=changed_snapshot.text)},
    )
    assert_self_check(
        serialized_schema == active_config.agent_validator.output_schema,
        "validator output schema must serialize from config",
    )
    assert_self_check(
        str(prepared_validator.schema_path) in rendered_agent_cmd,
        "validator schema path must render",
    )
    assert_self_check(
        prepared_validator.output_path != prepared_reviewer.output_path,
        "validator and reviewer runtime artifacts must not collide",
    )
    assert_self_check(
        validator_report in prepared_reviewer.prompt,
        "reviewer prompt must contain the validator candidate report",
    )
    assert_self_check("Self-check file" in advanced_render, "prompt renderer must support function calls")
    assert_self_check(
        "changed self-check content" not in prepared_validator.prompt,
        "validator prompt must not embed full file contents",
    )
    assert_self_check(
        "changed self-check content" not in prepared_reviewer.prompt,
        "reviewer prompt must not embed full file contents",
    )
    missing_pairs = reconcile_queue([missing_pair])
    assert_self_check(not missing_pairs, "missing-file pairs must be skipped")
    selection = select_current_pair(current_pairs)
    assert_self_check(selection.unchecked is not None, "one unchecked pair must be selected")
    assert_self_check(selection.inconsistent is None, "unchecked selection must not report inconsistency")
    consistent_pair = update_record_from_validator_output(
        selection.unchecked,
        self_check_child_output(
            active_config.agent_validator,
            status_property="check_status",
            status="consistent",
            report="",
        ),
    )
    current_pairs = replace_current_pair(current_pairs, consistent_pair)
    assert_self_check(
        has_unchecked_pair(current_pairs),
        "one processed pair must leave later unchecked pairs for exit 20",
    )
    preserved_raw_record_before = find_raw_record_by_pair_key(load_taskwarrior_records(), consistent_pair.identity.pair_key)
    preserved_pairs = reconcile_queue([pair, second_pair])
    preserved_raw_record_after = find_raw_record_by_pair_key(load_taskwarrior_records(), consistent_pair.identity.pair_key)
    preserved_record = next(
        item.record for item in preserved_pairs if item.identity.pair_key == consistent_pair.identity.pair_key
    )
    assert_self_check(preserved_record.check_status == "consistent", "unchanged pair key must preserve cached status")
    assert_self_check(
        preserved_raw_record_before == preserved_raw_record_after,
        "unchanged pair reconciliation must not rewrite its Taskwarrior record",
    )
    inconsistent_pair = update_record_from_reviewer_output(
        consistent_pair,
        validator_report=validator_report,
        reviewer_output=self_check_child_output(
            active_config.agent_reviewer,
            status_property="review_status",
            status="confirmed",
            report="## Review rationale\n\nThe candidate is valid.",
        ),
    )
    current_pairs = replace_current_pair(preserved_pairs, inconsistent_pair)
    inconsistent_selection = select_current_pair(current_pairs)
    assert_self_check(
        inconsistent_selection.inconsistent is not None,
        "current inconsistency must be selected before any child check",
    )
    assert_self_check(
        validator_report in inconsistent_pair.record.report,
        "confirmed reviewer result must retain the validator report",
    )
    rejected_pair = update_record_from_reviewer_output(
        current_pairs[1],
        validator_report=validator_report,
        reviewer_output=self_check_child_output(
            active_config.agent_reviewer,
            status_property="review_status",
            status="rejected",
            report="## Review rationale\n\nThe candidate is a false positive.",
        ),
    )
    assert_self_check(
        rejected_pair.record.check_status == "consistent",
        "a rejected validator candidate must be stored as consistent",
    )
    assert_self_check(
        validator_report in rejected_pair.record.report,
        "rejected reviewer result must retain the validator report",
    )

    try:
        validate_child_result(
            "{not json",
            agent_name="validator",
            agent_config=active_config.agent_validator,
            status_property="check_status",
            allowed_statuses={"consistent", "inconsistent"},
            heading_required_statuses={"inconsistent"},
        )
    except CheckerFailureError as error:
        malformed_error = str(error)
    else:
        raise CheckerFailureError("self-check failed: malformed validator output must fail the checker")

    assert_self_check(
        "validator child checker output was malformed" in malformed_error,
        "malformed validator output must identify a checker failure",
    )

    try:
        update_record_from_reviewer_output(
            current_pairs[1],
            validator_report=validator_report,
            reviewer_output='{"review_status":"maybe","report":"## Unclear"}',
        )
    except CheckerFailureError as error:
        malformed_reviewer_error = str(error)
    else:
        raise CheckerFailureError("self-check failed: malformed reviewer output must fail the checker")

    assert_self_check(
        "reviewer child checker output was malformed" in malformed_reviewer_error,
        "malformed reviewer output must identify a checker failure",
    )
    changed_file.write_text("changed self-check content v2\n", encoding="utf-8")
    assert_self_check(
        record_outdated_reason(current_pairs[0].record) is not None,
        "a checksum change after a child snapshot must make its result stale",
    )
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
    superseded_raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), identity.pair_key)
    assert_self_check(superseded_raw_record is not None, "superseded checksum record must remain as history")
    superseded_record = raw_record_to_check_record(superseded_raw_record)
    assert_self_check(
        superseded_record.check_status == "outdated",
        "reconciliation must eagerly mark an older checksum version outdated",
    )
    explicitly_consistent_pair = set_relation_pair_check_status(
        pair,
        check_status="consistent",
        report="Manual self-check consistency note.",
    )
    assert_self_check(
        explicitly_consistent_pair.record.check_status == "consistent",
        "explicit status command helper must set consistent",
    )
    explicitly_unchecked_pair = set_relation_pair_check_status(
        pair,
        check_status="unchecked",
        report=None,
    )
    assert_self_check(
        explicitly_unchecked_pair.record.check_status == "unchecked",
        "explicit status command helper must reset a pair to unchecked",
    )
    assert_self_check(
        not explicitly_unchecked_pair.record.report and not explicitly_unchecked_pair.record.checked_at,
        "resetting a pair to unchecked must clear the previous reviewer result",
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
    explicitly_inconsistent_pair = set_relation_pair_check_status(
        pair,
        check_status="inconsistent",
        report="Manual self-check inconsistency note.",
    )
    latest_operation = load_pair_operations(paths.operation_log_path, last=1)[0]
    assert_self_check(
        latest_operation.operation == "marked"
        and latest_operation.pair_key == changed_identity.pair_key
        and latest_operation.previous_status == "inconsistent"
        and latest_operation.next_status == "inconsistent",
        "explicit same-status marks must remain visible in operation history",
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
    current_filtered_records = filter_current_records(
        load_allowed_check_records(),
        {changed_identity.pair_key},
    )
    assert_self_check(
        [record.pair_key for record in current_filtered_records] == [changed_identity.pair_key],
        "current-only filtering must retain only current pair keys",
    )
    checked_current_records, marked_removed_records = mark_records_outside_current_pairs(
        [explicitly_inconsistent_pair.record],
        set(),
    )
    assert_self_check(checked_current_records == 1, "queue synchronization must check active pair records")
    assert_self_check(marked_removed_records == 1, "queue synchronization must mark removed relations outdated")
    removed_raw_record = find_raw_record_by_pair_key(load_taskwarrior_records(), changed_identity.pair_key)
    assert_self_check(removed_raw_record is not None, "removed relation record must remain as history")
    assert_self_check(
        raw_record_to_check_record(removed_raw_record).check_status == "outdated",
        "removed relation record must be outdated",
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
        active_config.journal_cmd is None
        or any(record.get("description") == "self-check command started" for record in project_journal),
        "script operations must log to the project journal when journaling is configured",
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


def add_pair_status_arguments(parser: argparse.ArgumentParser, *, include_report: bool = True) -> None:
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
    if include_report:
        parser.add_argument(
            "--report",
            help="optional markdown report to store with the explicit status",
        )


def add_agent_jobs_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--agent-jobs",
        "--jobs",
        dest="agent_jobs",
        type=int,
        help="number of child agent checks to keep running; defaults to consistency.toml agent_jobs",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run depmesh-backed consistency checks.")
    parser.add_argument(
        "--mode",
        help="consistency.toml mode to use; defaults to the config's mode value",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "enqueue-changed",
        help="enqueue relation pairs for all Git-changed files without processing them",
    )

    subparsers.add_parser(
        "sync-queue",
        help="synchronize current relation pairs and mark stale or removed pairs outdated without processing",
    )

    run_cycle_parser = subparsers.add_parser(
        "run-cycle",
        help="reconcile and process one dependency-ready frontier",
    )
    add_agent_jobs_argument(run_cycle_parser)

    process_queue_parser = subparsers.add_parser(
        "process-queue",
        help="rediscover, reconcile, and process one dependency-ready frontier",
    )
    add_agent_jobs_argument(process_queue_parser)

    subparsers.add_parser(
        "frontier",
        help="show the current dependency-ready changed files without reconciling the queue",
    )

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
        "--current",
        action="store_true",
        help="include only records matching current file checksums and depmesh relations",
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

    list_operations_parser = subparsers.add_parser(
        "list-operations",
        help="list the latest pair operations in chronological order",
    )
    list_operations_parser.add_argument(
        "--last",
        type=int,
        default=20,
        help="number of latest operations to include; defaults to 20",
    )

    mark_consistent_parser = subparsers.add_parser(
        "mark-consistent",
        help="explicitly mark one current-checksum relation pair as consistent",
    )
    add_pair_status_arguments(mark_consistent_parser)

    mark_unchecked_parser = subparsers.add_parser(
        "mark-unchecked",
        help="reset one current-checksum relation pair to unchecked for reviewer reevaluation",
    )
    add_pair_status_arguments(mark_unchecked_parser, include_report=False)

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

        if args.command == "enqueue-changed":
            return int(enqueue_changed())

        if args.command == "sync-queue":
            return int(sync_queue())

        if args.command == "run-cycle":
            return int(run_cycle(args))

        if args.command == "process-queue":
            return int(process_queue(args))

        if args.command == "frontier":
            return int(show_frontier())

        if args.command == "enqueue":
            return int(enqueue_files(parse_enqueue_files(args)))

        if args.command == "progress":
            return int(report_progress(args.file))

        if args.command == "list-pairs":
            return int(list_pairs(args))

        if args.command == "list-operations":
            return int(list_operations(args))

        if args.command == "mark-consistent":
            return int(mark_pair_status(args, check_status="consistent"))

        if args.command == "mark-unchecked":
            return int(mark_pair_status(args, check_status="unchecked"))

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
