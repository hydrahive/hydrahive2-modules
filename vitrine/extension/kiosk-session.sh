#!/bin/bash
# Vitrine-Kiosk-Sitzung (startet sddm automatisch für den Nutzer hydrahive-kiosk).
# Schaltet den virtuellen Monitor (EVDI, 1080x1920) ein, alle anderen Ausgänge aus, und zeigt das Dashboard im Firefox-Kiosk.
# Den virtuellen Monitor stellt der Vitrine-Dienst bereit; bis er da ist, wird gewartet.
set -u
exec >"${HOME}/kiosk.log" 2>&1

START="file://${HOME}/.vitrine/start.html"              # leitet auf die Kiosk-Seite weiter (Schlüssel nicht in ps)
SERVICE_USER="$(cat /etc/hydrahive2-vitrine/service-user 2>/dev/null || echo hydrahive)"

xhost "+SI:localuser:${SERVICE_USER}" >/dev/null      # nur der Vitrine-Dienst darf Leerlauf/Zeiger abfragen
xset s off -dpms s noblank
xsetroot -solid "#0b1220"

output_on() {
  local p o
  p="$(xrandr --listproviders | awk '/name:modesetting/ {print $4}' | head -1)"
  [ -n "${p}" ] && xrandr --setprovideroutputsource "${p}" 0
  o="$(xrandr | awk '/^DVI-I-[0-9-]+ connected/ {print $1}' | head -1)"
  [ -n "${o}" ] || return 1
  xrandr --output "${o}" --mode 1080x1920 --pos 0x0 --primary
  for other in $(xrandr | awk '/ connected/ && !/^DVI-I/ {print $1}'); do
    xrandr --output "${other}" --off
  done
}

# Der Ausgang verschwindet, wenn der Vitrine-Dienst neu startet (virtueller Monitor meldet sich neu an) → laufend prüfen
output_ok() { xrandr | grep -Eq '^DVI-I-[0-9-]+ connected (primary )?1080x1920\+0\+0'; }
until output_on; do sleep 2; done
openbox &
( while true; do firefox --kiosk --profile "${HOME}/firefox" "${START}"; sleep 2; done ) &
while true; do
  output_ok || output_on || true
  sleep 3
done
