from __future__ import annotations

import argparse
import json
import subprocess  # noqa: S404
import sys
from pathlib import PurePosixPath
from typing import cast


def main() -> int:
    parser = argparse.ArgumentParser(description="Print Tach file relations for one Feeds Fun artifact.")
    parser.add_argument("--direction", choices=("dependencies", "dependents"), required=True)
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args()

    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "tach", "map", "--direction", args.direction, "--output", "-"],
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)  # noqa: T201

    if completed.returncode != 0:
        return completed.returncode

    try:
        loaded_map = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        print(f"could not parse tach map JSON: {error}", file=sys.stderr)  # noqa: T201
        return 1

    if not isinstance(loaded_map, dict):
        print("tach map JSON must be an object", file=sys.stderr)  # noqa: T201
        return 1

    dependency_map = cast(dict[str, object], loaded_map)
    artifact = _to_backend_artifact(args.artifact)

    for dependency in sorted(_dependencies_for(dependency_map, artifact)):
        print(f"@/ffun/{dependency}")  # noqa: T201

    return 0


def _to_backend_artifact(artifact: str) -> str:
    normalized = _normalize_artifact(artifact)

    if normalized.startswith("ffun/"):
        return normalized

    if normalized.startswith("@/ffun/"):
        return normalized.removeprefix("@/ffun/")

    if normalized.startswith("@/"):
        return normalized.removeprefix("@/")

    return normalized


def _normalize_artifact(artifact: str) -> str:
    normalized = artifact.strip()

    if normalized.startswith("./"):
        normalized = normalized[2:]

    return PurePosixPath(normalized).as_posix()


def _dependencies_for(dependency_map: dict[str, object], artifact: str) -> list[str]:
    values = dependency_map.get(artifact, dependency_map.get(f"./{artifact}", []))

    if not isinstance(values, list):
        print(f"tach map value for {artifact!r} must be a list", file=sys.stderr)  # noqa: T201
        return []

    return [_normalize_artifact(value) for value in values if isinstance(value, str)]


if __name__ == "__main__":
    raise SystemExit(main())
