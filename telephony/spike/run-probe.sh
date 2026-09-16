#!/usr/bin/env bash
set -euo pipefail

readonly RUNTIME_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/dev/shm
cd "$RUNTIME_ROOT"
exec python3 -m spike.cli "$@"
