#!/bin/sh
# HydraHive Rig-Client installieren (Ubuntu/Debian).
#
#   curl -fsSL <url>/install.sh | sudo sh -s -- --server https://… --code XXXX-XXXX-XXXX [--pin sha256//…]
#   curl -fsSL <url>/install.sh | sudo sh -s -- --update      # nur Client erneuern, Kopplung bleibt
#
# Legt Systemnutzer hh-rig an (Gruppen video/render für GPU-Zugriff), kopiert
# den Client nach /opt/hydrahive-rig, koppelt mit dem Code und startet den
# systemd-Dienst. Kein pip, keine Fremdpakete — nur python3 (>= 3.11).
set -eu

REPO_TAR="${HH_RIG_TARBALL:-https://codeload.github.com/hydrahive/hydrahive2-modules/tar.gz/refs/heads/main}"
PREFIX=/opt/hydrahive-rig
CONF_DIR=/etc/hydrahive-rig
USER_NAME=hh-rig
SERVER="" CODE="" PIN="" SRC="" UPDATE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --server) SERVER="$2"; shift 2 ;;
    --code)   CODE="$2"; shift 2 ;;
    --pin)    PIN="$2"; shift 2 ;;
    --src)    SRC="$2"; shift 2 ;;   # lokaler Pfad zu mining/rig (Tests/Offline)
    --update) UPDATE=1; shift ;;
    *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
  esac
done

say() { printf '\033[1;36m[hydrahive-rig]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[hydrahive-rig]\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "Bitte mit sudo ausführen."
if [ "$UPDATE" -eq 1 ]; then
  [ -f "$CONF_DIR/config.json" ] || die "Kein gekoppelter Client gefunden ($CONF_DIR/config.json) — erst mit --server/--code installieren."
else
  [ -n "$SERVER" ] && [ -n "$CODE" ] || die "--server und --code sind nötig (oder --update für ein Update)."
  case "$SERVER" in https://*) ;; *) die "--server muss mit https:// beginnen." ;; esac
fi
command -v python3 >/dev/null || die "python3 fehlt (apt install python3)."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
  || die "python3 >= 3.11 nötig (Debian 12 / Ubuntu 24.04 oder neuer)."
command -v systemctl >/dev/null || die "systemd fehlt."

say "Systemnutzer $USER_NAME"
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd --system --home-dir "$PREFIX" --shell /usr/sbin/nologin "$USER_NAME"
fi
for g in video render; do getent group "$g" >/dev/null && usermod -aG "$g" "$USER_NAME"; done

say "Dateien nach $PREFIX"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
if [ -n "$SRC" ]; then
  cp -r "$SRC" "$TMP/rig"
else
  command -v curl >/dev/null || die "curl fehlt."
  curl -fsSL "$REPO_TAR" | tar -xz -C "$TMP" --wildcards '*/mining/rig' --strip-components=2 \
    || die "Download fehlgeschlagen: $REPO_TAR"
  [ -d "$TMP/rig" ] || die "Archiv enthält mining/rig nicht."
fi
rm -rf "$PREFIX/hydrahive_rig"
mkdir -p "$PREFIX" "$CONF_DIR"
cp -r "$TMP/rig/hydrahive_rig" "$PREFIX/"
chown -R root:root "$PREFIX"; chmod -R go-w "$PREFIX"
chown "$USER_NAME:$USER_NAME" "$CONF_DIR"; chmod 700 "$CONF_DIR"

if [ "$UPDATE" -eq 1 ]; then
  say "systemd-Dienst neu starten"
  install -m 644 "$TMP/rig/hydrahive-rig.service" /etc/systemd/system/hydrahive-rig.service
  systemctl daemon-reload
  systemctl restart hydrahive-rig.service
  say "Fertig: Client $(PYTHONPATH=$PREFIX python3 -c 'import hydrahive_rig; print(hydrahive_rig.__version__)'). Kopplung unverändert."
  exit 0
fi

say "Koppeln mit $SERVER"
set -- --config "$CONF_DIR/config.json" enroll --server "$SERVER" --code "$CODE"
[ -n "$PIN" ] && set -- "$@" --pin "$PIN"
runuser -u "$USER_NAME" -- env PYTHONPATH="$PREFIX" python3 -m hydrahive_rig "$@" \
  || die "Koppeln fehlgeschlagen (Code abgelaufen oder schon benutzt?)."

say "systemd-Dienst"
install -m 644 "$TMP/rig/hydrahive-rig.service" /etc/systemd/system/hydrahive-rig.service
systemctl daemon-reload
systemctl enable --now hydrahive-rig.service
say "Fertig. In HydraHive unter Mining → Rechner den neuen Rechner freigeben."
