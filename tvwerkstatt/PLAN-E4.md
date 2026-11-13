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

## Teil 2 – Schalter (nächster PR)

Schalter je Paket, Sicherung des Stands vor dem ersten Abschalten, in Schüben mit Home-Prüfung danach, „Alles zurück“,
„Nach Update prüfen“ (was eine neue Firmware wieder eingeschaltet hat). Erster echter Schub am TCL gemeinsam mit Till.
