#!/usr/bin/env bash
# Vitrine Multiseat (M2): Zweiten Arbeitsplatz ausschalten = Stand vor multiseat-apply.sh wiederherstellen. Läuft als root.
# Aufrufer: multiseat-apply.sh (Prüfung fehlgeschlagen), der Rückbau-Timer (Skript hängt) oder „ausschalten“.
# Wiederholbar: ein zweiter Aufruf schadet nicht. Ohne Sicherung wird der Anmeldedienst NICHT geraten.
# Systemprogramme über Variablen (Tests setzen Ersatzprogramme); HH_MULTISEAT_ROOT nur für Tests.
set -uo pipefail

ROOT_DIR="${HH_MULTISEAT_ROOT:-}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
LOGINCTL="${LOGINCTL:-loginctl}"
UDEVADM="${UDEVADM:-udevadm}"
SLEEP="${SLEEP:-sleep}"
CONF="${ROOT_DIR}/etc/hydrahive2-vitrine"
BK="${CONF}/multiseat-vorher"
MARKER="${CONF}/multiseat.aktiv"
LIGHTDM_DIR="${ROOT_DIR}/etc/lightdm/lightdm.conf.d"
LIGHTDM_CONF="${LIGHTDM_DIR}/50-hydrahive-multiseat.conf"
XORG_CONF="${ROOT_DIR}/etc/X11/xorg.conf.d/90-hydrahive-vitrine-seat0.conf"
DDM="${ROOT_DIR}/etc/X11/default-display-manager"
SDDM_CONF="${ROOT_DIR}/etc/sddm.conf"
VITRINE_UNIT=hydrahive2-vitrine
DROPIN="${ROOT_DIR}/etc/systemd/system/${VITRINE_UNIT}.service.d/50-hydrahive-multiseat.conf"
TIMER=hydrahive2-vitrine-multiseat-revert
KIOSK_USER="${KIOSK_USER:-hydrahive-kiosk}"
CHECK_SECONDS="${HH_MULTISEAT_CHECK_SECONDS:-60}"
SEAT_WAIT="${HH_MULTISEAT_SEAT_WAIT:-20}"

# Sicherheitsnetz abbauen (läuft der Rückbau selbst aus dem Timer, endet nur der Timer, nicht dieser Lauf)
"${SYSTEMCTL}" stop "${TIMER}.timer" >/dev/null 2>&1 || true

restore() {   # <Sicherungsname> <Ziel>: Datei zurück, oder entfernen, wenn sie vorher fehlte
  if [ -f "${BK}/$1" ]; then mkdir -p "$(dirname "$2")" && cp -a "${BK}/$1" "$2"
  elif [ -f "${BK}/$1.fehlt" ]; then rm -f "$2"; fi
}

seat1_gone() {
  [ -z "$("${LOGINCTL}" list-seats --no-legend 2>/dev/null | awk '$1 == "seat1"')" ]
}

# Geräte zurück zu seat0 und WARTEN, bis udev/logind seat1 wirklich entfernt haben. Live-Test 24.11.2026: sddm startete,
# während die Grafikkarte noch an seat1 hing → Xorg auf seat0 brach ab („Failed to read display number from pipe“,
# wie M0-Probe C), der Kiosk landete auf seat1. Ein zweites flush-devices hat geholfen.
release_devices() {
  "${LOGINCTL}" flush-devices >/dev/null 2>&1 || echo "Vitrine-Multiseat: loginctl flush-devices fehlgeschlagen" >&2
  "${UDEVADM}" settle --timeout=15 >/dev/null 2>&1 || true
  for _ in $(seq 1 "${SEAT_WAIT}"); do
    seat1_gone && return 0
    "${SLEEP}" 1
  done
  echo "Vitrine-Multiseat: zweiter Arbeitsplatz nach ${SEAT_WAIT} s noch da – Geräte noch einmal zurückgeben" >&2
  "${LOGINCTL}" flush-devices >/dev/null 2>&1 || true
  "${UDEVADM}" settle --timeout=15 >/dev/null 2>&1 || true
  "${SLEEP}" 2
  seat1_gone && return 0
  echo "Vitrine-Multiseat: zweiter Arbeitsplatz ist immer noch da – Anmeldedienst wird trotzdem gestartet" >&2
  return 1
}

kiosk_on_seat0() {
  local n=$(( (CHECK_SECONDS + 2) / 3 ))
  for _ in $(seq 1 "${n}"); do
    if "${LOGINCTL}" list-sessions --no-legend 2>/dev/null \
       | awk -v u="${KIOSK_USER}" '$3 == u && $4 == "seat0" {f=1} END {exit !f}'; then
      return 0
    fi
    "${SLEEP}" 3
  done
  return 1
}

