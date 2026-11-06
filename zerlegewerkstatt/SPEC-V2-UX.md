# Zerlege-Werkstatt V2 – UX- und Interaktionsspezifikation

**Stand:** 03.11.2026
**Status:** Freigegeben am 03.11.2026
**Bezug:** [`SPEC-V2.md`](SPEC-V2.md), [`SPEC-V2-ARCHITEKTUR.md`](SPEC-V2-ARCHITEKTUR.md)

## 1. UX-Ziel

Die Zerlege-Werkstatt darf Agentenarbeit nicht hinter einem Ladeindikator verbergen.
Der Nutzer soll jederzeit verstehen:

- was untersucht wird,
- warum dieser Schritt erfolgt,
- welcher Agent arbeitet,
- welches REA-Werkzeug verwendet wird,
- welche Wirkung und Berechtigung der Schritt hat,
- was tatsächlich beobachtet wurde,
- welche Grenzen und offenen Fragen bestehen,
- wie er eingreifen kann.

Transparenz bedeutet nicht, den Nutzer mit vollständigem JSON zu überfordern. Die
Oberfläche bietet eine verständliche Standardansicht und verlustfreien Zugriff auf
Details.

## 2. Informationsarchitektur

Die V2-Seite besteht aus fünf dauerhaft erreichbaren Bereichen:

1. **Untersuchungen** – Liste, Status, Ziel, Fortschritt und letzte Aktivität.
2. **Arbeitsraum** – Plan, Live-Aktivität, Chat und Eingriff.
3. **Artefakte** – Originale, extrahierter Baum und Beziehungen.
4. **Evidence** – Befunde, Quellen, Coverage, Limitations und Rohdaten.
5. **Rekonstruktion** – Pflichten, Dossier, Lücken, Nachbauplan und Tests.

Zusätzlich gibt es **Umgebung & Provider** für Container-, REA- und
Providerstatus.

## 3. Untersuchungsübersicht

Jede Karte zeigt:

- Titel und Ziel,
- Projekt,
- Besitzer und Beteiligte,
- Zustand,
- Fortschritt nach Planpunkten, nicht nach geschätzter Prozentzahl allein,
- aktive Agenten,
- wartende Nutzerentscheidung,
- offene Pflichtpunkte,
- letzte Aktivität,
- REA-/Image-Revision,
- Aktionen: Öffnen, Pausieren/Fortsetzen, Archivieren, Löschen.

Statusfarben dürfen nie die einzige Information sein. Text und Symbol sind Pflicht.

Leerer Zustand:

- „Neue Untersuchung“ als primäre Aktion,
- kurze Erklärung: Datei/Verzeichnis auswählen, Ziel beschreiben, Plan prüfen,
- kein Fallaktenjargon als notwendige Voraussetzung.

## 4. Neue Untersuchung

Der Einrichtungsdialog hat vier Schritte.

### 4.1 Ziel

- Titel,
- natürliche Fragestellung,
- gewünschte funktionale Kompatibilität,
- optional bekannte Hinweise und Hypothesen.

Beispiel:

> Analysiere die Firmware dieser Lampe. Finde heraus, wie Pairing, lokale Steuerung,
> Statusmeldungen und Updates funktionieren, damit wir eine kompatible lokale
> Implementierung bauen können.

### 4.2 Artefakte

Möglichkeiten:

- Upload,
- Projektdatei oder Projektverzeichnis,
- Samba-Eingang,
- bereits vorhandenes Artefakt,
- später: URL/Website, Gerät, Prozess oder Mitschnitt als ausdrücklich freigegebenes Ziel.

Vor dem Start zeigt die UI:

- Name,
- Typ soweit erkannt,
- Größe,
- Hash nach Aufnahme,
- Herkunft,
- Aufnahmefehler,
- ob ein Verzeichnis als Snapshot erfasst wird.

### 4.3 Zweck und Berechtigung

- Zweck auswählen,
- Untersuchungsberechtigung bestätigen,
- optional Herkunft/Owner notieren,
- verständlicher Hinweis auf eigene Verantwortung.

### 4.4 Arbeitsmodus

- **Geführt** – Standard,
- **Manuell** – jeder Call bestätigen,
- **Autopilot** – sichere freigegebene Schritte automatisch.

Die zwingenden Sicherheitsfreigaben bleiben in allen Modi erhalten.

## 5. Arbeitsraum

