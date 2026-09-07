#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${HH_DATA_DIR:-${HOME}/.local/share/hydrahive2}"
RUNTIME="${HYDRAHIVE_OPENTOR_RUNTIME:-${DATA_ROOT}/opentor-runtime}"
if [[ -f "${RUNTIME}/tor.pid" ]]; then
  PID="$(cat "${RUNTIME}/tor.pid" || true)"
  if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then
    kill "${PID}" 2>/dev/null || true
  fi
fi
rm -rf "${RUNTIME}"
echo "OpenTor Runtime entfernt"