start_old_dm() {   # alter Anmeldedienst, danach die Vitrine (Dashboard an das neue X bzw. Stand ohne Drop-in)
  "${SYSTEMCTL}" restart "${old_unit}" >/dev/null 2>&1 || echo "Vitrine-Multiseat: ${old_unit} startet nicht" >&2
  "${SYSTEMCTL}" restart "${VITRINE_UNIT}" >/dev/null 2>&1 || echo "Vitrine-Multiseat: Vitrine-Dienst startet nicht" >&2
}

if [ ! -d "${BK}" ]; then
  rm -f "${LIGHTDM_CONF}" "${XORG_CONF}" "${MARKER}"
  if [ -f "${DROPIN}" ]; then rm -f "${DROPIN}"; "${SYSTEMCTL}" daemon-reload >/dev/null 2>&1 || true; fi
  release_devices || true
  echo "Vitrine-Multiseat: keine Sicherung gefunden – eigene Dateien entfernt, Anmeldedienst NICHT umgestellt." \
       "Bleibt ein Bildschirm schwarz: Rechner neu starten." >&2
  exit 0
fi

old_unit="$(tr -cd 'A-Za-z0-9@._-' < "${BK}/dm-unit" 2>/dev/null || true)"
# 1. lightdm aus (nur wenn er nicht schon vorher der Anmeldedienst war)
if [ "${old_unit}" != "lightdm.service" ]; then
  "${SYSTEMCTL}" disable lightdm.service >/dev/null 2>&1 || true
  "${SYSTEMCTL}" stop lightdm.service >/dev/null 2>&1 || true
fi
# 2. eigene Dateien weg; vorher vorhandene gleichnamige lightdm-Dateien zurück
rm -f "${LIGHTDM_CONF}" "${XORG_CONF}"
for f in "${BK}"/lightdm-50-hydrahive*.conf; do
  [ -f "${f}" ] || continue
  mkdir -p "${LIGHTDM_DIR}" && cp -a "${f}" "${LIGHTDM_DIR}/${f##*/lightdm-}"
done
# 3. Drop-in des Vitrine-Dienstes wie vorher (fehlte er, bleibt er weg → Entscheidung des letzten Updates gilt wieder)
if [ -f "${BK}/vitrine-dropin.conf" ] || [ -f "${BK}/vitrine-dropin.conf.fehlt" ]; then
  restore vitrine-dropin.conf "${DROPIN}"
else
  rm -f "${DROPIN}"                                  # Sicherung einer älteren Version ohne Vermerk: eigene Datei weg
fi
rmdir "$(dirname "${DROPIN}")" 2>/dev/null || true
"${SYSTEMCTL}" daemon-reload >/dev/null 2>&1 || true
# 4. Geräte zurück zu seat0 (entfernt die 72-seat-*-Regeln von loginctl attach; M0 belegt) und auf udev/logind warten
release_devices || true
# 5. Anmeldedienst wie vorher – Pfad und Dienst kommen aus der Sicherung, nie geraten
restore default-display-manager "${DDM}"
restore sddm.conf "${SDDM_CONF}"
if [ -n "${old_unit}" ]; then
  "${SYSTEMCTL}" enable --force "${old_unit}" >/dev/null 2>&1 || echo "Vitrine-Multiseat: ${old_unit} ließ sich nicht aktivieren" >&2
  start_old_dm
else
  echo "Vitrine-Multiseat: vorheriger Anmeldedienst unbekannt – nicht gestartet. Rechner neu starten." >&2
  "${SYSTEMCTL}" restart "${VITRINE_UNIT}" >/dev/null 2>&1 || true
fi
rm -rf "${BK}"
rm -f "${MARKER}"
echo "Vitrine-Multiseat: zweiter Arbeitsplatz ausgeschaltet, Anmeldedienst ${old_unit:-unverändert} wie vorher"

# 6. Nachprüfung: Kiosk wieder auf seat0 – sonst EINMAL Geräte zurückgeben und den Anmeldedienst neu starten
if kiosk_on_seat0; then echo "Vitrine-Multiseat: Vitrine läuft wieder (seat0)"; exit 0; fi
if [ -n "${old_unit}" ]; then
  echo "Vitrine-Multiseat: Vitrine noch nicht auf seat0 – Geräte und ${old_unit} noch einmal" >&2
  release_devices || true
  start_old_dm
  if kiosk_on_seat0; then echo "Vitrine-Multiseat: Vitrine läuft wieder (seat0)"; exit 0; fi
fi
echo "Vitrine-Multiseat: Vitrine-Sitzung nach dem Rückbau nicht gefunden. Rechner neu starten; hilft das nicht," \
     "Vitrine in den Moduleinstellungen neu installieren." >&2
exit 3
