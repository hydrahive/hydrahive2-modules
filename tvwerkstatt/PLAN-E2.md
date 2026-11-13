# TV-Werkstatt – Bauplan Etappe E2 (Seite wie die Demo, Desktop und Aussehen)

Gehört zu `SPEC.md` (Task 42c78c45). Stand 13.11.2026: von Till freigegeben („ja passt, bitte mache das fertig wie es
sein sollte“). Bausteine A und B gebaut (Zweig `feat/tvwerkstatt-e2-desktop`), C teilweise (Hochladen je Tageszeit;
mitgelieferte Themes fehlen noch).

## Zielbild: die Demo

Maßstab für jeden Schritt ist die Klick-Demo `generated/tv-werkstatt/demo.html` (Projektordner) mit den Bildern
`demo-desktop-abend.png`, `demo-desktop-nacht.png`, `demo-entruempeln.png`, `demo-zusaetze.png`. Till am 13.11.:
„wenn du mir schon demos schickst wie es werden soll, dann notiere dir das auch“ und „hochgradig flexibel und NICHT NUR
für den Sony“.

| Demo | E2 |
|---|---|
| Kopf mit Reitern Desktop · Entrümpeln · Zusätze · Geräte · Bauumgebung | ja; Entrümpeln und Zusätze zeigen, was kommt (E3/E4) |
| Desktop links: Gerät (Name, Modell, System, Adresse, Debugging), Bauumgebung, Stand auf dem Fernseher | ja, mit Gerätewahl oben |
| Desktop Mitte: Vorschau des Startbildschirms (Uhr, Datum, Pillen, Titel, Leiste, Raster, Tageszeit) | ja, aus den echten Apps des Geräts |
| Desktop Mitte: 1 Bauen → 2 Auf den Fernseher schieben, Nur das Aussehen schieben, Zurück zum Original | ja |
| Desktop rechts: Hintergrund je Tageszeit, eigenes Bild, abdunkeln, Kacheln pro Reihe, Apps ziehen + Schalter | ja |
| Geräte: Liste, hinzufügen, prüfen | ja (aus E1) |
| Bauumgebung: Container, Java, Android-Werkzeuge, Quelle | ja (aus E1) |

## Wie es funktioniert (cleanyourtv b953804)

- Die App ist für alle Fernseher dieselbe. Das Aussehen ist ein **Theme**: `config.json` plus Bilder unter
  `/sdcard/Android/data/com.gathin.tvhome/files/`, geschrieben über `content://com.gathin.tvhome.theme` (Kopie als
  Rückfall), danach `theme_revision` und Home neu starten. Kein Neubau. Ablauf wie `tools/theme.sh`.
- 150 Schlüssel (themes/README.md). E2 nutzt: `dock_apps`, `hidden_apps`, `app_labels`, `columns`, `rows_below_dock`,
  `background_color`, `wallpaper`, `wallpaper_moods` (`morning`/`evening`/`night`), `wallpaper_rotation_minutes`,
  `wallpaper_dim`, `dock_opacity`, `clock_format`, `show_greeting`, `greeting_name`, `sky_intensity`.
- 29 mitgelieferte Themes als Ausgangspunkt.

## Bausteine

### A Seite wie die Demo (Reiter, Gerätewahl, Desktop-Gerüst)
- Reiter; Desktop mit drei Spalten wie die Demo; Gerät wählen (mehrere Fernseher).
- Vorhandenes aus E1 wandert in die Reiter Geräte und Bauumgebung; Bauen/Schieben/Zurück als Schritte im Desktop.

### B Apps vom Gerät und Aussehen je Gerät
- Apps lesen (nur lesend): `LEANBACK_LAUNCHER`-Aktivitäten, je App Name (`aapt2 dump badging`, deutsch zuerst) und
  Banner bzw. Symbol aus dem APK (im Container, nie auf dem Server). Gemessen am Sony: 20 Apps, 257 MB APKs, Abzug je
  App ~0,7 s → Bilder werden zwischengespeichert, nur neue Pakete werden gezogen.
- Aussehen je Gerät gespeichert (Tabelle), Vorschau zeigt Leiste und Raster mit echten Bannern.
- „Nur das Aussehen schieben“: config.json im Server bauen, im Container auf den Fernseher schreiben, Home neu starten.

### C Hintergründe
- Bild hochladen je Tageszeit, auf dem Server verkleinern (1920×1080, JPEG, ≤ ca. 300 KB), Abdunkeln, Wechsel.
- Mitgelieferte Themes als Ausgangspunkt (Einstellungen und Bilder aus dem festen Stand der Quelle).

## Nicht in E2
Entrümpeln (E4), Zusätze (E3), Google-TV-Kopplung mit wechselndem Port und Gerätesonderfälle aus den 468 Profilen
(eigener Baustein „alle Fernseher“, nach E2).

## Gemessen (13.11.2026, Sony, echt)

- Apps lesen (nur lesend): 20 startbare Apps in 0,2 s gelistet, Namen und Bilder aus den APKs in 26 s, 18 mit Bild
  (YouTube und Play Store haben verschleierte Pfade `res/dN.png` – Fund, behoben: genau diese Datei nehmen). Bilder
  zusammen 260 KB auf dem Server.
- Aussehen schieben ohne Neubau: config.json (4 Spalten, Leiste Plex/Emby/Netflix/YouTube, Timer ausgeblendet, Gruß „Till“)
  plus ein Nachtbild in 5,8 s, Größe zurückgelesen, Home neu gestartet. Bildschirmfoto vom Fernseher:
  `generated/tv-werkstatt/e2-sony-aussehen.png` – 4 Kacheln, Reihenfolge wie eingestellt, „GUTEN TAG, TILL“, Timer nicht da.
  Danach das Theme wieder entfernt (nur `theme_revision` bleibt, wie bei cleanyourtv `--reset`).
- Nicht sichtbar geprüft: eigener Name „Joyn TV“ (Joyn lag außerhalb des Bildausschnitts); Hintergrundbild (das
  Probebild war ein sehr dunkler Verlauf).
