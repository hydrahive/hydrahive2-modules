#!/usr/bin/env bash
# Vitrine-Kiosk zurückbauen: sddm wie vorher, Sitzung, Nutzer, Richtlinien, EVDI-Autoload weg. Läuft als root.
# Die Pakete (evdi, openbox) bleiben installiert – sie stören nicht und könnten anders genutzt werden.
set -uo pipefail

KIOSK=hydrahive-kiosk
CONF=/etc/hydrahive2-vitrine
SDDM=/etc/sddm.conf

if [ -f "${CONF}/sddm.conf.vor-vitrine" ]; then
  if [ -s "${CONF}/sddm.conf.vor-vitrine" ]; then cp -a "${CONF}/sddm.conf.vor-vitrine" "${SDDM}"; else rm -f "${SDDM}"; fi
fi
rm -f /usr/share/xsessions/hydrahive-vitrine-kiosk.desktop
rm -f /etc/modules-load.d/hydrahive2-vitrine-evdi.conf /etc/modprobe.d/hydrahive2-vitrine-evdi.conf
rm -f /etc/ssh/sshd_config.d/50-hydrahive2-vitrine-kiosk.conf
rm -f /etc/firefox/policies/policies.json
if id "${KIOSK}" >/dev/null 2>&1; then
  loginctl terminate-user "${KIOSK}" 2>/dev/null
  sleep 2
  pkill -u "${KIOSK}" 2>/dev/null
  sleep 1
  userdel -r "${KIOSK}" 2>/dev/null
fi
rm -rf "${CONF}"
systemctl restart sddm 2>/dev/null || true
echo "Vitrine-Kiosk entfernt (Anmeldebildschirm wie vorher)"
