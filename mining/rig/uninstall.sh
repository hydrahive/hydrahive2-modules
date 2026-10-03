#!/bin/sh
# HydraHive Rig-Client entfernen. Den Rechner danach in HydraHive sperren/löschen.
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausführen." >&2; exit 1; }
systemctl disable --now hydrahive-rig.service 2>/dev/null || true
rm -f /etc/systemd/system/hydrahive-rig.service
systemctl daemon-reload
rm -rf /opt/hydrahive-rig /etc/hydrahive-rig /var/lib/hydrahive-rig
id hh-rig >/dev/null 2>&1 && userdel hh-rig || true
echo "[hydrahive-rig] entfernt."
