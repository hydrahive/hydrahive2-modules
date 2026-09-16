#!/usr/bin/env bash
set -euo pipefail

readonly RUNTIME_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/dev/shm
cd "$RUNTIME_ROOT"
exec 9>/run/hh-telephony-spike.lock
if ! flock -n 9; then
    printf '%s\n' busy
    exit 0
fi
exec python3 -m spike.stdin_incoming_probe
