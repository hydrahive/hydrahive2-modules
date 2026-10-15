#!/usr/bin/env bash
# Vitrine: Dienst + udev-Regel entfernen. Videos und Cache bleiben (Moduldaten).
set -euo pipefail
UNIT=hydrahive2-vitrine
sudo -n bash -c "systemctl disable --now ${UNIT} >/dev/null 2>&1 || true
rm -f /etc/systemd/system/${UNIT}.service /etc/udev/rules.d/71-hydrahive2-vitrine.rules
systemctl daemon-reload
udevadm control --reload-rules || true"
echo "Vitrine-Dienst entfernt (Videos bleiben erhalten)"
