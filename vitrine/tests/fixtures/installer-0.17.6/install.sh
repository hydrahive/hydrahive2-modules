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

# --- Mainboard-Licht (S8, SPEC-LICHT.md) – darf die Installation nie abbrechen ---
USER_NAME="${USER_NAME}" DATA="${DATA}" bash "${MODULE_ROOT}/extension/light-install.sh" || true

# --- Kiosk (Statuszentrale per Maus, SPEC-STATUSZENTRALE.md) ---
# Nur unter Linux mit apt + sddm + Firefox und nur, wenn kein echter Monitor angeschlossen ist (dann gehört der
# Anmeldebildschirm niemandem). Abschalten: Datei ${DATA}/kiosk.off anlegen.
KIOSK_ENV=""
sudo -n bash -c 'systemctl stop hydrahive2-vitrine-kiosk-cleanup.timer' >/dev/null 2>&1 || true   # Update: Rückbau abbrechen
_monitor=""
for st in /sys/class/drm/card*-*/status; do
  [ -r "${st}" ] || continue
  drv="$(basename "$(readlink -f "$(dirname "${st}")/device/driver" 2>/dev/null)" 2>/dev/null || true)"
  [ "${drv}" != "evdi" ] && [ "$(cat "${st}")" = "connected" ] && _monitor="$(basename "$(dirname "${st}")")"
done
if [ -f "${DATA}/kiosk.off" ]; then
  echo "Vitrine-Kiosk: abgeschaltet (${DATA}/kiosk.off)"
elif [ -n "${_monitor}" ]; then
  echo "Vitrine-Kiosk: nicht eingerichtet – Monitor ${_monitor} angeschlossen (Anmeldebildschirm bleibt)"
elif command -v apt-get >/dev/null && command -v sddm >/dev/null && command -v firefox >/dev/null; then
  [ -s "${DATA}/kiosk.key" ] || (umask 077 && head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > "${DATA}/kiosk.key")
  _port="${HH_PORT:-$(systemctl show hydrahive2 -p Environment --value 2>/dev/null | tr ' ' '\n' | sed -n 's/^HH_PORT=//p')}"
  _url="http://127.0.0.1:${_port:-8001}/api/module-device/vitrine/kiosk?k=$(cat "${DATA}/kiosk.key")"
  # Nur `sudo -n bash` ist erlaubt (sudoers des Installers). Der HydraHive-Dienst läuft mit ProtectHome=read-only, und
  # sudo erbt das → Kiosk-Teil (legt /home/hydrahive-kiosk an) über systemd-run außerhalb der Sandbox (am Gerät belegt).
  _before="$(sudo -n bash -c 'cat /etc/sddm.conf' 2>/dev/null || true)"
  if sudo -n bash -c "systemd-run --quiet --wait --pipe --collect /bin/bash '${MODULE_ROOT}/extension/kiosk-install.sh' '${MODULE_ROOT}' '${USER_NAME}' '${_url}'"; then
    sudo -n bash -c "install -m 755 '${MODULE_ROOT}/extension/kiosk-uninstall.sh' /etc/hydrahive2-vitrine/kiosk-uninstall.sh"
    [ "${_before}" != "$(sudo -n bash -c 'cat /etc/sddm.conf')" ] && KIOSK_RESTART_SDDM=1
    KIOSK_ENV="Environment=VITRINE_KIOSK_DISPLAY=:0
SupplementaryGroups=video
BindReadOnlyPaths=-/tmp/.X11-unix"
  else
    # Kiosk gescheitert → halb Eingerichtetes zurücknehmen, Vitrine-Dienst trotzdem einrichten (Video läuft weiter)
    echo "Vitrine-Kiosk: Kiosk-Einrichtung fehlgeschlagen – Rückbau, Display zeigt weiter Videos" >&2
    sudo -n bash -c "systemd-run --quiet --wait --pipe --collect /bin/bash '${MODULE_ROOT}/extension/kiosk-uninstall.sh'" || true
    KIOSK_ENV=""
  fi
else
  echo "Vitrine-Kiosk: nicht eingerichtet (braucht apt, sddm und Firefox)"
fi

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
${KIOSK_ENV}

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now ${UNIT} >/dev/null && systemctl restart ${UNIT}"

# Erst nach dem Dienst (stellt den virtuellen Monitor bereit): Anmeldebildschirm → Kiosk-Sitzung, nur beim ersten Mal
if [ "${KIOSK_RESTART_SDDM:-0}" = 1 ]; then
  sudo -n bash -c 'systemctl restart sddm' && echo "Vitrine-Kiosk: Anmeldung auf Kiosk umgestellt"
fi

echo "Vitrine-Dienst eingerichtet (${UNIT}); Videos nach ${DATA}/videos"
