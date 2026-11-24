#!/usr/bin/env bash
# Vitrine-Kiosk einrichten (Statuszentrale, SPEC-STATUSZENTRALE.md). Aufruf aus install.sh, läuft als root (sudo -n bash).
# Argumente: <Modulordner> <Dienst-Nutzer> <Kiosk-URL>
# Idempotent: zweimal ausführen ergibt denselben Zustand. Rückbau: kiosk-uninstall.sh.
set -euo pipefail

MODULE_ROOT="$1"
SERVICE_USER="$2"
URL="$3"
KIOSK=hydrahive-kiosk
HOME_DIR="/home/${KIOSK}"
CONF=/etc/hydrahive2-vitrine
SDDM=/etc/sddm.conf
SESSION=/usr/share/xsessions/hydrahive-vitrine-kiosk.desktop

# --- Pakete (EVDI vom Ubuntu-Kernel, signiert; Openbox; Werkzeuge für xrandr/xset/xhost) ---
DEBIAN_FRONTEND=noninteractive apt-get -qq install -y --no-install-recommends \
  linux-modules-evdi-generic libevdi1 openbox x11-xserver-utils >/dev/null
command -v firefox >/dev/null || echo "Vitrine-Kiosk: Firefox fehlt – das Dashboard bleibt aus, bis er installiert ist" >&2

# --- EVDI beim Start laden, ein Gerät ---
echo evdi > /etc/modules-load.d/hydrahive2-vitrine-evdi.conf
echo "options evdi initial_device_count=1" > /etc/modprobe.d/hydrahive2-vitrine-evdi.conf
modprobe evdi initial_device_count=1 || true

# --- Kiosk-Nutzer: Passwort gesperrt, kein SSH, Home unter /home (Firefox-Snap braucht das) ---
id "${KIOSK}" >/dev/null 2>&1 || useradd -m -d "${HOME_DIR}" -s /bin/bash -c "HydraHive Vitrine Kiosk" "${KIOSK}"
passwd -l "${KIOSK}" >/dev/null
usermod -aG video,input "${KIOSK}"
usermod -aG video "${SERVICE_USER}"
mkdir -p /etc/ssh/sshd_config.d
echo "DenyUsers ${KIOSK}" > /etc/ssh/sshd_config.d/50-hydrahive2-vitrine-kiosk.conf
systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true

# --- Sitzung + Konfiguration ---
# Die Kiosk-URL enthält den Kiosk-Schlüssel → nur für den Kiosk-Nutzer lesbar, und Firefox bekommt sie NICHT als
# Argument (sonst sieht sie jeder per ps), sondern über eine lokale Startseite, die weiterleitet.
install -d -m 755 "${CONF}"
printf '%s\n' "${SERVICE_USER}" > "${CONF}/service-user"
install -d -m 700 -o "${KIOSK}" -g "${KIOSK}" "${HOME_DIR}/vitrine"
_esc="$(printf '%s' "${URL}" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e 's/"/\&quot;/g')"   # HTML-Attribut
(umask 077 && cat > "${HOME_DIR}/vitrine/start.html" <<EOF
<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=${_esc}"><body style="background:#0b1220">
EOF
)
chown "${KIOSK}:${KIOSK}" "${HOME_DIR}/vitrine/start.html"
rm -rf "${HOME_DIR}/.vitrine"                       # alte Ablage bis 0.7.2 (Firefox-Snap durfte sie nicht lesen)
install -m 755 "${MODULE_ROOT}/extension/kiosk-session.sh" "${CONF}/kiosk-session.sh"
# Openbox ohne Menü/Tastenkürzel (Standard öffnet per Rechtsklick ein Terminal – mit BT-Tastatur eine Shell)
install -m 644 "${MODULE_ROOT}/extension/kiosk-openbox.xml" "${CONF}/openbox.xml"
mkdir -p "$(dirname "${SESSION}")"
cat > "${SESSION}" <<EOF
[Desktop Entry]
Name=HydraHive Vitrine-Kiosk
Exec=${CONF}/kiosk-session.sh
Type=Application
EOF

# --- Firefox: nur lokale Seiten, keine Erstlauf-/Update-Seiten ---
install -d -o "${KIOSK}" -g "${KIOSK}" "${HOME_DIR}/firefox"
cat > "${HOME_DIR}/firefox/user.js" <<'EOF'
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.aboutwelcome.enabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("app.update.enabled", false);
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("security.fileuri.strict_origin_policy", true);
EOF
chown "${KIOSK}:${KIOSK}" "${HOME_DIR}/firefox/user.js"
mkdir -p /etc/firefox/policies
cat > /etc/firefox/policies/policies.json <<'EOF'
{"policies": {
  "WebsiteFilter": {"Block": ["<all_urls>"], "Exceptions": ["http://127.0.0.1/*", "http://127.0.0.1:*/*", "file:///home/hydrahive-kiosk/vitrine/*"]},
  "DisableAppUpdate": true, "DisableTelemetry": true, "DontCheckDefaultBrowser": true,
  "OverrideFirstRunPage": "", "OverridePostUpdatePage": "", "DisableDeveloperTools": true
}}
EOF

# --- sddm: /etc/sddm.conf hat Vorrang vor sddm.conf.d (am Gerät geprüft) → ersetzen, Original einmalig sichern ---
[ -f "${SDDM}" ] && [ ! -f "${CONF}/sddm.conf.vor-vitrine" ] && cp -a "${SDDM}" "${CONF}/sddm.conf.vor-vitrine"
[ -f "${CONF}/sddm.conf.vor-vitrine" ] || : > "${CONF}/sddm.conf.vor-vitrine"
cat > "${SDDM}" <<EOF
# Von HydraHive Vitrine geschrieben (Kiosk-Sitzung). Original: ${CONF}/sddm.conf.vor-vitrine
[Autologin]
User=${KIOSK}
Session=hydrahive-vitrine-kiosk
Relogin=true
EOF
# --- laufenden Kiosk-Firefox beenden: die Sitzungsschleife startet ihn sofort neu → neue Seite nach Modul-Update ---
pkill -u "${KIOSK}" -f "firefox --kiosk" 2>/dev/null || true
# Openbox liest seine Konfiguration nur beim Start. Läuft noch eines OHNE die eigene Datei (Standard-Menü mit Terminal),
# sddm neu starten → Autologin startet die Sitzung frisch. NICHT `loginctl terminate-user`: das beendet auch den
# sddm-helper, sddm meldet dann „Process crashed“ und meldet nicht neu an (19.10.2026 17:24 auf .2, Display schwarz).
# Läuft Openbox schon mit der Datei, bleibt die Sitzung (kein Schwarzbild bei jedem Update).
if pgrep -u "${KIOSK}" -x openbox >/dev/null 2>&1 \
   && ! pgrep -u "${KIOSK}" -f -- "--config-file /etc/hydrahive2-vitrine/openbox.xml" >/dev/null 2>&1; then
  systemctl restart sddm 2>/dev/null || true
fi
echo "Vitrine-Kiosk eingerichtet (Nutzer ${KIOSK}, Sitzung hydrahive-vitrine-kiosk) – wirksam nach Neustart von sddm"
