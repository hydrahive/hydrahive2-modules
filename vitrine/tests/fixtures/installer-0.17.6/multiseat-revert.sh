#!/usr/bin/env bash
# Vitrine Multiseat (M2): Zweiten Arbeitsplatz ausschalten = Stand vor multiseat-apply.sh wiederherstellen. Läuft als root.
# Aufrufer: multiseat-apply.sh (Prüfung fehlgeschlagen), der Rückbau-Timer (Skript hängt) oder „ausschalten“.
# Wiederholbar: ein zweiter Aufruf schadet nicht. Ohne Sicherung wird der Anmeldedienst NICHT geraten.
# Systemprogramme über Variablen (Tests setzen Ersatzprogramme); HH_MULTISEAT_ROOT nur für Tests.
set -uo pipefail

ROOT_DIR="${HH_MULTISEAT_ROOT:-}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
LOGINCTL="${LOGINCTL:-loginctl}"
SLEEP="${SLEEP:-sleep}"
CONF="${ROOT_DIR}/etc/hydrahive2-vitrine"
BK="${CONF}/multiseat-vorher"
MARKER="${CONF}/multiseat.aktiv"
LIGHTDM_DIR="${ROOT_DIR}/etc/lightdm/lightdm.conf.d"
LIGHTDM_CONF="${LIGHTDM_DIR}/50-hydrahive-multiseat.conf"
XORG_CONF="${ROOT_DIR}/etc/X11/xorg.conf.d/90-hydrahive-vitrine-seat0.conf"
DDM="${ROOT_DIR}/etc/X11/default-display-manager"
SDDM_CONF="${ROOT_DIR}/etc/sddm.conf"
TIMER=hydrahive2-vitrine-multiseat-revert
KIOSK_USER="${KIOSK_USER:-hydrahive-kiosk}"
CHECK_SECONDS="${HH_MULTISEAT_CHECK_SECONDS:-60}"

# Sicherheitsnetz abbauen (läuft der Rückbau selbst aus dem Timer, endet nur der Timer, nicht dieser Lauf)
"${SYSTEMCTL}" stop "${TIMER}.timer" >/dev/null 2>&1 || true

restore() {   # <Sicherungsname> <Ziel>: Datei zurück, oder entfernen, wenn sie vorher fehlte
  if [ -f "${BK}/$1" ]; then cp -a "${BK}/$1" "$2"
  elif [ -f "${BK}/$1.fehlt" ]; then rm -f "$2"; fi
}

if [ ! -d "${BK}" ]; then
  rm -f "${LIGHTDM_CONF}" "${XORG_CONF}" "${MARKER}"
  "${LOGINCTL}" flush-devices >/dev/null 2>&1 || true
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
# 3. Geräte zurück zu seat0 (entfernt die 72-seat-*-Regeln von loginctl attach; M0 belegt)
"${LOGINCTL}" flush-devices >/dev/null 2>&1 || echo "Vitrine-Multiseat: loginctl flush-devices fehlgeschlagen" >&2
# 4. Anmeldedienst wie vorher – Pfad und Dienst kommen aus der Sicherung, nie geraten
restore default-display-manager "${DDM}"
restore sddm.conf "${SDDM_CONF}"
if [ -n "${old_unit}" ]; then
  "${SYSTEMCTL}" enable --force "${old_unit}" >/dev/null 2>&1 || echo "Vitrine-Multiseat: ${old_unit} ließ sich nicht aktivieren" >&2
  "${SYSTEMCTL}" restart "${old_unit}" >/dev/null 2>&1 || echo "Vitrine-Multiseat: ${old_unit} startet nicht" >&2
else
  echo "Vitrine-Multiseat: vorheriger Anmeldedienst unbekannt – nicht gestartet. Rechner neu starten." >&2
fi
rm -rf "${BK}"
rm -f "${MARKER}"
echo "Vitrine-Multiseat: zweiter Arbeitsplatz ausgeschaltet, Anmeldedienst ${old_unit:-unverändert} wie vorher"

# Nachprüfung: Kiosk wieder auf seat0
n=$(( (CHECK_SECONDS + 2) / 3 ))
for _ in $(seq 1 "${n}"); do
  if "${LOGINCTL}" list-sessions --no-legend 2>/dev/null \
     | awk -v u="${KIOSK_USER}" '$3 == u && $4 == "seat0" {f=1} END {exit !f}'; then
    echo "Vitrine-Multiseat: Vitrine läuft wieder (seat0)"
    exit 0
  fi
  "${SLEEP}" 3
done
echo "Vitrine-Multiseat: Vitrine-Sitzung nach dem Rückbau nicht gefunden. Rechner neu starten; hilft das nicht," \
     "Vitrine in den Moduleinstellungen neu installieren." >&2
exit 3
