#!/usr/bin/bash

set -euo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 '<prolog-goal>'" >&2
    exit 2
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
main="${project_root}/prolog/main.pl"
goal="${1}, halt"

if [[ -f "${main}" ]]; then
    exec swipl --quiet --no-packs -f none -s "${main}" -g "${goal}" -t halt
fi

exec swipl --quiet --no-packs -f none -g "${goal}" -t halt
