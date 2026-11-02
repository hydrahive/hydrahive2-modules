#!/usr/bin/env bash
# Zerlege-Werkstatt: Analyseumgebung stoppen und entfernen.
#
# Die Falldaten liegen im Modul-Datenordner und bleiben unangetastet. Nur der
# Container mit den Werkzeugen geht weg. Die Containerdefinition kann mit
# install.sh jederzeit neu erzeugt werden.
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-hh-zerlegewerkstatt}"
DATA_DIR="${DATA_DIR:-/var/lib/hydrahive2/data/modules/zerlegewerkstatt}"

log() { printf '[zerlegewerkstatt] %s\n' "$*" >&2; }
die() { printf '[zerlegewerkstatt] FEHLER: %s\n' "$*" >&2; exit 1; }

command -v incus >/dev/null 2>&1 || die "incus ist nicht installiert."

if incus info "$CONTAINER_NAME" >/dev/null 2>&1; then
  log "stoppe $CONTAINER_NAME"
  incus stop --force "$CONTAINER_NAME" >/dev/null 2>&1 || true
  log "entferne $CONTAINER_NAME"
  incus delete --force "$CONTAINER_NAME" >/dev/null 2>&1 || true
  log "Container entfernt"
else
  log "Container $CONTAINER_NAME gibt es nicht"
fi

# Falldaten bleiben bewusst erhalten.
if [ -d "$DATA_DIR" ]; then
  log "Falldaten bleiben erhalten: $DATA_DIR"
fi

log "Fertig."
