#!/usr/bin/env bash
# Vitrine: Renderer-Dienst einrichten. Läuft als HydraHive-Nutzer (Modul-Installer); root-Teile über
# `sudo -n bash` wie die Kern-Extensions (sudoers-Regel des Installers).
set -euo pipefail

MODULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${HH_DATA_DIR:-/var/lib/hydrahive2}/vitrine"
VENV="${DATA}/venv"
USER_NAME="$(id -un)"
UNIT=hydrahive2-vitrine
RULE=/etc/udev/rules.d/71-hydrahive2-vitrine.rules

mkdir -p "${DATA}/videos" "${DATA}/cache"

# --- Python-venv: gleicher Interpreter wie der Kern (Muster OpenTor, Python-3.14-Umstieg) ---
_base="$(readlink -f -- "${VITRINE_BASE_PYTHON:-$(command -v python3)}")"
_want="$("${_base}" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
_have="$("${VENV}/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
if [[ "${_want}" != "${_have}" ]]; then
  echo "Vitrine: Python-venv neu bauen (${_have:-keins} -> ${_want})"
  "${_base}" -m venv --clear "${VENV}"
fi
"${VENV}/bin/python" -m pip install --disable-pip-version-check --no-input -q -r "${MODULE_ROOT}/renderer/requirements.txt"

command -v ffmpeg >/dev/null 2>&1 || sudo -n bash -c 'DEBIAN_FRONTEND=noninteractive apt-get -qq install -y ffmpeg fonts-dejavu-core >/dev/null'

# --- udev: nur dieses Display, nur für die HydraHive-Gruppe ---
sudo -n bash -c "cat > '${RULE}' <<EOF
# HydraHive Vitrine: ArtInChip-USB-Display (Gehäuse-LCD)
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"33c3\", ATTR{idProduct}==\"0e02\", MODE=\"0660\", GROUP=\"${USER_NAME}\"
EOF
udevadm control --reload-rules && udevadm trigger --subsystem-match=usb --attr-match=idVendor=33c3"

# --- systemd-Dienst ---
sudo -n bash -c "cat > /etc/systemd/system/${UNIT}.service <<EOF
[Unit]
Description=HydraHive Vitrine (Gehäuse-Display)
After=network.target

[Service]
Type=simple
User=${USER_NAME}
Group=${USER_NAME}
WorkingDirectory=${MODULE_ROOT}
Environment=VITRINE_DATA=${DATA}
Environment=PYTHONUNBUFFERED=1
ExecStart=${VENV}/bin/python -m renderer.main
Restart=always
RestartSec=3
Nice=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=${DATA}

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now ${UNIT} >/dev/null && systemctl restart ${UNIT}"

echo "Vitrine-Dienst eingerichtet (${UNIT}); Videos nach ${DATA}/videos"
