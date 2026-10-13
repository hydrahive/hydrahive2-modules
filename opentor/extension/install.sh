#!/usr/bin/env bash
set -euo pipefail

MODULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT="${HH_DATA_DIR:-${HOME}/.local/share/hydrahive2}"
RUNTIME="${HYDRAHIVE_OPENTOR_RUNTIME:-${DATA_ROOT}/opentor-runtime}"
UPSTREAM="${RUNTIME}/upstream"
VENV="${RUNTIME}/venv"
PIN="f3b87546f9699f9a319b94fb08b02849881f7fa6"
REPO="https://github.com/vichhka-git/OpenTor.git"

mkdir -p "${RUNTIME}"
chmod 700 "${RUNTIME}"

if [[ ! -d "${UPSTREAM}/.git" ]]; then
  rm -rf "${UPSTREAM}"
  git clone --filter=blob:none "${REPO}" "${UPSTREAM}"
fi
git -C "${UPSTREAM}" fetch --quiet --depth 1 origin "${PIN}"
git -C "${UPSTREAM}" checkout --quiet --detach "${PIN}"

# --- Python-venv ---
# Gleiches Python wie HydraHive (Standard: der Interpreter, mit dem der Kern
# läuft), aufgelöst auf die versionierte Datei. NICHT `python3 -m venv`: dann
# folgt bin/python dem System-Link und findet nach einem Python-Wechsel seine
# Pakete nicht mehr. Passt die Version nicht oder zeigt bin/python ins Leere
# (Ubuntu 26.04: 3.12 entfernt), wird mit --clear neu gebaut.
# Kern-Spec docs/specs/python-314-umstieg.md.
_base_python="${HYDRAHIVE_OPENTOR_BASE_PYTHON:-$(command -v python3)}"
_base_python="$(readlink -f -- "${_base_python}")"
_want="$("${_base_python}" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
_have="$("${VENV}/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
if [[ "${_want}" != "${_have}" ]]; then
  echo "OpenTor: Python-venv neu bauen (${_have:-keins} -> ${_want})"
  "${_base_python}" -m venv --clear "${VENV}"
fi
# --- Ende Python-venv ---
"${VENV}/bin/python" -m pip install --disable-pip-version-check --no-input -q -r "${MODULE_ROOT}/requirements.txt"

TOR_BIN="$(command -v tor || true)"
if [[ -z "${TOR_BIN}" ]]; then
  if ! command -v apt-get >/dev/null 2>&1 || ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "OpenTor: kein Tor und kein rootloser Debian-Paketweg vorhanden" >&2
    exit 1
  fi
  TOR_CACHE="${RUNTIME}/tor-package"
  mkdir -p "${TOR_CACHE}"
  (cd "${TOR_CACHE}" && apt-get download tor >/dev/null)
  TOR_DEB="$(find "${TOR_CACHE}" -maxdepth 1 -type f -name 'tor_*.deb' | sort | tail -1)"
  [[ -n "${TOR_DEB}" ]] || { echo "OpenTor: Tor-Paket konnte nicht geladen werden" >&2; exit 1; }
  rm -rf "${RUNTIME}/tor"
  mkdir -p "${RUNTIME}/tor"
  dpkg-deb -x "${TOR_DEB}" "${RUNTIME}/tor"
  TOR_BIN="${RUNTIME}/tor/usr/bin/tor"
fi
[[ -x "${TOR_BIN}" ]] || { echo "OpenTor: Tor-Binary fehlt" >&2; exit 1; }

cat > "${RUNTIME}/runtime.env" <<EOF
HYDRAHIVE_OPENTOR_ROOT=${UPSTREAM}
HYDRAHIVE_OPENTOR_PYTHON=${VENV}/bin/python
HYDRAHIVE_OPENTOR_RUNTIME=${RUNTIME}
HYDRAHIVE_TOR_BIN=${TOR_BIN}
EOF
chmod 600 "${RUNTIME}/runtime.env"

echo "OpenTor Runtime bereit: ${RUNTIME}"