Desktopaufteilung:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Untersuchung · Status · Pause · Stop · Modus · Providerzustand      │
├──────────────────┬────────────────────────────────┬──────────────────┤
│ Plan & Agenten   │ Live-Aktivität / Ergebnisse   │ Chat & Eingriff  │
│                  │                                │                  │
│ Schritte         │ Agent-/REA-Ereignisse          │ Koordinator      │
│ Abhängigkeiten   │ Ergebniszusammenfassungen      │ Hinweise         │
│ offene Fragen    │ Freigaben und Blocker          │ Dateien ergänzen │
└──────────────────┴────────────────────────────────┴──────────────────┘
```

Auf kleinen Bildschirmen werden die drei Spalten als Reiter dargestellt. Keine
horizontale Pflichtnavigation.

## 6. Kopfzeile und globale Aktionen

Immer sichtbar:

- Untersuchungsstatus,
- Containerstatus,
- aktiver Agent/Schritt,
- `Pausieren`,
- `Aktuellen Schritt abbrechen`,
- `Gesamte Arbeit stoppen`,
- `Fortsetzen`,
- Arbeitsmodus,
- wartende Freigaben,
- Link zum Audit.

Semantik:

### Pausieren

- startet keine neuen Schritte,
- laufender sicherer Schritt darf regulär enden,
- UI sagt ausdrücklich, ob noch ein Schritt ausläuft.

### Aktuellen Schritt abbrechen

- sendet Cancellation,
- zeigt Cleanupstatus,
- Schritt wird `cancelled` oder bei unsicherem Cleanup `blocked/quarantined`.

### Gesamte Arbeit stoppen

- stoppt den Agentenlauf,
- cancelt aktive Calls,
- startet Cleanup,
- löscht keine Evidence und keine Originale.

## 7. Analyseplan

### 7.1 Darstellung

Der Plan ist ein gerichteter, aber als Liste verständlich bedienbarer Ablauf. Jeder
Punkt zeigt:

- Titel und Fragestellung,
- Begründung,
- Agent,
- Zielartefakte,
- Abhängigkeiten,
- erwartetes Werkzeug oder Kategorie,
- Wirkungsklasse A–F,
- Status,
- erwartetes Ergebnis,
- offene Blocker,
- entstandene Evidence.

### 7.2 Nutzeraktionen

Für noch nicht gestartete Punkte:

- bearbeiten,
- deaktivieren,
- überspringen mit Begründung,
- verschieben, soweit Abhängigkeiten erhalten bleiben,
- Priorität ändern,
- Spezialisten wechseln,
- „als Nächstes ausführen“,
- „nach diesem Schritt pausieren“.

Für laufende Punkte:

- Details öffnen,
- Agentenhinweis senden,
- abbrechen,
- nach Abschluss pausieren.

Für abgeschlossene Punkte:

- Ergebnis und Evidence öffnen,
- erneut mit geänderten Parametern planen,
- Folgefrage erstellen,
- als unzureichend markieren,
- mit anderer Evidence vergleichen.

### 7.3 Planänderungen durch Agenten

Ein Agent darf neue Punkte nur als `proposed` einfügen. Die UI hebt hervor:

- warum der Punkt vorgeschlagen wurde,
- welche Evidence ihn ausgelöst hat,
- welche neue Wirkungsklasse entsteht,
- ob bestehende Freigabe reicht.

Safe statische Folgepunkte innerhalb des genehmigten Scopes dürfen im geführten
Modus automatisch `approved` werden. Eine höhere Wirkungsklasse nie.

## 8. Sichtbare Agentenzusammenarbeit

### 8.1 Agentenleiste

Jeder Agent erscheint mit:

- Rolle und Name,
- Status `idle`, `planning`, `working`, `waiting`, `blocked`, `done`,
- aktuellem Planpunkt,
- letzter Aktivität,
- verwendeter Modellfamilie,
- Link zu seinem Arbeitsverlauf.

### 8.2 Delegationen

Eine Delegation ist ein sichtbares Ereignis:

- Auftraggeber,
- Empfänger,
- genaue Frage,
- übergebene Artefakte/Evidence,
- Scope und Berechtigungen,
- Start/Ende,
- Ergebnis oder Fehler.

Der Nutzer kann:

- eine Zusatznotiz senden,
- Priorität ändern,
- einen Auftrag abbrechen,
- einen weiteren Spezialisten beauftragen,
- Ergebnis annehmen oder als unzureichend zurückgeben.

### 8.3 Kein Black Box „KI analysiert“

Ein alleiniger Spinner mit „Analyse läuft“ ist unzulässig. Mindestens Planpunkt,
Agent, Werkzeug und Ziel müssen sichtbar sein.

## 9. REA-Werkzeugereignisse

Jeder Call erhält eine Karte.

### 9.1 Eingeklappte Ansicht

- REA-Werkzeugname,
- verständliche Kurzbeschreibung,
- Agent,
- Ziel,
- Wirkungsklasse,
- Status und Dauer,
- Anzahl/Typ entstandener Ergebnisse,
- Coverage-/Limitationshinweis.

### 9.2 Aufgeklappte Ansicht

- exakter Werkzeugname,
- REA-/Provider-Version,
- redigierte Argumente,
- Schema-Digest,
- Start/Ende,
- Ergebnis-ID und Evidence-IDs,
- Confidence/Authority,
- Coverage,
- Limitations,
- Retry-/Reconnecthistorie,
- Cleanupstatus,
- Link zur vollständigen strukturierten Antwort.

Secrets und sensible Tokens werden nie angezeigt. Pfade werden auf
Untersuchungs-Relative reduziert, sofern kein Admin-Detail erforderlich ist.

## 10. Chat und aktive Mitarbeit

Der Chat ist Teil der Untersuchung, nicht eine getrennte allgemeine Session.

Der Nutzer kann:

- dem Koordinator eine neue Frage stellen,
- einen sichtbaren Spezialisten adressieren,
- einen Planpunkt oder Befund zitieren,
- Artefakte und Evidence verlinken,
- eine Hypothese formulieren,
- eine Antwort auf einen Blocker geben,
- sagen „untersuche diese Funktion tiefer“,
- sagen „überspringe die dynamische Analyse“,
- sagen „vergleiche das mit Version B“.

Eine Nutzernachricht während eines laufenden Schritts wird sichtbar als
`pending_intervention` erfasst. Sie darf nicht still in einen bereits laufenden
Toolcall hineingemischt werden. Der Nutzer wählt:

- nach aktuellem Schritt anwenden,
- aktuellen Schritt abbrechen und sofort neu planen,
- nur als Notiz speichern.

## 11. Freigabedialoge

Ein Freigabedialog nennt verständlich:

- was ausgeführt wird,
- warum es nötig ist,
- welcher Agent es beantragt,
- welches Ziel betroffen ist,
- ob Code ausgeführt wird,
- ob Netzwerk oder Gerät verwendet wird,
- welche Daten den Container verlassen können,
- Laufzeit und Gültigkeit,
- Cleanup-/Rollbackverhalten.

Aktionen:

- einmal erlauben,
- für diesen Planpunkt und Zeitraum erlauben,
- ablehnen,
- Parameter einschränken,
- zurück zum Plan.

„Dauerhaft alles erlauben“ ist für C–F nicht verfügbar.

## 12. Artefakt- und Extraktionsansicht

### 12.1 Baum

Der Baum zeigt:

- Originale,
- Container/Archive/Partitionen,
- extrahierte Dateien,
- abgeleitete Beziehungen,
- Hash und Größe,
- Typ/Architektur,
- Extraktionsstatus,
- Gaps und fehlende Extraktoren,
- zugehörige Planpunkte und Evidence.

### 12.2 Aktionen

- als neues Analyseziel markieren,
- an Spezialisten übergeben,
- sichere Vorschau öffnen,
- Hash kopieren,
- herunterladen, wenn berechtigt,
- mit anderem Artefakt vergleichen,
- Herkunftspfad anzeigen,
- Folgefrage erstellen.

Keine extrahierte Datei wird durch Vorschau ausgeführt.

## 13. Evidence-Explorer

Filter:

- Artefakt,
- Agent,
- Werkzeug,
- Confidence,
- Authority,
- Provider,
- Planpunkt,
- Zeitraum,
- offene Limitations,
- Widerspruch.

Jede Evidence-Ansicht zeigt:

- Aussage oder Beobachtung,
- Subject,
- Fundstelle,
- Quelle und Provider,
- Hash/Identität,
- Confidence/Authority,
- Coverage,
- Limitations,
- Beziehungen,
- Parent-/View-Digest.

Der Nutzer kann Evidence:

- zu einem Planpunkt verknüpfen,
- kommentieren,
- als relevant/irrelevant für den gewählten Scope markieren,
- mit anderer Evidence vergleichen,
- als Widerspruch melden,
- vollständig herunterladen.

Manuelle Kommentare werden nie als `observed`-Evidence ausgegeben.

## 14. Ergebnis- und Rohdatenansicht

Standardmäßig werden Summary und relevante Collections gezeigt. Experten können:

- Collections seitenweise lesen,
- bestimmte Funktionen/Module/Zeilen auswählen,
- vollständiges JSON/JSONL öffnen,
- REA-Analyseviews erzeugen,
- Rohbundle herunterladen,
- Schema und Digest prüfen.

Die Oberfläche zeigt klar, ob eine Ansicht vollständig, paginiert, begrenzt,
truncated, partial oder unknown ist.

## 15. Rekonstruktionsansicht

### 15.1 Pflichtenkatalog

Gruppen:

- Komponenten,
- Funktionen,
- Schnittstellen/Protokolle,
- Datenmodelle,
- UI/Verhalten,
- Persistenz,
- Fehlerfälle,
- Installation/Boot/Update,
- Vergleich/Verifikation.

Jede Pflicht besitzt:

- Status `open`, `in_progress`, `verified`, `unknown`, `blocked`, `not_applicable`,
- Owner,
- erforderliche Evidence,
- vorhandene Evidence,
- Restfrage,
- vorgeschlagene Probe,
- Einfluss auf Rekonstruktionsstatus.

### 15.2 Dossier

Der Dossiereditor zeigt generierten Text neben Evidence-Matrix. Nutzer und Agent
können Text ändern; jede fachliche Aussage bleibt mit Evidence oder explizitem
`unknown` verbunden.

### 15.3 Abschluss

Die UI zeigt nie nur „100 %“. Sie zeigt beispielsweise:

```text
32 erforderliche Pflichten
27 verifiziert
3 unbekannt
1 blockiert
1 widersprüchlich
Status: Teilweise rekonstruierbar
```

## 16. Umgebung und Provider

Darstellung:

- Basisimage und Revision,
- REA-Version und Katalogdigest,
- Containerzustand,
- freie Ressourcen,
- Providerliste,
- installiert/verfügbar/unavailable,
- Lizenz-/Setuphinweis,
- letzter Healthcheck,
- ausstehendes Update mit Katalogdiff.

Ein fehlender kommerzieller Provider wird nicht als allgemeiner Modulfehler gezeigt.

## 17. Fehler- und Blocker-UX

Fehlerkarte enthält:

- verständliche Zusammenfassung,
- betroffenen Schritt und Agenten,
- stabilen Fehlercode,
- ob Arbeit gestartet wurde,
- ob ein Retry sicher ist,
- Cleanupstatus,
- erhaltene Teil-Evidence,
- konkrete nächste Optionen.

Unzulässig:

- endlose automatische Retries,
- „Analyse fehlgeschlagen“ ohne Phase,
- technisch erfolgreiche Anzeige bei truncated/partial,
- Verlust bereits erzeugter Evidence,
- erneutes Starten eines möglicherweise wirksamen Calls ohne Nutzerentscheidung.

## 18. Ereignisvertrag

Die UI konsumiert geordnete Ereignisse mit fortlaufender Sequenznummer:

- `investigation.state_changed`
- `plan.created`
- `plan.step_changed`
- `agent.delegated`
- `agent.state_changed`
- `rea.call_requested`
- `rea.call_started`
- `rea.call_progress`
- `rea.call_completed`
- `rea.call_failed`
- `rea.call_cancelled`
- `evidence.published`
- `artifact.discovered`
- `artifact.extracted`
- `grant.requested`
- `grant.decided`
- `runtime.cleanup_changed`
- `obligation.changed`
- `report.version_created`

Reconnect verwendet `after_seq` und darf keine Ereignislücke still übergehen.
Snapshots gleichen ältere Ereignisse aus, ohne deren Audit zu ersetzen.

## 19. Barrierefreiheit und Internationalisierung

- Deutsch und Englisch vollständig.
- Status nie nur über Farbe.
- Tastaturbedienung für Plan, Freigaben und Dialoge.
- Fokus bleibt nach Liveupdates stabil.
- `aria-live` nur für wichtige Status-/Freigabeänderungen, nicht für jeden Logeintrag.
- Tabellen und Bäume besitzen lineare Alternativdarstellung.
- Rohdatenansichten sind kopierbar und umbrechen kontrolliert.
- Mobile Ansicht ohne horizontales Seitenoverflow.

## 20. UX-Akzeptanzkriterien

- Nutzer kann eine Untersuchung ohne Kenntnis von REA-Befehlen anlegen.
- Vor dem ersten nichttrivialen Schritt ist der Plan sichtbar und änderbar.
- Jeder laufende Schritt zeigt Agent, Ziel und REA-Werkzeug.
- Delegationen und Spezialistenergebnisse sind sichtbar.
- Nutzer kann pausieren, aktuellen Schritt abbrechen und fortsetzen.
- Nutzer kann einen noch nicht gestarteten Planpunkt bearbeiten und priorisieren.
- Nutzer kann eine Zusatzdatei und einen Hinweis während der Untersuchung ergänzen.
- C–F-Aktionen besitzen verständliche, gebundene Freigabedialoge.
- Resultate zeigen Coverage und Limitations; `partial` sieht nicht wie Erfolg aus.
- Extrahierte Firmware erscheint als navigierbarer Baum mit Gaps.
- Evidence ist von Aussagen aus erreichbar und umgekehrt.
- Vollständige Rohdaten bleiben in Expertenansicht zugänglich.
- Ein Stream-Reconnect verliert keine sichtbaren Agenten-/Toolereignisse.
- Rekonstruktionsstatus nennt Counts und offene Pflichten statt einer unbelegten 100-%-Anzeige.
- Desktop und 390×844 funktionieren ohne unbedienbare Bereiche oder horizontales Seitenoverflow.
