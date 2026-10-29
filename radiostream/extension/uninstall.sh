#!/usr/bin/env bash
# Radiostream: Dienste und Hörer-Seite entfernen. Pakete, Bibliothek, Passwörter und der Merker sender.on bleiben
# (ein Modul-Update ruft uninstall.sh und gleich danach install.sh auf – der Sender soll dann wieder laufen).
set -euo pipefail
UNIT_ICE=hydrahive-radiostream-icecast
UNIT_LIQ=hydrahive-radiostream-liquidsoap
SITE=hydrahive-radiostream
sudo -n bash -c "systemctl disable --now $UNIT_LIQ $UNIT_ICE >/dev/null 2>&1 || true
rm -f /etc/systemd/system/$UNIT_LIQ.service /etc/systemd/system/$UNIT_ICE.service
systemctl daemon-reload
if [ -e /etc/nginx/sites-enabled/$SITE ] || [ -e /etc/nginx/sites-available/$SITE ]; then
  rm -f /etc/nginx/sites-enabled/$SITE /etc/nginx/sites-available/$SITE
  nginx -t >/dev/null 2>&1 && systemctl reload nginx || true
fi"
echo "Radiostream: Dienste entfernt (Bibliothek und Einstellungen bleiben)"
