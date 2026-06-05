#!/bin/bash
# Archiver-Setup: sudoers-Regel für mount/umount anlegen
set -euo pipefail

RULE=/etc/sudoers.d/hydrahive-mount
CONTENT="hydrahive ALL=(ALL) NOPASSWD: /usr/bin/mount, /usr/bin/umount"

if [[ -f "$RULE" ]]; then
  echo "[archiver] sudoers-Regel bereits vorhanden: $RULE"
  exit 0
fi

echo "$CONTENT" > "$RULE"
chmod 440 "$RULE"
echo "[archiver] sudoers-Regel installiert: $RULE"
