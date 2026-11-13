# TV-Werkstatt – Startbildschirm und Zusätze für Android-TV per Klick

> Neues Modul `tvwerkstatt`. Wunsch Till 13.11.2026: „modul bauen das den passenden container zur verfügung stellt und den
> ganzen desktop dann hübsch zu managen, klicken zum bauen und irgendwie auf den tv schieben“, Zusätze „auch flexibel im
> modul mit einbauen, addon hinzufügen“, fremde Repos „ja erlaubt“. Name „TV-Werkstatt“ von Till bestätigt.
> **Status: von Till freigegeben am 13.11.2026. Gebaut wird Etappe für Etappe, in kleinen PRs.** Task 42c78c45.

## Problem

Der Sony im Wohnzimmer (KD-60XF8305, Android TV 9) ist seit dem 12./13.11. von Hand entrümpelt und hat einen neuen
Startbildschirm (cleanyourtv, com.gathin.tvhome). Jeder Schritt dahin war Handarbeit in der Shell: Container aufsetzen,
Android-Werkzeuge laden, bauen, per ADB schieben, Aussehen als JSON schreiben. Das kann nur ein Agent oder ein Entwickler.
Till will das Aussehen, die Apps und Zusätze selbst in HydraHive verwalten.

Der Sony ist das **Testgerät**, das Debugging bleibt dort an (Till 13.11.). Das eigentliche Gerät kommt später: ein
**TCL 98C7L** (SQD-Mini LED, Google TV). Das Modul muss deshalb von Anfang an mehrere Geräte und beide Arten tragen.

## Ziel

Eine Seite „TV-Werkstatt“ (nur Admins), auf der man

- einen Fernseher einträgt und prüft, ob er erreichbar ist,
- den Startbildschirm per Klick baut, installiert und wieder durch das Original ersetzt,
- das Aussehen gestaltet (Apps, Leiste, Hintergrundbilder je Tageszeit, Filmloops als Bildschirmschoner) und hinüberschiebt,
- Zusätze aus dem Katalog oder aus einem beliebigen GitHub-Repo hinzufügt, baut, installiert und entfernt,
- die Liste abgeschalteter Werbe- und Tracking-Apps verwaltet.

## Was es schon gibt (nicht neu bauen)

| Was | Wo | Nutzung |
|---|---|---|
| Startbildschirm, 36 Zusätze, Themes, Abschaltlisten, ADB-Werkzeuge in Python | github.com/Gathin23/cleanyourtv (MIT) | Quelle, an einem festen Commit |
| `tools/tv.py`, `b64push.py`, `disable.sh`, `restore.sh`, `theme.sh`, `manage.py` | cleanyourtv `tools/` | laufen im Container |
| Incus-Container aus einem Modul, eigenes Netz mit Sperrliste | Module `vibe`, `hydralabor` (`incus.py`, `network.py`, `container.py`) | Muster, kein Import |
| `hydrahive.containers.incus_client` | Kern | Aufruf von incus |
| Steuerung im Alltag (Sender, Lautstärke, Ein/Aus) | Modul `fernseher` (Zweig `feat/fernseher-e1`) | bleibt dort, keine Doppelung |

## Befund aus dem Probelauf (13.11.2026, von Hand, Task 42c78c45)

- Bau im Incus-Container (Ubuntu 24.04, unprivilegiert, 8 Kerne, 6 GiB): openjdk 17, Android cmdline-tools 11076708,
  platforms;android-34, build-tools 34.0.0 (445 MB). `./gradlew assembleRelease` des Startbildschirms: 30 s.
- Prüfsummen vor dem Bau geprüft: Gradle-Wrapper gegen gradle.org, cmdline-tools gegen Googles `repository2-3.xml`.
- Installation über `launcher/build-and-install.sh` mit `SKIP_BUILD=1`: 11 s, danach Home = neuer Startbildschirm.
- Netz `hhnat0` hat keinen Namensdienst am Gateway: im Container musste die Namensauflösung von Hand gesetzt werden.
- Ohne Sperrliste erreichte der Container den Server selbst (SSH, HTTPS) und den Router. Das darf das Modul nicht.
- Gradle hinterließ trotz `--no-daemon` einen Java-Prozess. Container nach dem Bau anhalten.

## Zwei Gerätearten (aus den Listen von cleanyourtv, Stand b953804)

