#!/bin/bash
# Vitrine-Kiosk-Sitzung (startet sddm automatisch für den Nutzer hydrahive-kiosk).
# Schaltet den virtuellen Monitor (EVDI, 1080x1920) ein, alle anderen Ausgänge aus, und zeigt das Dashboard im Firefox-Kiosk.
# Den virtuellen Monitor stellt der Vitrine-Dienst bereit; bis er da ist, wird gewartet.
set -u
exec >"${HOME}/kiosk.log" 2>&1

START="file://${HOME}/vitrine/start.html"   # leitet auf die Kiosk-Seite weiter (Schlüssel nicht in ps). KEIN Punkt-Ordner:
#                                          Firefox-Snap darf versteckte Ordner im Home nicht lesen (19.10. auf .2).
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

# Der Ausgang verschwindet, wenn der Vitrine-Dienst neu startet → laufend prüfen. NUR `xrandr --current`: ein volles `xrandr`
# fragt alle Ausgänge neu ab und setzt bei EVDI jedes Mal die EDID neu (19.10.: alle 3 s, X hing dabei bis 20 s).
output_ok() { xrandr --current | grep -Eq '^DVI-I-[0-9-]+ connected (primary )?1080x1920\+0\+0'; }
# Hintergrund-Prozesse enden mit der Sitzung (sonst startet eine verwaiste Schleife Firefox mit dem Xauthority der alten
# Sitzung – am 19.10. nach `systemctl restart sddm` gesehen). Zusätzlich endet jede Schleife, sobald ihr X-Server weg ist.
trap 'kill $(jobs -p) 2>/dev/null' EXIT
x_alive() { xset q >/dev/null 2>&1; }
until output_on; do sleep 2; x_alive || exit 0; done
openbox &
( while x_alive; do firefox --kiosk --profile "${HOME}/firefox" "${START}"; sleep 2; done ) &
while x_alive; do
  output_ok || output_on || true
  sleep 3
done
