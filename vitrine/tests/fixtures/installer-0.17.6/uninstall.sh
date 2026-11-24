#!/usr/bin/env bash
# Vitrine: Dienst + udev-Regel entfernen. Videos und Cache bleiben (Moduldaten).
set -euo pipefail
UNIT=hydrahive2-vitrine
sudo -n bash -c "systemctl disable --now ${UNIT} >/dev/null 2>&1 || true
rm -f /etc/systemd/system/${UNIT}.service /etc/udev/rules.d/71-hydrahive2-vitrine.rules
systemctl daemon-reload
udevadm control --reload-rules || true"
bash "$(dirname "${BASH_SOURCE[0]}")/light-uninstall.sh" || true    # S8: Licht-Regel (OpenRGB bleibt)
# Kiosk: Ein Modul-Update ruft uninstall.sh und gleich danach install.sh auf. Der Rückbau läuft deshalb verzögert und
# nur, wenn das Modul dann wirklich weg ist (install.sh bricht ihn bei einem Update ab).
MODULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -x /etc/hydrahive2-vitrine/kiosk-uninstall.sh ]; then
  sudo -n bash -c "systemctl stop hydrahive2-vitrine-kiosk-cleanup.timer >/dev/null 2>&1
    systemd-run --quiet --unit hydrahive2-vitrine-kiosk-cleanup --on-active=120s \
      /bin/bash -c \"[ -d '${MODULE_ROOT}' ] || /etc/hydrahive2-vitrine/kiosk-uninstall.sh\"" || true
fi
echo "Vitrine-Dienst entfernt (Videos bleiben erhalten)"
