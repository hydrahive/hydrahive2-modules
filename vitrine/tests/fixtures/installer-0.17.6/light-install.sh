#!/usr/bin/env bash
# Vitrine S8: Mainboard-Licht einrichten (SPEC-LICHT.md). Wird von install.sh aufgerufen; Fehler hier brechen die
# Installation nie ab (install.sh ruft mit `|| true`).
#   - nur wenn ein unterstützter Licht-Chip am USB hängt (heute: ITE IT5711 048d:5711, Gigabyte RGB Fusion 2)
#   - OpenRGB aus dem Ubuntu-Archiv, ohne Empfehlungen; sein Benutzer-Dienst bleibt aus
#   - udev-Regel: nur dieses Gerät, nur hidraw, Lese-/Schreibrecht für die HydraHive-Gruppe
# Nur `sudo -n bash` ist erlaubt (sudoers des Installers). Abschalten: Datei ${DATA}/light.off anlegen.
set -uo pipefail

USER_NAME="${USER_NAME:-$(id -un)}"
DATA="${DATA:-${HH_DATA_DIR:-/var/lib/hydrahive2}/vitrine}"
RULE="${VITRINE_LIGHT_RULE:-/etc/udev/rules.d/72-hydrahive2-vitrine-licht.rules}"
CHIPS=("048d:5711")

if [ -f "${DATA}/light.off" ]; then
  echo "Vitrine-Licht: abgeschaltet (${DATA}/light.off)"
  exit 0
fi

found=""
for id in "${CHIPS[@]}"; do
  if lsusb 2>/dev/null | grep -qi " ID ${id} "; then found="${id}"; fi
done
if [ -z "${found}" ]; then
  echo "Vitrine-Licht: kein unterstützter Licht-Chip gefunden – nichts eingerichtet"
  exit 0
fi

if ! command -v openrgb >/dev/null 2>&1; then
  echo "Vitrine-Licht: OpenRGB installieren (Licht-Chip ${found})"
  if ! sudo -n bash -c 'DEBIAN_FRONTEND=noninteractive apt-get -qq install -y --no-install-recommends openrgb >/dev/null'; then
    echo "Vitrine-Licht: OpenRGB nicht installiert – Licht bleibt, wie es ist"
    exit 0
  fi
fi

vendor="${found%%:*}"
product="${found##*:}"
[[ "${vendor}${product}" =~ ^[0-9a-f]{8}$ && "${USER_NAME}" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || {
  echo "Vitrine-Licht: unerwarteter Gerätename oder Nutzer – nichts eingerichtet"; exit 0; }
# Nur GROUP reicht nicht (live .2, 26.10.): Mit angemeldeter Kiosk-Sitzung legt uaccess eine ACL mit `group::---` auf
# das Gerät, die überstimmt die Gruppe. Ein benannter ACL-Eintrag für die HydraHive-Gruppe übersteht uaccess.
match="SUBSYSTEM==\\\"hidraw\\\", ATTRS{idVendor}==\\\"${vendor}\\\", ATTRS{idProduct}==\\\"${product}\\\""
sudo -n bash -c "printf '%s\n' '# HydraHive Vitrine S8: Mainboard-Licht (${found}) für die HydraHive-Gruppe' \
  \"${match}, MODE=\\\"0660\\\", GROUP=\\\"${USER_NAME}\\\"\" \
  \"${match}, RUN+=\\\"/usr/bin/setfacl -m g:${USER_NAME}:rw \\\$devnode\\\"\" \
  | tee '${RULE}' >/dev/null && udevadm control --reload-rules" \
  || { echo "Vitrine-Licht: Regel nicht angelegt"; exit 0; }

# Vorhandene Geräte jetzt anwenden. Nicht mit --attr-match: idVendor sitzt am USB-Elterngerät, nicht am hidraw-Gerät
# (live .2: der Filter fand nichts). Stattdessen die hidraw-Geräte mit passender HID_ID heraussuchen.
SYS="${VITRINE_SYS_HIDRAW:-/sys/class/hidraw}"
want="$(printf '0003:0000%s:0000%s' "${vendor^^}" "${product^^}")"
devs=()
for d in "${SYS}"/hidraw*; do
  grep -qx "HID_ID=${want}" "${d}/device/uevent" 2>/dev/null && devs+=("${d}")
done
if [ "${#devs[@]}" -gt 0 ]; then
  sudo -n bash -c "udevadm trigger --action=change ${devs[*]} && udevadm settle" || true
fi
echo "Vitrine-Licht: eingerichtet (${found}, Regel ${RULE}, ${#devs[@]} Gerät(e) angewendet)"
