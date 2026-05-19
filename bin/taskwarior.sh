#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.."; pwd)"

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <taskwarrior-arguments...>" >&2
    exit 2
fi

cd "$ROOT_DIR"

logged_at() {
    local alphabet
    local encoded
    local epoch_seconds
    local nanoseconds
    local remainder
    local seconds
    local timestamp
    local value

    alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    epoch_seconds=1767225600
    timestamp="$(date -u +%s:%N)"
    seconds="${timestamp%:*}"
    nanoseconds="${timestamp#*:}"
    value=$(((seconds - epoch_seconds) * 1000000000 + 10#$nanoseconds))

    if ((value < 0)); then
        echo "logged_at timestamp is before the project epoch" >&2
        return 1
    fi

    encoded=""

    for _ in {1..10}; do
        remainder=$((value % 62))
        encoded="${alphabet:remainder:1}${encoded}"
        value=$((value / 62))
    done

    if ((value > 0)); then
        echo "logged_at timestamp exceeds the fixed-width range" >&2
        return 1
    fi

    printf "%s\n" "$encoded"
}

logged_time() {
    date +%H:%M:%S
}

ARGS=("$@")
OVERRIDES=()

while [[ ${#ARGS[@]} -gt 0 && "${ARGS[0]}" == rc.* ]]; do
    OVERRIDES+=("${ARGS[0]}")
    ARGS=("${ARGS[@]:1}")
done

if [[ ${#ARGS[@]} -eq 0 ]]; then
    echo "Usage: $0 <taskwarrior-arguments...>" >&2
    exit 2
fi

case "${ARGS[0]}" in
    add | log)
        exec task rc:.taskrc rc.confirmation:no "${OVERRIDES[@]}" "${ARGS[@]}" project:feeds.fun "logged_at:$(logged_at)" "logged_time:$(logged_time)"
        ;;
esac

exec task rc:.taskrc rc.confirmation:no "${OVERRIDES[@]}" project:feeds.fun "${ARGS[@]}"
