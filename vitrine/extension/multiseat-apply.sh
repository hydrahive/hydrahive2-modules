#!/usr/bin/env bash
# Vitrine Multiseat (M2): Zweiten Arbeitsplatz einschalten. Läuft als root (sudo -n bash → systemd-run, wie kiosk-install).
# Argumente: <plan.json> <lightdm.conf> <xorg.conf>  – erzeugt von backend/seat_plan.py aus seats.validate() + Snapshot.
# Ablauf: Plan prüfen → Sicherung → lightdm installieren → Dateien → Rückbau-Timer → loginctl attach → lightdm statt
# bisherigem Anmeldedienst → Prüfung. Fehlschlag → multiseat-revert.sh sofort; hängt dieses Skript, greift der Timer.
# Systemprogramme über Variablen (Tests setzen Ersatzprogramme); HH_MULTISEAT_ROOT nur für Tests.
set -uo pipefail

PLAN="${1:?Plan fehlt}"; LIGHTDM_IN="${2:?lightdm-Datei fehlt}"; XORG_IN="${3:?Xorg-Datei fehlt}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${HH_MULTISEAT_ROOT:-}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
SYSTEMD_RUN="${SYSTEMD_RUN:-systemd-run}"
LOGINCTL="${LOGINCTL:-loginctl}"
APT_GET="${APT_GET:-apt-get}"
PGREP="${PGREP:-pgrep}"
PYTHON="${PYTHON:-python3}"
SLEEP="${SLEEP:-sleep}"
CHECK_SECONDS="${HH_MULTISEAT_CHECK_SECONDS:-90}"
REVERT_AFTER="${HH_MULTISEAT_REVERT_AFTER:-300}"
CONF="${ROOT_DIR}/etc/hydrahive2-vitrine"
BK="${CONF}/multiseat-vorher"
MARKER="${CONF}/multiseat.aktiv"
LIGHTDM_DIR="${ROOT_DIR}/etc/lightdm/lightdm.conf.d"
LIGHTDM_CONF="${LIGHTDM_DIR}/50-hydrahive-multiseat.conf"
XORG_CONF="${ROOT_DIR}/etc/X11/xorg.conf.d/90-hydrahive-vitrine-seat0.conf"
DDM="${ROOT_DIR}/etc/X11/default-display-manager"
SDDM_CONF="${ROOT_DIR}/etc/sddm.conf"
DM_LINK="${ROOT_DIR}/etc/systemd/system/display-manager.service"
TIMER=hydrahive2-vitrine-multiseat-revert
REVERT="${CONF}/multiseat-revert.sh"

die() { echo "Vitrine-Multiseat: $*" >&2; exit 2; }

# --- 1. Plan lesen und SELBST prüfen (vor jeder Änderung) ---
mapfile -t P < <("${PYTHON}" - "${PLAN}" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
vals = [p["seat0_busid"], p["evdi_kmsdev"], p["kiosk_user"], *p["attach"]]
if not all(isinstance(v, str) and v.isprintable() for v in vals):
    sys.exit(2)
print("\n".join(vals))
PY
) || die "Plan ${PLAN} nicht lesbar – Zuordnung in der Vitrine neu speichern."
[ "${#P[@]}" -ge 4 ] || die "Plan enthält keine Geräte für den zweiten Arbeitsplatz."
BUSID="${P[0]}"; KMSDEV="${P[1]}"; KIOSK_USER="${P[2]}"; ATTACH=("${P[@]:3}")
[[ "${BUSID}" =~ ^PCI:[0-9]+(@[0-9]+)?:[0-9]+:[0-9]+$ ]] || die "ungültige BusID im Plan: ${BUSID}"
[[ "${KMSDEV}" =~ ^/dev/dri/[A-Za-z0-9:._/-]+$ && "${KMSDEV}" != *..* ]] || die "ungültiges USB-Display-Gerät im Plan"
[[ "${KIOSK_USER}" =~ ^[a-z_][a-z0-9_-]*$ ]] || die "ungültiger Kiosk-Nutzer im Plan"
for p in "${ATTACH[@]}"; do
  [[ "${p}" =~ ^/sys/devices/[A-Za-z0-9:._/-]+$ ]] || die "Gerätepfad mit unerlaubten Zeichen abgelehnt: ${p}"
  case "/${p}/" in */../*|*/./*) die "Gerätepfad mit ../ abgelehnt: ${p}" ;; esac
  real="$(readlink -e -- "${ROOT_DIR}${p}")" || die "Gerät nicht gefunden: ${p} – Geräte neu einlesen und Zuordnung speichern."
  [[ "${real}" == "${ROOT_DIR}/sys/devices/"* ]] || die "Gerätepfad zeigt aus /sys/devices hinaus: ${p}"
done
[ -f "${LIGHTDM_IN}" ] && [ -f "${XORG_IN}" ] || die "Konfigurationsdateien fehlen."
[ -d "${BK}" ] && die "Zweiter Arbeitsplatz ist schon eingeschaltet (Sicherung vorhanden) – erst ausschalten."
dm_unit="$(basename "$(readlink -f "${DM_LINK}" 2>/dev/null)" 2>/dev/null)"
[[ "${dm_unit}" =~ ^[A-Za-z0-9@._-]+\.service$ ]] || die "Aktiver Anmeldedienst nicht feststellbar – nichts geändert."

# --- 2. Sicherung der berührten Dateien ---
mkdir -p "${BK}"
backup() { if [ -f "$2" ]; then cp -a "$2" "${BK}/$1"; else : > "${BK}/$1.fehlt"; fi; }
backup default-display-manager "${DDM}"
backup sddm.conf "${SDDM_CONF}"
printf '%s\n' "${dm_unit}" > "${BK}/dm-unit"
for f in "${LIGHTDM_DIR}"/50-hydrahive*.conf; do [ -f "${f}" ] && cp -a "${f}" "${BK}/lightdm-${f##*/}"; done
ls -1 "${ROOT_DIR}/etc/udev/rules.d/" 2>/dev/null | grep '^72-seat-' > "${BK}/udev-72-seat.liste" || true
early_fail() {   # vor dem Umschalten: nichts ist aktiv → nur eigene Spuren entfernen, Anmeldedienst nicht anfassen
  rm -f "${LIGHTDM_CONF}" "${XORG_CONF}"; rm -rf "${BK}"
  echo "Vitrine-Multiseat: $* – nichts umgeschaltet, Vitrine läuft wie bisher." >&2; exit 1
}

