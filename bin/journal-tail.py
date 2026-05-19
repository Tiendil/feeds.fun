#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
TASKWARIOR = ROOT_DIR / "bin" / "taskwarior.sh"
COLUMN_PADDING = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Output project journal records.")
    parser.add_argument("-n", "--lines", type=int, default=20, help="number of existing records to show")
    parser.add_argument("-f", "--follow", action="store_true", help="follow new records after output")
    parser.add_argument("-i", "--interval", type=float, default=1.0, help="poll interval in seconds when following")
    return parser.parse_args()


def load_records() -> list[dict[str, Any]]:
    result = subprocess.run(
        [str(TASKWARIOR), "rc.verbose:nothing", "+journal", "export"],
        cwd=ROOT_DIR,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    return json.loads(result.stdout)


def record_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("logged_at") or ""),
        str(record.get("entry") or ""),
        str(record.get("uuid") or ""),
    )


def record_id(record: dict[str, Any]) -> str:
    uuid = record.get("uuid")

    if uuid:
        return str(uuid)

    return "|".join(record_key(record) + (str(record.get("description") or ""),))


def record_time(record: dict[str, Any]) -> str:
    logged_time = record.get("logged_time")

    if logged_time:
        return str(logged_time)

    entry = str(record.get("entry") or "")

    if not entry:
        return ""

    try:
        return datetime.strptime(entry, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).astimezone().strftime("%H:%M:%S")
    except ValueError:
        return ""


def record_actor(record: dict[str, Any]) -> str:
    return " ".join(str(tag) for tag in record.get("tags", []) if tag != "journal")


def record_kind(record: dict[str, Any]) -> str:
    return str(record.get("kind") or "")


class Formatter:
    def __init__(self) -> None:
        self.actor_width = 0
        self.kind_width = 0

    def observe(self, records: list[dict[str, Any]]) -> None:
        for record in records:
            self.actor_width = max(self.actor_width, len(record_actor(record)))
            self.kind_width = max(self.kind_width, len(record_kind(record)))

    def format_record(self, record: dict[str, Any]) -> str:
        actor_width = self.actor_width + COLUMN_PADDING
        kind_width = self.kind_width + COLUMN_PADDING

        return "{time} {actor:<{actor_width}} {kind:<{kind_width}} {description}".format(
            time=record_time(record),
            actor=record_actor(record),
            actor_width=actor_width,
            kind=record_kind(record),
            kind_width=kind_width,
            description=str(record.get("description") or ""),
        ).rstrip()


def print_records(records: list[dict[str, Any]], formatter: Formatter) -> None:
    for record in records:
        print(formatter.format_record(record), flush=True)


def main() -> int:
    args = parse_args()
    records = sorted(load_records(), key=record_key)
    formatter = Formatter()
    formatter.observe(records)
    seen = {record_id(record) for record in records}

    if args.lines > 0:
        print_records(records[-args.lines :], formatter)

    if not args.follow:
        return 0

    while True:
        time.sleep(args.interval)

        records = sorted(load_records(), key=record_key)
        formatter.observe(records)
        new_records = [record for record in records if record_id(record) not in seen]

        for record in new_records:
            seen.add(record_id(record))

        print_records(new_records, formatter)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(file=sys.stderr)
        raise SystemExit(130)