| | Sony KD-60XF8305 (Test) | TCL 98C7L (kommt) |
|---|---|---|
| System | Android TV 9 (SDK 28), am Gerät gelesen | Google TV 14 – angenommen nach 55C7K/65C7K/65C7L, am Gerät nicht gelesen |
| Startbildschirm ab Werk | `com.google.android.tvlauncher` | `com.google.android.apps.tv.launcherx` |
| Live-TV/HDMI-App | `com.sony.dtv.tvx` | `com.tcl.tv` |
| Debugging | USB-Debugging, Port 5555 offen | Kabelloses Debugging mit Kopplungscode (verschlüsselt); Port 5555 antwortete bei 65C7L ohne Kopplung |
| Besonderheit | – | `setupwraith` kann das gespeicherte WLAN besitzen und Home übernehmen; `com.tcl.ttvs` ist Samba-Tracking UND Firmware-Updater |
| Vorlage Abschaltliste | `examples/sony-kd-55xf8096` | `examples/tcl-55c7k-uk`, `tcl-65c7k-google-tv`, `tcl-65c7l-google-tv` (Board G08, Build UTT2.250416.001) |

Folgen: Geräte-Tabelle statt eines festen Fernsehers; Verbindung wahlweise Port 5555 (`tv.py`) oder gekoppelt über
Googles `adb` (`TV_ADB_BINARY`, `tools/native-adb.md`), dann wechselt der Port und die Sperrliste muss ihm folgen.
Ob der 98C7L dasselbe Board und denselben Build hat, liest das Modul beim Eintragen aus.

## Rahmen und Entscheidungen

1. **Alles Fremde läuft im Container.** Gradle führt die Bau-Skripte eines Repos als Code aus, und die ADB-Werkzeuge von
   cleanyourtv sind ebenfalls fremder Code. Beides läuft nur im Container `hh-tvwerkstatt`, nie auf dem Server, der in der
   Gruppe `incus-admin` ist.
2. **Eigenes Netz `hhtvw0` mit Sperrliste `hhtvw-acl`** nach dem Muster von vibe: Internet ja, Server, Router, Tailscale und
   das übrige Heimnetz nein. Ausnahme: jede eingetragene Fernseher-Adresse, nur TCP 5555. Weil incus `reject` vor `allow`
   wertet (Befund hydralabor, 30.10.), wird die Ausnahme durch Herausrechnen der Adresse aus den gesperrten Bereichen
   gebaut, die übrigen Ports des Fernsehers bleiben gesperrt. Ob das so greift, wird in Baustein 2 gemessen.
3. **Feste Stände.** Jede Quelle (cleanyourtv und jedes fremde Repo) wird an einem Commit festgenagelt. Neuer Stand nur auf
   Knopfdruck, mit Anzeige, was sich geändert hat. Nie automatisch.
4. **Fremde Repos sind erlaubt** (Till 13.11.). Vor dem ersten Bau zeigt das Modul: Lizenz, Stand, Sterne, Alter, minSdk
   gegen die Android-Version des Geräts, Rechte aus dem Manifest. Rechte mit Folgen werden rot markiert
   (`REQUEST_INSTALL_PACKAGES`, `UPDATE_PACKAGES_WITHOUT_USER_ACTION`, `WRITE_SECURE_SETTINGS`), gelb
   (`SYSTEM_ALERT_WINDOW`, `RECEIVE_BOOT_COMPLETED`, Vordergrunddienst, Nutzungsdaten, Standort). Gebaut wird erst nach
   Bestätigung. Installationsskripte fremder Repos laufen nicht: das Modul baut die App und installiert sie selbst.
5. **Nur abschalten, nie deinstallieren** (Systempakete). Kein Root, keine Umgehung von Herstellersperren.
6. **Debugging am Fernseher gehört dem Nutzer.** Das Modul zeigt, ob Port 5555 offen ist, und bietet „Debugging
   ausschalten“ an (`settings put global adb_enabled 0`, Wirkung in Baustein 7 zu messen). Es schaltet nie selbst ein.
7. **Signierschlüssel bleibt erhalten.** Apps werden mit einem Schlüssel des Moduls signiert. Er wird im Datenordner des
   Moduls gesichert, weil ein Update mit anderem Schlüssel erst eine Deinstallation verlangt.
8. **ADB-Schlüssel des Moduls** liegt im Container und in der Sicherung. Der Fernseher fragt beim ersten Kontakt einmal
   „USB-Debugging zulassen?“.
9. Zugriff nur für Admins (`module.tvwerkstatt`, `admin_only`). Keine Werkzeuge für Agenten in E1.

## Aufbau

- Ein Container für alle Fernseher (`hh-tvwerkstatt`), angelegt beim ersten „Einrichten“, angehalten, wenn nichts läuft.
- Tabellen: Geräte (Name, Adresse, Android-Stand, Startbildschirm, Zustand), Quellen (Repo, Commit, Lizenz, geprüft am),
  Bauten (Quelle, Teil, Commit, Prüfsumme, Zustand, Protokoll), Installiert (Gerät, Paket, Commit, Prüfsumme).
