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
NODE_TARBALL=""
NODE_URL=""
NODE_SHA256=""

RUST_VERSION="1.81.0"
RUST_TARBALL=""
RUST_URL=""
RUST_SHA256=""

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

BINWALK_VERSION="3.1.0"
BINWALK_FILE="binwalk-${BINWALK_VERSION}.crate"
BINWALK_URL="https://crates.io/api/v1/crates/binwalk/${BINWALK_VERSION}/download"
BINWALK_SHA256="99d5dc70f5021c55624f098adae4d1de9c1c07d000475664704b675aad7e0811"

SASQUATCH_RELEASE="sasquatch-v4.5.1-4"
SASQUATCH_FILE=""
SASQUATCH_URL=""
SASQUATCH_SHA256=""

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

resolve_architecture() {
  local architecture
  architecture="$(incus exec "$CONTAINER_NAME" -- uname -m)" \
    || die "Containerarchitektur konnte nicht ermittelt werden."
  case "$architecture" in
    x86_64)
      NODE_TARBALL="node-v${NODE_VERSION}-linux-x64.tar.xz"
      NODE_SHA256="48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75"
      RUST_TARBALL="rust-${RUST_VERSION}-x86_64-unknown-linux-gnu.tar.xz"
      RUST_SHA256="1a9ee8caaa18a3e433fef93cea8a55dc1ebd478ed761b2fef69d4565f9d00e7f"
      SASQUATCH_FILE="sasquatch_1.0_amd64.deb"
      SASQUATCH_SHA256="bb211daf90069a43b7d5e76f136766a8542a5328015773e9b8be87541b307b60"
      ;;
    aarch64|arm64)
      NODE_TARBALL="node-v${NODE_VERSION}-linux-arm64.tar.xz"
      NODE_SHA256="eb187837a2230d4047161ac0be008584e16b46f726e9c9490ee35dc6b17d9ba8"
      RUST_TARBALL="rust-${RUST_VERSION}-aarch64-unknown-linux-gnu.tar.xz"
      RUST_SHA256="5cd65b0a2724e4193a5c4ba79f0687f8c11d52c2d58ee35bc7ce5958a3cc8dc2"
      SASQUATCH_FILE="sasquatch_1.0_arm64.deb"
      SASQUATCH_SHA256="fb281906a25667414e8b6aff96b49ceb227519122a7844bbc8166f2b6a59554a"
      ;;
    *)
      die "Nicht unterstuetzte Architektur: $architecture (erlaubt: x86_64, aarch64)"
      ;;
  esac
  NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/${NODE_TARBALL}"
  RUST_URL="https://static.rust-lang.org/dist/${RUST_TARBALL}"
  SASQUATCH_URL="https://github.com/onekey-sec/sasquatch/releases/download/${SASQUATCH_RELEASE}/${SASQUATCH_FILE}"
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

ensure_install_network() {
  if incus config device list "$CONTAINER_NAME" | grep -qx eth0; then
    return 0
  fi
  log "haenge Installationsnetzwerk an"
  incus config device add "$CONTAINER_NAME" eth0 nic \
    "nictype=bridged" "parent=$BRIDGE" "name=eth0" \
    || die "Netzwerkbruecke $BRIDGE konnte nicht angehaengt werden."
}

# Das Netz dient ausschliesslich der Installation. Ein EXIT-Trap ruft diese
# Funktion auch bei Download-, Paket- oder Prueffehlern auf.
disable_network() {
  if ! incus info "$CONTAINER_NAME" >/dev/null 2>&1; then
    return 0
  fi
  if ! incus config device list "$CONTAINER_NAME" | grep -qx eth0; then
    return 0
  fi
  log "entferne Installationsnetzwerk"
  incus config device remove "$CONTAINER_NAME" eth0
}

