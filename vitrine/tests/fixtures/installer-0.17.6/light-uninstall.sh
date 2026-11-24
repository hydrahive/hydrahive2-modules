#!/usr/bin/env bash
# Vitrine S8: udev-Regel fürs Mainboard-Licht entfernen. OpenRGB bleibt installiert (normales Systempaket).
set -uo pipefail
RULE="${VITRINE_LIGHT_RULE:-/etc/udev/rules.d/72-hydrahive2-vitrine-licht.rules}"
sudo -n bash -c "rm -f '${RULE}'; udevadm control --reload-rules || true"
echo "Vitrine-Licht: Regel entfernt (OpenRGB bleibt installiert)"
