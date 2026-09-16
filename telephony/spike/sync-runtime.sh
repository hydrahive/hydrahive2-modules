#!/usr/bin/env bash
set -euo pipefail

readonly CONTAINER_NAME="hh-telephony-spike"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly RUNTIME_ROOT="/opt/hh-telephony-spike"
readonly FILES=(
    __init__.py cli.py config.py ctrl_tcp.py incoming_probe.py incoming_runtime.py probe.py
    stdin_payload.py stdin_probe.py stdin_incoming_probe.py
    run-probe.sh run-stdin-probe.sh run-stdin-incoming-probe.sh
)

command -v incus >/dev/null || {
    echo "incus is required" >&2
    exit 69
}
incus info "$CONTAINER_NAME" >/dev/null 2>&1 || {
    echo "missing dedicated runtime: $CONTAINER_NAME" >&2
    exit 69
}

if ! incus info "$CONTAINER_NAME" | grep -q '^Status: RUNNING$'; then
    incus start "$CONTAINER_NAME"
fi
version="$(incus exec "$CONTAINER_NAME" -- /opt/baresip/bin/baresip -h 2>&1 || true)"
grep -q 'baresip v4\.11\.0' <<<"$version" || {
    echo "unexpected Baresip runtime version" >&2
    exit 78
}

for filename in "${FILES[@]}"; do
    incus file push "$SCRIPT_DIR/$filename" \
        "$CONTAINER_NAME$RUNTIME_ROOT/spike/$filename"
done
incus exec "$CONTAINER_NAME" -- chmod 0755 \
    "$RUNTIME_ROOT/spike/run-probe.sh" \
    "$RUNTIME_ROOT/spike/run-stdin-probe.sh" \
    "$RUNTIME_ROOT/spike/run-stdin-incoming-probe.sh"

echo "synced: $CONTAINER_NAME"
