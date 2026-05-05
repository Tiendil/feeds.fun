#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    env = os.environ.copy()
    env["COMPOSE_IGNORE_ORPHANS"] = "true"

    completed = subprocess.run(
        ["./bin/backend-utils.sh", "poetry", "run", "python", "tach_map_query.py", *sys.argv[1:]],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )

    sys.stdout.write(completed.stdout)

    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
