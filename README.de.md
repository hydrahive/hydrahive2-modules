# HydraHive2 Modul-Hub

> 🇬🇧 [English version](README.md)

First-Party-Modul-Hub für [HydraHive2](https://github.com/hydrahive/hydrahive2.0).

Jedes Top-Level-Verzeichnis ist ein installierbares Modul. `hub.json` ist der
Hub-Index, den das HydraHive-Backend nutzt, um diese Module aufzulisten,
zu pullen und zu installieren. Der Katalog enthält aktuell **21 Einträge:
20 Endnutzer-Module plus ein Entwickler-Beispiel-Template**.

## Installation

Ein Modul wird über den Modul-Manager des HydraHive-Backends installiert
(`Admin Cockpit → Modules`), der:

- das Modul aus diesem Repository oder zusätzlichen `HH_MODULE_HUB_GIT_URLS` pullt;
- das Backend nach `HH_DATA_DIR/modules/<id>` und das Frontend nach
  `frontend/src/modules/<id>` im Core-Checkout kopiert;
- deklarierte Modul-Migrationen ausführt;
- das React-Frontend neu baut und einen Backend-Restart anfordert.

Modul-Backend-Code wird als Teil des HydraHive-Prozesses geladen.
Modul-Frontend-Code wird in die Hauptanwendung kompiliert. Deinstallation
entfernt die Modul-Dateien, lässt aber Modul-Datenbank-Tabellen und -Daten
bewusst stehen. Das erforderliche Tasks-Modul ist im Core-Repository
gebündelt und wird aus der gebündelten Quelle repariert, wenn es fehlt.

## Katalog

Der Katalog wird zur Laufzeit aus `hub.json` gelesen. Die Tabelle unten
listet die aktuellen Manifest-Versionen, Abhängigkeiten, deklarierte
Summary und verifizierte Contributions auf. Verifizierte Contributions
stammen aus dem generierten `frontend/src/modules/index.generated.ts` nach
einem Build, der das `frontend/index.tsx` jedes Moduls lädt.

| Modul | Manifest | Abhängig von | Verifizierte Contributions | Summary |
|---|---:|---|---|---|
| **Archiver** | 2.0.2 | — | router, migration | Archiviert Webseiten, Forum-Threads und Dokumente in dauerhafter, durchsuchbarer Form. |
| **Atelier** | 1.6.5 | `videoeditor` | router, frontend routes, nav, i18n, `slotBlocks`, `mediaWorkflows` | AI-Media-Workshop für Bilder, Video, Musik und Kurzfilme, projekt-gebunden mit konsistenten Charakteren. |
| **Blueprint** | 1.0.2 | — | router, migration | Visueller Node-Canvas, um Layout- und Flow-Ideen nonverbal an einen Agenten zu vermitteln. |
| **Brettspiele** | 1.0.2 | — | router, migration, `buddyWidgets` | Klassische Brettspiele wie Schach, spielbar gegen einen Agenten, mit gespeicherten Ergebnissen. |
| **Cryptoboard** | 1.1.2 | — | router, migration, Agent-Tools, Butler-Typen, Poll-Jobs | Live-Crypto-Dashboard mit Charts, Watchlist, Portfolio, Trades, Alerts und Indikatoren. |
| **Deep Research** | 1.0.2 | — | router, migration, `research_report`-Tool | Mehrstufige, quellenbasierte Web-Recherche, die einen zitierten Bericht erstellt. |
| **Haushaltsbuch** | 1.5.3 | — | router, migration | Lokales Haushalts-Ledger mit Bank-Import, automatischer Kategorisierung und experimentellem Read-Only-Lidl-Plus-Beleg-Sync. |
| **Home Assistant** | 1.0.2 | — | router, migration, 4 Tools | Verbindet Home Assistant: Entities listen/lesen, Templates rendern und Services aufrufen. |
| **Mediacenter** | 0.8.1 | — | router, migration, 5 Tools, Queue/History | Treasure-Maps-Suche mit Medien-Profilen, idempotenter SABnzbd-Übergabe und Per-User-Queue/History. |
| **Mining** | 0.7.2 | — | router, Geräte-Router, migration, Poll-Job, frontend routes, nav, i18n, Rig-Client, Agent-Tools, Skill | Verwaltet GPU-Rechner im Netz für Kryptex: Live-Erträge, Rechner koppeln/freigeben/sperren, Benchmark, automatisches Umschalten auf den besten Coin, Watchdog, Energie-Steuerung (PV). |
| **Minigames** | 1.0.2 | — | router, migration, `buddyWidgets` | Eine Sammlung kleiner Browser-Spiele für kurze Pausen. |
| **Musicplayer** | 1.1.1 | — | router, migration, `buddyMediaWidgets` | Projektgebundene, rollenbasierte Audio-Bibliothek im Buddy-Media-Slot; speichert updatefest unter `media/audio`, unterstützt Upload, Import, Streaming und Download. |
| **Notizbuch** | 1.0.2 | — | router, migration | Einfaches Notizbuch für Texte und Ideen, verfügbar über Projekte hinweg. |
| **Meine Akte** | 1.0.2 | — | router, migration, 2 Read-Tools, `buddyWidgets` | Persönliche Patientenakte für Befunde, Medikamente und Diagnosen, mit strukturierten Importen. |
| **Scratchpad** | 1.0.2 | — | router, 2 Tools, nav, i18n, routes | Geteiltes Notizbuch zwischen User und Agent mit getrennten, nicht geteilten Zonen. |
| **Storyteller** | 0.17.0 | — | router, frontend routes, nav, i18n, Agent-Tools | Bücher und Geschichten schreiben (Roman, Sach-, Lernbuch) mit Kapitel-Navigator, Steckbriefen und KI-Vorschlägen. Bücher liegen als Markdown/JSON im Projektordner, Versionsprüfung gegen stilles Überschreiben, echte KI über die HydraHive-Modelle mit Modellwahl je Buch. Ghostwriter „Szene schreiben“: die KI schreibt eine ganze Szene aus Zusammenfassung, Steckbriefen und Gedächtnis, live sichtbar, erst nach Annehmen übernommen; „Kapitel/Buch“ schreibt viele Szenen im Hintergrund (Gliederung aus Idee, Fortschritt, Abbrechen, vorhandener Text wird zum Vorschlag); „Interview“ stellt je Kapitel Fragen, man antwortet getippt oder diktiert, daraus entsteht das Kapitel in der eigenen Stimme; „Im Chat“ lässt den Projekt-Agenten das Buch lesen und Szenentext, Titel, Zusammenfassung und Perspektive einer Szene neue und geänderte Steckbriefe oder neue Kapitel als Vorschlag ablegen, den man übernimmt oder verwirft – im Chat-Fenster direkt neben dem Editor (lange Szenen liest er in Abschnitten, ein deutlich kürzerer Vorschlag zeigt eine Warnung; das Projekt-Cockpit springt nicht mehr in den Buch-Chat); Herkunft je Szene und KI-Anteil werden angezeigt. „Neues Buch“ kann ein eigenes Projekt mit Schreib-Team anlegen: ein Autor für den Chat (ohne Shell, Dateien, Git) und sieben Helfer (Plausibilität, Recherche, Lektor, Kritiker, Kreativ, Struktur, Steckbriefe), alle mit dem Modell des Buchs; die Helfer legen Hinweise und Recherche-Notizen (mit Quellen) ab, die im Reiter „Team“ und als Markierung im Navigator erscheinen; Knöpfe dort schicken einen Helfer ohne Chat los (Szene prüfen, Lektorat, Kritisch lesen, Aufbau prüfen, Steckbriefe pflegen) – vorher mit Kostenschätzung, abbrechbar, danach mit den tatsächlichen Kosten; eine abschaltbare Kostengrenze je Auftrag (Eingabe + Ausgabe) gilt für Hintergrund-Läufe, einzelne Szenen und Team-Aufträge – darüber startet ein Auftrag nur mit „Trotzdem“, ein Team-Auftrag endet zwischen zwei Runden und behält seine Kosten; nichts geht verloren: ein Vorschlag, der einen anderen ersetzt, sagt das („ersetzt einen Vorschlag vom Lektor“), ersetzte und verworfene Vorschläge stehen unter „Frühere Vorschläge“ und lassen sich zurückholen, gelöschte Szenen kehren an ihre alte Stelle und gelöschte Bücher in die Liste zurück (Papierkorb); auch große Bücher bleiben schnell (Gedächtnis ohne Volltexte, Dateiarbeit außerhalb der Ereignisschleife: ein Buch mit 500 Szenen schätzt in unter einer halben Sekunde statt 27 s und hält den Server nie an); ein Buch aus einem normalen Projekt lässt sich in ein eigenes Projekt mit Team umziehen (Sicherung bleibt im Papierkorb des alten Projekts); braucht die Freigabe „storyteller.create_project“ (standardmäßig nur Admins). Braucht Kern mit Prosa-Editor (TipTap). |
| **Aufgaben** | 1.0.1 | — | router, migration, 4 Tools, `buddyWidgets`, `workspaceTabs` | Persistentes Task-Management, das Chat-Sessions überdauert. Der Agent kann Tasks erstellen, aktualisieren und abschließen. |
| **Video-Editor** | 0.1.2 | — | router, frontend routes, nav, i18n | Web-Video-Editor mit Timeline, Filmstrip-Preview und Hybrid-Export. |
| **Voice** | 0.8.0 | — | router, frontend routes, nav | Voicebox für den HydraHive-Voice-Assistenten (HA Voice PE) mit Voice-, Volume- und Wake-Word-Settings. |
| **VoIP** | 0.2.0 | — | authentifizierter Statusrouter, typisierter Gatewayvertrag + Fake, frontend routes, nav, i18n | Installierbare Grundlage für projektgebundene VoIP-Zugänge, Telefonaufträge und Gesprächsarchive; Telefoniefunktionen sind noch nicht aktiv. |
| **OpenTor OSINT** | 0.1.0 | — | router, migration, 4 read-only Tools, frontend routes, nav | Kontrollierte Tor-basierte OSINT- und Threat-Intelligence-Recherche, standardmäßig deaktiviert. |
| **AI-Sicherheit** | 0.1.0 | — | router, migration, Polling-Job | Authentifizierter Adapter für lokale AI-Infra-Guard-Infrastruktur-Scans; kein privilegierter Scanner-Dienst wird automatisch installiert. |
| **Beispiel-Modul** | 1.0.1 | — | router, migration | Minimales Beispiel-Modul, das als Template für neue Module dient. |

Versionen, Summaries und die Spalte „Verifizierte Contributions" stammen
aus den Modul-Manifesten und den aktuellen `frontend/index.tsx`-Exports.
Der Hub wird unabhängig vom HydraHive-Core-Repository aktualisiert; die
installierte Version auf einem bestimmten HydraHive-Host kann abweichen,
bis der Administrator ein Update ausführt.

## Ein neues Modul erstellen

Die Repository-Konvention für ein neues Modul `foo` ist:

```text
foo/
├── manifest.json    # id, name, version, depends, summary, ...
├── backend/
│   ├── __init__.py  # register_routes, register_tools, run_migrations
│   └── ...
├── frontend/
│   ├── index.tsx    # exportiert routes, nav, i18n, optional buddyWidgets,
│   │                # workspaceTabs, slotBlocks, mediaSources, mediaWorkflows
│   └── ...
└── migrations/      # SQL- oder Python-Migrationen, angewendet bei Install/Update
```

Das `example`-Modul ist eine bewusst kleine, funktionierende Referenz.
Der Modul-Manager von HydraHive kopiert das Modul bei der Installation
nach `HH_DATA_DIR/modules/<id>` und kopiert `frontend/` nach
`frontend/src/modules/<id>` im Core-Source-Tree, bevor die Anwendung neu
gebaut wird.

Manifest-Versions-Bumps sind für sichtbare Änderungen erforderlich; der
`spec-guard`-CI-Workflow im Core-Repository blockiert Modul-Updates, die
die Manifest-Version nicht ändern.

## Sicherheit und Vertrauen

Der Backend-Code eines Moduls läuft innerhalb des HydraHive-Prozesses. Das
Frontend eines Moduls wird in die Hauptanwendung kompiliert. HydraHive
sandboxt Modul-Python-Code nicht. Administratoren sollten nur Module
installieren, die sie reviewt haben oder aus einer vertrauenswürdigen
Quelle stammen.

## Sprachkonvention der Dokumentation

Siehe [I18N.md](I18N.md) zur englisch/deutschen Spiegel-Konvention.

## Lizenz und Beitrag

Jedes Modul ist Teil des HydraHive-Projekts. Modul-Code steht unter
derselben Lizenz wie das Core-Projekt, sofern keine modul-spezifische
Lizenz deklariert ist. Bug-Reports und Pull-Requests sind in diesem
Repository willkommen.