install_container_dependencies() {
  # Ein unveraendertes images:ubuntu/24.04 enthaelt diese Werkzeuge nicht.
  # Erst pruefen: Wiederholungen nach einer Teilinstallation bleiben schnell.
  if incus exec "$CONTAINER_NAME" -- bash -c '
    command -v xz >/dev/null &&
    command -v unzip >/dev/null &&
    command -v java >/dev/null &&
    command -v file >/dev/null &&
    command -v objdump >/dev/null &&
    command -v readelf >/dev/null &&
    command -v strings >/dev/null &&
    command -v python3 >/dev/null &&
    command -v tshark >/dev/null &&
    command -v capinfos >/dev/null &&
    command -v setpriv >/dev/null &&
    command -v gcc >/dev/null &&
    command -v pkg-config >/dev/null &&
    command -v mksquashfs >/dev/null &&
    command -v unsquashfs >/dev/null &&
    command -v 7z >/dev/null &&
    command -v cpio >/dev/null &&
    command -v dtc >/dev/null &&
    command -v yara >/dev/null
  '; then
    log "Container-Grundpakete bereits vorhanden"
    return 0
  fi

  log "installiere Container-Grundpakete"
  incus exec "$CONTAINER_NAME" -- env DEBIAN_FRONTEND=noninteractive \
    apt-get -qq update \
    || die "Paketlisten im Analysecontainer konnten nicht geladen werden."
  incus exec "$CONTAINER_NAME" -- env DEBIAN_FRONTEND=noninteractive \
    apt-get -qq install -y --no-install-recommends \
    xz-utils unzip openjdk-21-jre-headless file binutils python3 ca-certificates \
    tshark wireshark-common util-linux gcc pkg-config libfontconfig1-dev \
    squashfs-tools p7zip-full cpio device-tree-compiler yara \
    || die "Container-Grundpakete konnten nicht installiert werden."

  incus exec "$CONTAINER_NAME" -- bash -c '
    command -v xz >/dev/null &&
    command -v unzip >/dev/null &&
    command -v java >/dev/null &&
    command -v file >/dev/null &&
    command -v objdump >/dev/null &&
    command -v readelf >/dev/null &&
    command -v strings >/dev/null &&
    command -v python3 >/dev/null &&
    command -v tshark >/dev/null &&
    command -v capinfos >/dev/null &&
    command -v setpriv >/dev/null &&
    command -v gcc >/dev/null &&
    command -v pkg-config >/dev/null &&
    command -v mksquashfs >/dev/null &&
    command -v unsquashfs >/dev/null &&
    command -v 7z >/dev/null &&
    command -v cpio >/dev/null &&
    command -v dtc >/dev/null &&
    command -v yara >/dev/null
  ' || die "Container-Grundpakete sind nach der Installation unvollstaendig."
}

install_tshark_adapter() {
  # TShark schreibt unter einem von Node angelegten Pipe-Dateideskriptor keine
  # Ausgabe. REA startet TShark aus Node und kann dann weder Version noch
  # Ergebnisse sehen. Der feste Adapter puffert ausschließlich das fest
  # installierte /usr/bin/tshark und reicht Exit-Code sowie beide Ausgaben durch.
  incus exec "$CONTAINER_NAME" -- bash -s <<'INNER' || die "TShark-Adapter konnte nicht installiert werden."
set -euo pipefail
# Die Werkstatt liest vorhandene Mitschnitte. Live-Capture bleibt selbst im
# Analysecontainer technisch gesperrt.
if [ -e /usr/bin/dumpcap ]; then chmod 000 /usr/bin/dumpcap; fi
cat > /usr/local/bin/rea-tshark <<'WRAPPER'
#!/bin/sh
out="$(mktemp)" || exit 1
err="$(mktemp)" || { rm -f "$out"; exit 1; }
cleanup() { rm -f "$out" "$err"; }
trap cleanup EXIT
# 64 MiB je Ausgabestrom: Ein manipuliertes Capture darf den Container nicht fuellen.
ulimit -f 131072
/usr/bin/tshark "$@" >"$out" 2>"$err" &
child=$!
trap 'kill "$child" 2>/dev/null || true; exit 143' HUP INT TERM
wait "$child"
status=$?
cat "$out"
cat "$err" >&2
exit "$status"
WRAPPER
chmod 0755 /usr/local/bin/rea-tshark
INNER
}