# --- 3. lightdm nur hier installieren (nie für Ein-Arbeitsplatz-Nutzer) ---
DEBIAN_FRONTEND=noninteractive "${APT_GET}" -qq install -y --no-install-recommends lightdm lightdm-gtk-greeter >/dev/null \
  || early_fail "lightdm ließ sich nicht installieren (Internet/Paketquellen prüfen)"
LIGHTDM_BIN="$(command -v lightdm)" || early_fail "lightdm nach der Installation nicht gefunden"

# --- 4. Dateien ---
install -d -m 755 "${LIGHTDM_DIR}" "$(dirname "${XORG_CONF}")"
install -m 644 "${LIGHTDM_IN}" "${LIGHTDM_CONF}"
install -m 644 "${XORG_IN}" "${XORG_CONF}"
install -m 755 "${HERE}/multiseat-revert.sh" "${REVERT}"

# --- 5. Sicherheitsnetz VOR dem Umschalten: Rückbau-Timer, den nur die erfolgreiche Prüfung stoppt ---
"${SYSTEMCTL}" stop "${TIMER}.timer" >/dev/null 2>&1 || true
"${SYSTEMCTL}" reset-failed "${TIMER}.timer" "${TIMER}.service" >/dev/null 2>&1 || true
"${SYSTEMD_RUN}" --quiet --unit="${TIMER}" --on-active="${REVERT_AFTER}" /bin/bash "${REVERT}" \
  || early_fail "Rückbau-Timer ließ sich nicht starten"

fail() {
  echo "Vitrine-Multiseat: $* – stelle den Stand von vorher wieder her." >&2
  HH_MULTISEAT_ROOT="${ROOT_DIR}" bash "${REVERT}"
  echo "Vitrine-Multiseat: zweiter Arbeitsplatz NICHT eingeschaltet. Geräte-Zuordnung prüfen und erneut versuchen." >&2
  exit 1
}

# --- 6. Geräte an seat1 ---
for p in "${ATTACH[@]}"; do
  "${LOGINCTL}" attach seat1 "${p}" || fail "loginctl attach ${p} fehlgeschlagen"
done

# --- 7. Anmeldedienst wechseln (Pfad aus dem System, nicht geraten) ---
printf '%s\n' "${LIGHTDM_BIN}" > "${DDM}"
if [ "${dm_unit}" != "lightdm.service" ]; then
  "${SYSTEMCTL}" disable "${dm_unit}" >/dev/null 2>&1 || true
fi
"${SYSTEMCTL}" enable --force lightdm.service >/dev/null || fail "lightdm ließ sich nicht aktivieren"
[ "${dm_unit}" != "lightdm.service" ] && "${SYSTEMCTL}" stop "${dm_unit}"
"${SYSTEMCTL}" restart lightdm.service || fail "lightdm startet nicht"

# --- 8. Prüfung: Kiosk NUR auf seat0, Anmeldung (nicht Kiosk) auf seat1, USB-Display an, Kiosk-Firefox läuft ---
evdi_card="$(basename "$(readlink -f "${ROOT_DIR}${KMSDEV}")")"
check() {
  local s; s="$("${LOGINCTL}" list-sessions --no-legend 2>/dev/null)"
  awk -v u="${KIOSK_USER}" '$3 == u && $4 == "seat0" {f=1} END {exit !f}' <<<"${s}" || return 1
  awk -v u="${KIOSK_USER}" '$3 == u && $4 == "seat1" {f=1} END {exit f}' <<<"${s}" || return 1
  awk -v u="${KIOSK_USER}" '$3 != u && $4 == "seat1" {f=1} END {exit !f}' <<<"${s}" || return 1
  grep -qx enabled "${ROOT_DIR}/sys/class/drm/${evdi_card}"-*/enabled 2>/dev/null || return 1
  "${PGREP}" -u "${KIOSK_USER}" -f "firefox --kiosk" >/dev/null 2>&1 || return 1
}
ok=0
for _ in $(seq 1 $(( (CHECK_SECONDS + 2) / 3 ))); do
  if check; then ok=1; break; fi
  "${SLEEP}" 3
done
[ "${ok}" = 1 ] || fail "Prüfung nach ${CHECK_SECONDS} s fehlgeschlagen (Vitrine oder Anmeldebildschirm nicht da)"

# --- 9. Erfolg: Sicherheitsnetz abbauen, Marker setzen (install.sh lässt sddm dann in Ruhe – M2b) ---
"${SYSTEMCTL}" stop "${TIMER}.timer" >/dev/null 2>&1 || true
printf 'seit=%s\n' "$(date -Is)" > "${MARKER}"
echo "Vitrine-Multiseat: zweiter Arbeitsplatz eingeschaltet (Vitrine auf seat0, Anmeldebildschirm auf seat1)"