- Lange Aufträge (Einrichten, Bauen, Installieren) mit Schritt-Anzeige nach dem Muster `vibe/backend/jobs.py`.
- Seite mit Reitern: Desktop, Zusätze, Entrümpeln, Geräte, Bauumgebung (Klick-Demo `generated/tv-werkstatt/demo.html`).

## Etappen

| Etappe | Inhalt |
|---|---|
| E1 Bauen und schieben | Gerüst, Netz, Container, Gerät eintragen und prüfen, Startbildschirm bauen, installieren, zurück zum Original, Debugging-Anzeige |
| E2 Aussehen | Apps (Leiste, Reihenfolge, ausblenden, umbenennen), Spalten, Farben, Hintergrundbilder je Tageszeit, Abdunkeln, mitgelieferte Themes, Bildschirmschoner mit Filmloops (Zusatz photo-screensaver) |
| E3 Zusätze | Katalog aus cleanyourtv, fremdes Repo per Adresse, Prüfung, Bauen, Installieren, Entfernen, Aktualisieren |
| E4 Entrümpeln | Abschaltliste je Gerät mit Schaltern, Sicherung, Prüfen nach Firmware-Update, alles zurück |
| E5 HydraHive auf dem Fernseher | eigene kleine TV-App als Kachel und Bildschirmschoner |

Video hinter den Kacheln ist keine Etappe: dafür gibt es nur eine Abspaltung des Startbildschirms
(dev-bhaskar8/cleanyourtv, Zweig `wallpaper-video`). Erst lesen und auf dem Sony messen, dann entscheiden.

## Fehlercodes (Auswahl, de/en)

`tvw_no_incus`, `tvw_network_failed`, `tvw_net_open` (Sperrliste greift nicht), `tvw_setup_failed`, `tvw_checksum_mismatch`,
`tvw_tv_unreachable`, `tvw_adb_closed`, `tvw_adb_unauthorized` (Rückfrage am Fernseher nicht bestätigt), `tvw_sdk_too_old`,
`tvw_build_failed`, `tvw_install_failed`, `tvw_home_not_switched`, `tvw_busy`.

## Nicht enthalten

Root, Bootloader, eigenes Betriebssystem; Deinstallieren von Systempaketen; automatische Updates; dauerhaft offenes Netz-ADB;
Docker; Steuerung im Alltag (Modul `fernseher`); Agenten-Werkzeuge (frühestens nach E3).

## Tests (TDD)

Wie vibe: `fake_incus` für alle incus-Aufrufe, ein gefälschtes `tv.py` im Container für ADB, keine echten Container und
kein echter Fernseher in pytest. Echte Proben gegen den Sony nur mit Tills OK, je Etappe aufgeschrieben.

## Akzeptanzkriterien E1

- Ein Admin richtet die Bauumgebung per Klick ein; der Container erreicht das Internet, nicht den Server, nicht den Router,
  vom Fernseher nur Port 5555 (Probe im Container, Ergebnis sichtbar).
- Er trägt den Fernseher ein, sieht Modell, Android-Version und ob Debugging offen ist.
- „Bauen“ erzeugt den Startbildschirm mit sichtbarem Protokoll und Prüfsumme; „Installieren“ macht ihn nach Rückfrage zu
  Home; „Zurück zum Original“ stellt den Google-Startbildschirm wieder her. Beides am Sony geprüft.
- Nicht-Admins sehen die Seite nicht und erreichen keine Route (Test).
- Alle Suiten grün, keine Datei über 200 Zeilen.

## Offen (braucht Messung oder Till)

1. TCL 98C7L: System, Build und Debugging-Weg am Gerät lesen, sobald er da ist (Board G08 wie 55/65C7K?).
2. Greift die Ausnahme für Port 5555 in der Sperrliste (Messung Baustein 2)?
3. Schaltet `settings put global adb_enabled 0` das Netz-Debugging am Sony wirklich ab (Messung Baustein 7)?
4. Der Probe-Container `hh-tvwerkstatt` von Hand (auf `hhnat0`) muss vor der Abnahme weg, sonst kollidiert der Name.
   Löschen nur mit Tills OK.
5. Der Sony vertraut heute dem Schlüssel aus dem Probelauf (`_work/cleanyourtv/tools/adbkey` auf dem Server). Nach
   dem Umzug in den Container fragt er neu; den alten Schlüssel am Fernseher widerrufen (Entwickleroptionen).