install_tools() {
  local staging="/tmp/zerlegewerkstatt-install"
  mkdir -p "$staging"
  log "lade Werkzeuge"
  fetch_verified "$NODE_URL" "$staging/$NODE_TARBALL" "$NODE_SHA256"
  fetch_verified "$RUST_URL" "$staging/$RUST_TARBALL" "$RUST_SHA256"
  fetch_verified "$REA_URL" "$staging/rea-agents-$REA_VERSION.tgz" "$REA_SHA256"
  fetch_verified "$GHIDRA_URL" "$staging/$GHIDRA_FILE" "$GHIDRA_SHA256"
  fetch_verified "$JADX_URL" "$staging/$JADX_FILE" "$JADX_SHA256"
  fetch_verified "$BINWALK_URL" "$staging/$BINWALK_FILE" "$BINWALK_SHA256"
  fetch_verified "$SASQUATCH_URL" "$staging/$SASQUATCH_FILE" "$SASQUATCH_SHA256"

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

  log "installiere gepinnte Analysewerkzeuge"
  incus exec "$CONTAINER_NAME" -- bash -s -- "$NODE_TARBALL" "$REA_VERSION" \
    "$GHIDRA_FILE" "$JADX_FILE" "$BINWALK_FILE" "$RUST_TARBALL" "$SASQUATCH_FILE" <<'INNER' || die "Installation fehlgeschlagen."
set -euo pipefail
staging=/tmp/zerlegewerkstatt-staging
mkdir -p /opt
node_version="${1#node-}"
node_version="${node_version%%-linux-*}"
if [ ! -x /opt/node/bin/node ] || [ "$(/opt/node/bin/node --version)" != "$node_version" ]; then
  rm -rf /opt/node
  tar -xJf "$staging/$1" -C /opt
  mv "/opt/${1%.tar.xz}" /opt/node
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
rust_dir="${6%.tar.xz}"
rust_version="${6#rust-}"
rust_version="${rust_version%%-*}"
if [ ! -x /opt/rust/bin/cargo ] || \
   ! /opt/rust/bin/rustc --version | grep -Fq "rustc $rust_version "; then
  rm -rf /opt/rust
  tar -xJf "$staging/$6" -C /tmp
  "/tmp/$rust_dir/install.sh" --prefix=/opt/rust --disable-ldconfig
  rm -rf "/tmp/$rust_dir"
fi
# Upstream vergibt fuer mehrere Release-Artefakte dieselbe DEB-Version 1.0.
# Deshalb immer das zuvor per SHA-256 gepruefte Paket installieren.
dpkg -i "$staging/$7"
binwalk_version="${5#binwalk-}"
binwalk_version="${binwalk_version%.crate}"
if [ ! -x /opt/binwalk/bin/binwalk ] || \
   [ "$(/opt/binwalk/bin/binwalk --version)" != "binwalk $binwalk_version" ]; then
  build=/tmp/binwalk-build
  rm -rf "$build"
  rm -rf /opt/binwalk
  mkdir -p "$build"
  tar -xzf "$staging/$5" -C "$build"
  crate_dir="${5%.crate}"
  RUSTC=/opt/rust/bin/rustc /opt/rust/bin/cargo install --locked --path "$build/$crate_dir" --root /opt/binwalk
  rm -rf "$build" /root/.cargo/registry /root/.cargo/git
fi
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
/opt/rust/bin/rustc --version | grep -q '^rustc 1\.81\.0 '
[ -d /opt/ghidra ] || { echo "Ghidra fehlt" >&2; exit 1; }
[ -f /opt/jadx-headless-mcp.jar ] || { echo "JADX fehlt" >&2; exit 1; }
[ "$(/opt/binwalk/bin/binwalk --version)" = "binwalk 3.1.0" ] || {
  echo "Binwalk 3.1.0 fehlt" >&2; exit 1;
}
command -v sasquatch >/dev/null || { echo "Sasquatch fehlt" >&2; exit 1; }
[ -x /usr/local/bin/rea-tshark ] || { echo "TShark-Adapter fehlt" >&2; exit 1; }
[ ! -x /usr/bin/dumpcap ] || { echo "Live-Capture ist nicht gesperrt" >&2; exit 1; }
command -v capinfos >/dev/null
command -v setpriv >/dev/null
INNER
}

start_container() {
  incus start "$CONTAINER_NAME" 2>/dev/null || log "Container laeuft bereits"
}

main() {
  require_incus
  create_container
  start_container
  trap disable_network EXIT
  ensure_install_network
  install_container_dependencies
  install_tshark_adapter
  resolve_architecture
  install_tools
  create_user
  verify_install
  disable_network || die "Installationsnetzwerk konnte nicht entfernt werden."
  trap - EXIT
  log "Analyseumgebung bereit: $CONTAINER_NAME"
}

main "$@"
