#!/usr/bin/env bash
# Radiostream: Sendebetrieb einrichten (PLAN-E2.md „Sendebetrieb“). Läuft als HydraHive-Nutzer (Modul-Installer);
# root-Teile über `sudo -n bash` wie die anderen Module (sudoers-Regel des Installers).
#
# Startet den Sender NICHT von selbst. Nur wenn er vorher lief (Merker sender.on, z. B. bei einem Modul-Update),
# läuft er danach wieder. Passwörter werden einmalig erzeugt und bleiben bei Updates gleich.
set -euo pipefail

USER_NAME="$(id -un)"
DATA="${HH_DATA_DIR:-/var/lib/hydrahive2}/radiostream"
CFG="${HH_CONFIG_DIR:-/etc/hydrahive2}/radiostream"
WEB=/var/www/hydrahive-radiostream
UNIT_ICE=hydrahive-radiostream-icecast
UNIT_LIQ=hydrahive-radiostream-liquidsoap
SITE=hydrahive-radiostream

# --- Pakete (Paket-Dienst icecast2 bleibt aus; wir nutzen eine eigene Konfiguration) ---
_missing=""
for p in liquidsoap icecast2 ffmpeg; do dpkg -s "$p" >/dev/null 2>&1 || _missing="$_missing $p"; done
if [ -n "$_missing" ]; then
  echo "Radiostream: installiere$_missing"
  sudo -n bash -c "echo 'icecast2 icecast2/icecast-setup boolean false' | debconf-set-selections
DEBIAN_FRONTEND=noninteractive apt-get -qq install -y --no-install-recommends$_missing >/dev/null"
fi
sudo -n bash -c 'systemctl disable --now icecast2 >/dev/null 2>&1 || true'

# --- Ordner + Passwörter (einmalig, 0600, nur der HydraHive-Nutzer) ---
mkdir -p "$DATA/log" "$CFG"
chmod 700 "$CFG"
if [ ! -s "$CFG/secrets.env" ]; then
  _gen() { head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
  (umask 077 && printf 'RADIOSTREAM_SOURCE_PASSWORD=%s\nRADIOSTREAM_ADMIN_PASSWORD=%s\nRADIOSTREAM_FEED_KEY=%s\n' \
    "$(_gen)" "$(_gen)" "$(_gen)" > "$CFG/secrets.env")
  echo "Radiostream: Passwörter erzeugt"
fi
chmod 600 "$CFG/secrets.env"

# --- Pausenzeichen (leise Notschleife, falls kein Titel kommt) ---
if [ ! -s "$DATA/pausenzeichen.mp3" ] && command -v ffmpeg >/dev/null; then
  ffmpeg -loglevel error -y \
    -f lavfi -i "sine=f=523:d=0.35" -f lavfi -i "sine=f=659:d=0.35" -f lavfi -i "sine=f=784:d=0.7" \
    -f lavfi -i "anullsrc=r=44100:cl=stereo:d=8" \
    -filter_complex "[0][1][2]concat=n=3:v=0:a=1,afade=t=out:st=1.0:d=0.4,volume=0.25,aformat=channel_layouts=stereo[t];[t][3]concat=n=2:v=0:a=1" \
    -ar 44100 -b:a 128k "$DATA/pausenzeichen.mp3" || echo "Radiostream: Pausenzeichen nicht erzeugt (dann Stille)"
fi

# --- Hörer-Seite: Web-Ordner, den nginx lesen darf (/var/lib/hydrahive2 ist 0750) ---
sudo -n bash -c "install -d -m 755 -o '$USER_NAME' -g '$USER_NAME' '$WEB'"

# --- systemd-Dienste ---
sudo -n bash -c "cat > /etc/systemd/system/$UNIT_ICE.service <<UNIT
[Unit]
Description=HydraHive Radiostream – Verteiler (Icecast, nur 127.0.0.1)
After=network.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
ExecStart=/usr/bin/icecast2 -c $CFG/icecast.xml
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=$DATA/log

[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/systemd/system/$UNIT_LIQ.service <<UNIT
[Unit]
Description=HydraHive Radiostream – Programm (Liquidsoap)
After=network.target $UNIT_ICE.service
Requires=$UNIT_ICE.service

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
RuntimeDirectory=hydrahive-radiostream
RuntimeDirectoryMode=0750
ExecStart=/usr/bin/liquidsoap $DATA/radio.liq
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=$WEB $DATA

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload"

# --- Lief der Sender vorher (Update)? Dann wieder an, mit der zuletzt geschriebenen Konfiguration ---
if [ -f "$DATA/sender.on" ] && [ -s "$DATA/radio.liq" ] && [ -s "$CFG/icecast.xml" ]; then
  if [ -s "$DATA/nginx.conf" ]; then
    sudo -n bash -c "install -m 644 '$DATA/nginx.conf' /etc/nginx/sites-available/$SITE
ln -sf /etc/nginx/sites-available/$SITE /etc/nginx/sites-enabled/$SITE
if nginx -t >/dev/null 2>&1; then systemctl reload nginx; else rm -f /etc/nginx/sites-enabled/$SITE; echo 'Radiostream: Hörer-Seite abgelehnt (nginx -t)' >&2; fi"
  fi
  sudo -n bash -c "systemctl enable --now $UNIT_ICE $UNIT_LIQ >/dev/null"
  echo "Radiostream: Sender läuft wieder"
else
  echo "Radiostream: eingerichtet – Sender ist aus (im Modul „Sender starten“)"
fi
