# TV-Werkstatt E4: Entrümpeln

Zielbild: Reiter „Entrümpeln“ der Klick-Demo (`generated/tv-werkstatt/demo.html`): Stand, Sicherung, „Nach Update
prüfen“, „Alles zurück“, Liste vorinstallierter Apps nach Gruppen mit Schaltern. Nur abschalten, nie deinstallieren.

## Teil 1 – lesen (0.9.0)

- **Vom Fernseher lesen** (Auftrag `debloat_read`, nur lesend): Kennung (`ro.product.brand/name/device/model`,
  `ro.build.id`, `ro.build.version.incremental`) und `pm list packages` (alle, `-d` aus).
- **Listen:** `examples/*/debloat*.txt` und `tv.json` aus der Quelle am festen Stand (b953804, 477 Listen, 469 Ordner).
  Im Container als tar geholt, auf dem Server nur im Speicher gelesen (je Datei ≤ 200 KB, gesamt ≤ 8 MB), je Stand als
  JSON unter `data_dir/tvwerkstatt/debloat/` zwischengespeichert.
- **Passende Listen:** gleiche Marke (`tv.json`), Punkte für Build (30), Stand (15), Produkt (15), Gerät (10), Modell (5)
  im Kopf der Liste. Alle Listen mit der höchsten Punktzahl zählen (ab 40).
- **Empfohlen** ist, was die **Mehrheit** dieser Listen abschaltet **und keine bewusst anlässt** („Left enabled on
  purpose“ im Kopf oder `# paket` allein auf einer Zeile). Grund: Einzelne Listen tragen Vorlieben des Besitzers
  (TCL AU02: 3 von 11 schalten Netflix ab), und `com.tcl.ttvs` ist dort auch der Firmware-Updater (3 von 11 lassen es an).
- **Gesperrt:** Android selbst (Muster `CORE_RE` aus cleanyourtv `tools/recovery.py`), Startbildschirm, Original,
  Einrichtungs-Helfer (dafür ist das Aufspielen zuständig).
- **Gruppen** (fest, deutsch): Tracking und Fernwartung, Werbung und Inhalte, Ladendemo und Hotelmodus,
  Startbildschirm und Bildschirmschoner, Hilfe, Sonstiges – nach Stichworten aus Notiz, Paketname und Überschrift.

Gemessen 13.11.2026, echt und nur lesend:

| | Sony KD-60XF8305 (Android TV 9) | TCL 98" (Google TV 14, AU02) |
|---|---|---|
| Pakete gelesen / aus | 185 / 33 | 169 / 3 |
| passende Listen (Punkte) | 2 (75): sony-kd-55xf7596, -55xf8096 | 11 (75): tcl-55c745, -55c7k-uk, -55q7d-pro … |
| angezeigt | 44 | 53 |
| empfohlen und noch an | 1 (Alexa-Einrichtung, von Till bewusst an) | 13 (TCL-Werbung, Logs, Ladendemo, Alexa, Feedback) |

Listen holen beim ersten Mal ~10 s, Pakete lesen ~2 s.

## Teil 2 – Schalter (0.10.0)

- **Haken** je App (gesperrte nicht wählbar), „Empfohlene anhaken“, „Ausgewählte abschalten (n)“, „Wieder einschalten (n)“
  für Apps, die schon aus sind. Jede Aktion mit Rückfrage, die die Apps nennt.
- **Schutzprüfung am Fernseher** vor jedem Abschalten (nur lesend, wie cleanyourtv `tools/disable.sh`):
  `TV_INPUT_HARDWARE` in den angefragten Rechten (Schicht unter HDMI/AV/Tuner, #321), Apps, mit denen der Fernseher
  Eingänge (`vnd.android.cursor.item/channel`) oder Einstellungen öffnet. Nicht lesbar oder Dumps abgeschaltet → gilt als
  geschützt. Ist eine gewählte App betroffen, wird **nichts** abgeschaltet (`tvw_debloat_blocked`).
- **Sicherung:** Stand aller Pakete vor der ersten Änderung je Fernseher (`module_tvwerkstatt_debloat_backup`).
- **Schübe zu 4:** erst vermerken (`module_tvwerkstatt_debloat_changes`), dann `pm disable-user --user 0`, zurücklesen.
  Ist eine App danach nicht aus oder Home ein anderer als vorher → alles aus diesem Auftrag sofort wieder an, Vermerke
  nur dort weg, wo zurückgelesen wieder an. Scheitert auch das → `tvw_debloat_restore_incomplete`, Vermerk bleibt.
- **„Alles zurück“:** schaltet alles ein, was die Werkstatt abgeschaltet hat (nicht, was schon vorher aus war).
- **„Nach Update prüfen“:** liest neu; Apps, die die Werkstatt abgeschaltet hatte und die wieder an sind, werden gemeldet.
- Höchstens 40 Apps je Auftrag. Nie `uninstall`, nie `pm disable` ohne `-user`.

Gemessen 13.11.2026 am Sony, echt und ohne Änderung des Zustands (nur Apps „abgeschaltet“, die schon aus waren):
Schutzprüfung 1,0 s, Schub zu 4 Apps 0,5 s, Home danach gleich, Stand vorher = nachher (184 Pakete). Schutzprüfung am
TCL (nur lesend): `com.tcl.tv` und `com.tcl.tvinput` als Eingänge erkannt, 13 empfohlene Apps frei.

## Danach

App-Verwaltung mit dem App-Store des Fernsehers (Task 3f282d28): Play Store ist an beiden Geräten an, `market://details`
und `market://search` werden aufgelöst – Installieren selbst bestätigt man am Fernseher.
