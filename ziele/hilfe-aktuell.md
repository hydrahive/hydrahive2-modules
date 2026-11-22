# Zieldokument: Hilfe und Handbuch auf aktuellem Stand

> **Status:** FREIGEGEBEN (Till, 22.11.2026: „ALLES komplett auf den neusten Stand, vom Core bis zu den Modulen“)
> **Verbindlich für:** jeden Auftrag, der einen Hilfe-Artikel (Kern oder Modul) schreibt oder ändert.
> **Regel:** Ein Artikel ist fertig, wenn jede Aussage darin am **aktuellen Code** (origin/main) belegt ist.
> Was nicht belegt werden kann, kommt nicht hinein. Raten ist verboten.

## 1. Zielbild
1. Jede Seite und jedes Modul von HydraHive hat **einen deutschen Hilfe-Artikel**, der beschreibt, was es **heute** kann.
2. **Modul-Hilfe liegt im Modul** (`<modul>/frontend/help/de/<modul-id>.md`), nicht im Kern. Sie wird mit dem Modul
   gepflegt. Die Kern-Hilfe liegt unter `frontend/src/i18n/help/de/<topic>.md` im Kern-Repo.
3. Das GitHub-Wiki wird **nur** aus diesen Dateien gebaut. Discord-Texte sind keine Quelle mehr.
4. Zielgruppe: Laien. Kurze Sätze, Bedienung aus Sicht der Oberfläche, keine Code-Details.

## 2. Aufbau eines Artikels (verbindlich)
```
# <Name> – <ein halber Satz, wofür>

<2–3 Sätze: was es ist und wem es hilft>

## So startest du
<nummerierte Schritte: installieren/freigeben, öffnen, erstes Ergebnis>

## Was du damit machen kannst
<Abschnitte je Bereich/Reiter der Oberfläche, jeweils mit fettem Namen wie in der Oberfläche>

## Mit Buddy und Agenten        (nur wenn das Modul Agenten-Werkzeuge hat)
<welche Werkzeuge, was man fragen kann, was NICHT geht>

## Gut zu wissen
<Grenzen, Datenschutz, Kosten, Freigaben, Vault, typische Fehlermeldungen>

*Stand: <Modul> <Version aus manifest.json>, <Datum>*
```
Kein „Was noch kommt“, keine Pläne. Nur was heute im Code ist.

## 3. Quellen (in dieser Reihenfolge)
1. Code auf origin/main: Frontend-Texte (Beschriftungen, Knöpfe, i18n), Backend-Routen, Werkzeuge (`tools`), Manifest.
2. SPEC/PLAN-Dokumente im Modul nur als Hinweis, **nicht als Beleg** (sie beschreiben oft Geplantes).
3. Alte Hilfe- oder Discord-Texte nur als Vorlage für Ton und Aufbau, jede Aussage neu prüfen.

## 4. Verboten
- Interne Adressen, Rechnernamen, Benutzernamen, echte Daten von Till/Familie, Tokens, Server-Pfade.
- Behauptungen ohne Beleg im Code. Funktionen, die nur in SPEC/PLAN stehen.
- Änderungen an Code außer dem Hilfe-Artikel, der Manifest-Version und (beim Umzug) dem Entfernen des alten Kern-Artikels.

## 5. Abnahme-Punkte je Artikel
| # | Prüfung |
|---|---|
| H1 | Datei am richtigen Ort (`<modul>/frontend/help/de/<id>.md` bzw. Kern-Pfad), Aufbau wie §2 |
| H2 | Belegliste im Bericht: je Abschnitt Datei:Zeile, aus der die Aussage stammt |
| H3 | Jede Beschriftung in Fettdruck kommt wörtlich so in der Oberfläche vor (i18n-Datei/TSX belegt) |
| H4 | Keine verbotenen Inhalte (§4); Prüfung per grep im Bericht gezeigt |
| H5 | Stand-Zeile mit aktueller Manifest-Version; Modul-Version angehoben; `scripts/check_version_bump.py` grün |
| H6 | Abweichungen zur alten Hilfe/Discord-Fassung benannt (was war falsch/veraltet) |
