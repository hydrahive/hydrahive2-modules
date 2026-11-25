#!/usr/bin/env bash
# Vitrine-Kiosk zurückbauen: sddm wie vorher, Sitzung, Nutzer, Richtlinien, EVDI-Autoload weg. Läuft als root.
# Die Pakete (evdi, openbox) bleiben installiert – sie stören nicht und könnten anders genutzt werden.
set -uo pipefail

KIOSK=hydrahive-kiosk
CONF=/etc/hydrahive2-vitrine
SDDM=/etc/sddm.conf

# Multiseat (M2): Zweiter Arbeitsplatz an → ZUERST ausschalten (lightdm aus, Geräte zurück, Anmeldedienst wie vorher).
# Sonst bliebe nach dem Deinstallieren lightdm mit Kiosk-Autologin stehen. Die Kiosk-Nachprüfung ist hier überflüssig.
if [ -f "${CONF}/multiseat.aktiv" ]; then
  if [ -f "${CONF}/multiseat-revert.sh" ]; then
    HH_MULTISEAT_CHECK_SECONDS=1 bash "${CONF}/multiseat-revert.sh" || true
  else
    echo "Vitrine-Kiosk: zweiter Arbeitsplatz war an, Rückbau-Skript fehlt – Anmeldedienst bitte von Hand prüfen" >&2
  fi
fi

if [ -f "${CONF}/sddm.conf.vor-vitrine" ]; then
  if [ -s "${CONF}/sddm.conf.vor-vitrine" ]; then cp -a "${CONF}/sddm.conf.vor-vitrine" "${SDDM}"; else rm -f "${SDDM}"; fi
fi
rm -f /usr/share/xsessions/hydrahive-vitrine-kiosk.desktop
rm -f /etc/modules-load.d/hydrahive2-vitrine-evdi.conf /etc/modprobe.d/hydrahive2-vitrine-evdi.conf
rm -f /etc/ssh/sshd_config.d/50-hydrahive2-vitrine-kiosk.conf
# Früher (bis 0.18.1) stand die Website-Sperre SYSTEMWEIT in /etc/firefox/policies/policies.json – damit konnte niemand
# am Rechner mehr surfen (25.11.2026, zweiter Arbeitsplatz). Entfernen, aber NUR wenn die Datei exakt eine unserer
# Fassungen ist (sha256 aus der Git-Historie: 0.7.0 und 0.7.3–0.18.1); fremde Richtlinien bleiben unangetastet.
FF_POLICY=/etc/firefox/policies/policies.json
FF_OURS="0eb5dbc14674fa208767929ee0af43ca241e8f284023cd4ee1953962e9ebfd60 0893f0b5f9f5150f792619b0209e2ee3f0916669b73fe0c1a35de2b78d4dd656"
if [ -f "${FF_POLICY}" ]; then
  _ff_sum="$(sha256sum "${FF_POLICY}" | cut -d' ' -f1)"
  case " ${FF_OURS} " in
    *" ${_ff_sum} "*) rm -f "${FF_POLICY}"; rmdir "$(dirname "${FF_POLICY}")" 2>/dev/null || true
                      echo "Vitrine-Kiosk: alte systemweite Firefox-Sperre entfernt" ;;
  esac
fi
_kiosk_running="$(loginctl list-sessions --no-legend 2>/dev/null | grep -c " ${KIOSK} ")"
if id "${KIOSK}" >/dev/null 2>&1; then
  loginctl terminate-user "${KIOSK}" 2>/dev/null
  sleep 2
  pkill -u "${KIOSK}" 2>/dev/null
  sleep 1
  userdel -r "${KIOSK}" 2>/dev/null
fi
rm -rf "${CONF}"
# sddm nur neu starten, wenn gerade die Kiosk-Sitzung läuft (sonst unnötig den Anmeldebildschirm neu laden)
if [ "${_kiosk_running}" != 0 ]; then systemctl restart sddm 2>/dev/null || true; fi
echo "Vitrine-Kiosk entfernt (Anmeldebildschirm wie vorher)"
