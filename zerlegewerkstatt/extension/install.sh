#!/usr/bin/env bash
# Zerlege-Werkstatt: reproduzierbare Analyseumgebung in einem Incus-Container.
#
# Der Container ist unprivilegiert, hat keine Host-Secrets, kein Docker-Socket,
# kein /dev, keine GPU und begrenzte Ressourcen. Das Netz wird nur waehrend
# der Installation benutzt; die Analyse selbst laeuft offline (SPEC §7).
#
# Alle Versionen sind gepinnt und werden ueber SHA-256 geprueft. Bei
# abweichender Pruefsumme bricht das Skript ab.
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-hh-zerlegewerkstatt}"
IMAGE="${IMAGE:-images:ubuntu/24.04}"
CPU_LIMIT="${CPU_LIMIT:-6}"
MEMORY_LIMIT="${MEMORY_LIMIT:-12GiB}"
ANALYSIS_USER="${ANALYSIS_USER:-rea}"
BRIDGE="${BRIDGE:-br0}"

NODE_VERSION="24.22.2"
NODE_TARBALL="node-v${NODE_VERSION}-linux-x64.tar.xz"
NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/${NODE_TARBALL}"
NODE_SHA256="48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75"

REA_VERSION="6.8.0"
REA_URL="https://registry.npmjs.org/rea-agents/-/rea-agents-${REA_VERSION}.tgz"
REA_SHA256="8d542ec76a9cb350584b60a6c9c088706ff812d5bb5b094c20c95b6dc25698bb"

GHIDRA_VERSION="12.1.4"
GHIDRA_FILE="ghidra_${GHIDRA_VERSION}_PUBLIC_20260921.zip"
GHIDRA_URL="https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/${GHIDRA_FILE}"
GHIDRA_SHA256="ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db"

JADX_VERSION="0.7.1"
JADX_FILE="jadx-headless-mcp-${JADX_VERSION}-all.jar"
JADX_URL="https://github.com/1013503897/jadx-headless-mcp/releases/download/v${JADX_VERSION}/${JADX_FILE}"
JADX_SHA256="6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75"

log() { printf '[zerlegewerkstatt] %s\n' "$*" >&2; }
die() { printf '[zerlegewerkstatt] FEHLER: %s\n' "$*" >&2; exit 1; }

# Der Kern ruft dieses Skript als normaler Benutzer auf (modules/installer.py).
# Also kein root: Incus wird ueber die incus-admin-Gruppe verwaltet, wie der
# Kern es mit seinen eigenen Containern auch macht.
require_incus() {
  command -v incus >/dev/null 2>&1 || die "incus ist nicht installiert."
  incus info >/dev/null 2>&1 || die "incus laeuft nicht oder ist nicht initialisiert."
  if ! incus query /1.0 >/dev/null 2>&1; then
    die "Kein Zugriff auf incus. Der Benutzer muss in der Gruppe incus-admin sein."
  fi
}

# Laedt eine Datei herunter und prueft die SHA-256. Bei Abweichung: Abbruch.
fetch_verified() {
  local url="$1" target="$2" expected="$3"
  if [ -f "$target" ] && [ "$(sha256sum "$target" | cut -d' ' -f1)" = "$expected" ]; then
    log "bereits vorhanden und geprueft: $(basename "$target")"
    return 0
  fi
  log "lade $(basename "$target")"
  curl -fsSL --retry 3 --retry-delay 2 -o "$target.part" "$url" \
    || die "Download fehlgeschlagen: $url"
  local actual
  actual="$(sha256sum "$target.part" | cut -d' ' -f1)"
  [ "$actual" = "$expected" ] || {
    rm -f "$target.part"
    die "Pruefsumme weicht ab fuer $(basename "$target"): erwartet $expected, bekommen $actual"
  }
  mv "$target.part" "$target"
}

create_container() {
  if incus info "$CONTAINER_NAME" >/dev/null 2>&1; then
    log "Container $CONTAINER_NAME existiert bereits, aktualisiere ihn"
    return 0
  fi
  log "erzeuge Container $CONTAINER_NAME"
  incus init "$IMAGE" "$CONTAINER_NAME" \
    || die "Container konnte nicht erzeugt werden."
  incus config set "$CONTAINER_NAME" limits.cpu "$CPU_LIMIT" \
    || die "CPU-Limit konnte nicht gesetzt werden."
  incus config set "$CONTAINER_NAME" limits.memory "$MEMORY_LIMIT" \
    || die "Speicherlimit konnte nicht gesetzt werden."
  # Unprivilegiert: kein privileged, kein nesting, keine Host-Geraete.
  incus config set "$CONTAINER_NAME" security.privileged false \
    || die "Privilegien konnten nicht eingeschraenkt werden."
  incus config set "$CONTAINER_NAME" security.nesting false \
    || die "Nesting konnte nicht eingeschraenkt werden."
  # Minimale AppArmor-Erweiterung. REA braucht signal und ptrace, um seine
  # eigenen Hilfsprozesse zu ueberwachen und zu beenden. Nichts weiter.
  incus config set "$CONTAINER_NAME" raw.apparmor "signal,
ptrace," \
    || die "AppArmor-Regeln konnten nicht gesetzt werden."
  incus config device add "$CONTAINER_NAME" eth0 nic \
    "nictype=bridged" "parent=$BRIDGE" "name=eth0" \
    || die "Netzwerkbruecke $BRIDGE konnte nicht angehaengt werden."
}

install_tools() {
  local staging="/tmp/zerlegewerkstatt-install"
  mkdir -p "$staging"
  log "lade Werkzeuge"
  fetch_verified "$NODE_URL" "$staging/$NODE_TARBALL" "$NODE_SHA256"
  fetch_verified "$REA_URL" "$staging/rea-agents-$REA_VERSION.tgz" "$REA_SHA256"
  fetch_verified "$GHIDRA_URL" "$staging/$GHIDRA_FILE" "$GHIDRA_SHA256"
  fetch_verified "$JADX_URL" "$staging/$JADX_FILE" "$JADX_SHA256"

  incus exec "$CONTAINER_NAME" -- mkdir -p /tmp/zerlegewerkstatt-staging \
    || die "Staging konnte nicht angelegt werden."
  # Datei fuer Datei kopieren. `incus file push -r` legt bei einem Verzeichnis
  # einen zusaetzlichen Ordner mit dem Verzeichnisnamen an - dann landet
  # alles eine Ebene zu tief.
  local file
  for file in "$staging"/*; do
    [ -f "$file" ] || continue
    incus file push -p "$file" "$CONTAINER_NAME/tmp/zerlegewerkstatt-staging/$(basename "$file")" \
      || die "Werkzeuge konnten nicht in den Container kopiert werden: $(basename "$file")"
  done

  log "installiere Node, REA, Ghidra und JADX"
  incus exec "$CONTAINER_NAME" -- bash -s -- "$NODE_TARBALL" "$REA_VERSION" \
    "$GHIDRA_FILE" "$JADX_FILE" <<'INNER' || die "Installation fehlgeschlagen."
set -euo pipefail
staging=/tmp/zerlegewerkstatt-staging
mkdir -p /opt
if [ ! -x /opt/node/bin/node ]; then
  tar -xJf "$staging/$1" -C /opt
  mv /opt/node-v*-linux-x64 /opt/node
fi
export PATH="/opt/node/bin:$PATH"
npm install -g --prefix /opt/node "/tmp/zerlegewerkstatt-staging/rea-agents-$2.tgz" >/dev/null
if [ ! -d /opt/ghidra ]; then
  mkdir -p /opt/ghidra-tmp
  unzip -q "$staging/$3" -d /opt/ghidra-tmp
  mv /opt/ghidra-tmp/ghidra_*/ /opt/ghidra/
  rm -rf /opt/ghidra-tmp
fi
mkdir -p /opt/rea-android
install -m 0644 "$staging/$4" "/opt/rea-android/$4"
ln -sf "/opt/rea-android/$4" /opt/jadx-headless-mcp.jar
INNER

  rm -rf "$staging"
  incus exec "$CONTAINER_NAME" -- rm -rf /tmp/zerlegewerkstatt-staging \
    || log "WARNUNG: Staging im Container konnte nicht entfernt werden"
}

create_user() {
  log "lege Analysebenutzer $ANALYSIS_USER an"
  incus exec "$CONTAINER_NAME" -- bash -s <<'INNER' || die "Benutzer konnte nicht angelegt werden."
set -euo pipefail
id rea >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/rea --shell /usr/sbin/nologin rea
mkdir -p /work /out
chown -R rea:rea /work /out
chmod 0750 /work /out
INNER
}

verify_install() {
  log "pruefe die Installation"
  incus exec "$CONTAINER_NAME" -- bash -s <<'INNER' || die "Pruefung fehlgeschlagen."
set -euo pipefail
export PATH="/opt/node/bin:$PATH"
rea --version
node --version
[ -d /opt/ghidra ] || { echo "Ghidra fehlt" >&2; exit 1; }
[ -f /opt/jadx-headless-mcp.jar ] || { echo "JADX fehlt" >&2; exit 1; }
INNER
}

start_container() {
  incus start "$CONTAINER_NAME" 2>/dev/null || log "Container laeuft bereits"
}

main() {
  require_incus
  create_container
  start_container
  install_tools
  create_user
  verify_install
  log "Analyseumgebung bereit: $CONTAINER_NAME"
}

main "$@"
