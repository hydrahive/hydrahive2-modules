# Plan: Mediacenter V1

## Ziel

Das bestehende Dummy-Modul wird in fünf getrennten Etappen zu einem sicheren Cockpit für Treasure-Maps/Newznab-Suche, SABnzbd-Übergabe und Agentensteuerung ausgebaut. Jede Etappe erhält einen eigenen PR; die gemeinsame Service-Schicht wird von REST-API, Frontend und Agenten-Tools wiederverwendet.

Verbindliche Produkt- und Sicherheitsregeln stehen in `SPEC-V1.md`.

## PR-Schnitt

1. **E1 — Spec und Plan:** ausschließlich `SPEC-V1.md` und `PLAN-V1.md`.
2. **E2 — Newznab und Profile:** Credential-Zugriff, Client, Suche, Klassifikation, Result-Store, REST-Suche.
3. **E3 — SABnzbd:** sicherer NZB-Abruf/Upload, Job-Persistenz, Queue und Historie.
4. **Core-Voraussetzung:** unveränderter aktueller Benutzerturn im `ToolContext` als vertrauenswürdige Quelle für modulare Aktionsgrants.
5. **E4 — Agenten:** Intent-/Auswahlgate, vier Modul-Tools, Manifest-Freigabe und `mediacenter-workflow`-Skill.
6. **E5 — Cockpit:** Frontend, kanonisches `cockpit: true`, E2E-Livetest und Dokuabschluss.

Jeder nachfolgende PR beginnt erst, wenn seine Voraussetzungen grün und gemergt sind. Der kleine Core-PR kann nach E1 parallel zu E2/E3 entstehen, muss aber vor E4 gemergt sein.

## Geplante Dateien

Die konkreten Namen dürfen beim TDD-Red/Green-Zyklus nur dann abweichen, wenn die Verantwortungsgrenzen erhalten bleiben und der Plan im selben PR aktualisiert wird.

### Dokumentation

- `SPEC-V1.md` — verbindlicher Produkt-, API-, Tool- und Sicherheitsvertrag
- `PLAN-V1.md` — atomare Implementierungsreihenfolge und PR-Schnitt

### Core-Voraussetzung (separater Core-PR)

- `core/src/hydrahive/tools/base.py` — unveränderten Text des aktuellen Benutzerturns optional im `ToolContext` bereitstellen
- `core/src/hydrahive/runner/runner.py` — Feld ausschließlich aus dem authentifizierten `run(..., user_input)` setzen
- `core/tests/test_runner_tool_context.py` — beweisen, dass Tool-Argumente/Tool-Ausgaben den vertrauenswürdigen Turn nicht verändern

### Backend-Grundlage

- `backend/__init__.py` — Router, Tools und Migrationen registrieren
- `backend/config.py` — feste V1-Origins, Credential-Refs, Kategorie-Mappings und Limits
- `backend/models.py` — interne und REST-Pydantic-Modelle
- `backend/errors.py` — stabile Modulfehler ohne Upstream-Details
- `backend/credentials.py` — benutzergebundene Credential-Auflösung ohne Secret-Ausgabe
- `backend/http.py` — gehärteter Upstream-Transport, Origin-Pinning und redigierte Fehler
- `backend/audit.py` — strukturierte, secret-freie Auditereignisse

### Newznab und Profile

- `backend/newznab.py` — Caps, Suche und sicherer NZB-Abruf
- `backend/newznab_xml.py` — XXE-sicheres, größenbegrenztes XML-Parsing
- `backend/categories.py` — Newznab-/SAB-Mapping je Medientyp
- `backend/profiles.py` — serverseitige Release-Klassifikation und Ranking
- `backend/result_store.py` — kurzlebige, benutzergebundene Einmal-`result_id`s und Auswahlstatus
- `backend/intent_gate.py` — konservativer Agenten-Aktionsgrant aus dem vertrauenswürdigen aktuellen Benutzerturn
- `backend/routes_search.py` — Status, Verbindungstest und Suchroute

### SABnzbd und Jobs

- `backend/sabnzbd.py` — Version, Kategorien, NZB-Upload, Queue und Historie
- `backend/jobs.py` — Job-Persistenz, Idempotenz, Benutzerfilter und Statusabbildung
- `backend/routes_jobs.py` — Enqueue, Queue und Historie
- `migrations/001_mediacenter_jobs.sql` — Mediacenter-Job-/Audit-Metadaten und Indizes

### Agenten

- `backend/tools_search.py` — `mediacenter_search`
- `backend/tools_actions.py` — `mediacenter_enqueue`, `mediacenter_queue`, `mediacenter_history`
- `manifest.json` — `default_agent_tools: true` und V1-Beschreibung
- Skill `mediacenter-workflow` — als Projekt-Skill aus der finalen Spec anlegen

### Frontend

- `frontend/index.tsx` — Cockpit-Navigation und i18n
- `frontend/api.ts` — typisierte REST-Aufrufe
- `frontend/types.ts` — Frontend-Verträge
- `frontend/MediacenterPage.tsx` — Cockpit-Shell und Hauptzustand
- `frontend/ConnectionStatus.tsx` — Indexer-/SAB-Verbindung
- `frontend/SearchPanel.tsx` — Medien-Tabs und Suchfilter
- `frontend/ResultList.tsx` — Profilstatus, Gründe und Enqueue
- `frontend/QueuePanel.tsx` — eigene aktive Jobs
- `frontend/HistoryPanel.tsx` — eigene abgeschlossene/fehlgeschlagene Jobs

### Tests

- `tests/conftest.py` — isolierte Auth-/DB-/Transport-Fixtures
- `tests/test_credentials.py` — benutzergebundene Credential-Auflösung und Redaction
- `tests/test_http_security.py` — Origin-Pinning, Redirects, Timeouts und Response-Limits
- `tests/test_newznab.py` — Caps, Suchparameter und XML-Verträge
- `tests/test_profiles_video.py` — Sprache, Auflösung und verbotene Quellen
- `tests/test_profiles_books_audio.py` — E-Book-, Hörbuch-, Hörspiel- und Musikprofile
- `tests/test_result_store.py` — TTL, Benutzerbindung, Auswahlstatus, Replay und Parallelität
- `tests/test_intent_gate.py` — vertrauenswürdiger Turn, Such-vs.-Downloadabsicht, Grant-Bindung und Prompt-Injection-Fälle
- `tests/test_sabnzbd.py` — Kategorien, Upload, Queue, Historie und Fehlerabbildung
- `tests/test_jobs.py` — Idempotenz, Audit und Benutzerisolation
- `tests/test_routes.py` — Auth, Schemas, Limits und REST-Verträge
- `tests/test_agent_tools.py` — Tool-Schemas, Autonomiegrenzen und Secret-Freiheit

Produktionsdateien sollen möglichst unter 250 Zeilen bleiben; wachsende Verantwortlichkeiten werden vor dem jeweiligen Commit weiter getrennt.

## Implementierungsreihenfolge

### E1: Spec und TDD-Plan

- [x] Produktentscheidungen und Medienprofile festhalten
- [x] Treasure-Maps-Caps und authentifizierte Dummy-Suche live verifizieren
- [x] SABnzbd-Version und Kategorien live verifizieren
- [x] Sicherheitsgrenzen für SSRF, XML, Secrets, Prompt Injection und Result-Replay definieren
- [x] REST-, Tool-, Frontend- und Audit-Vertrag beschreiben
- [x] atomaren E2–E5-Plan einschließlich separater Core-Voraussetzung erstellen
- [x] Dokumente gegen bestehende Modul-/Tool-/Credential-Patterns reviewen
- [x] gezielter Diff- und Markdown-Sanity-Check
- [x] HydraHive-Strukturreview vor Commit
- [ ] Commit: `docs(mediacenter): V1-Spezifikation und Umsetzungsplan`
- [ ] Push und PR; CI grün

### E2 Task 1: Testgerüst und Credential-Auflösung

- [ ] RED: Fixture lädt `tresuere_token` nur für den aufrufenden Benutzer
- [ ] RED: fehlendes, leeres oder falsches Credential erzeugt stabilen Fehler ohne Wert/URL
- [ ] RED: API- und Tool-Serialisierung enthalten weder Credential-Ref noch Secret
- [ ] minimale Modul-Testumgebung mit isolierter Sessions-DB aufbauen
- [ ] `credentials.py`, Limits und stabile Fehler implementieren
- [ ] GREEN: Credential-/Redaction-Tests bestehen
- [ ] Commit: `feat(mediacenter): sichere Indexer-Credentials auflösen`

### E2 Task 2: Gehärteter Newznab-Transport und Caps

- [ ] RED: ausschließlich die kanonische Treasure-Maps-HTTPS-Origin ist zulässig
- [ ] RED: Redirect, Host-/Scheme-Wechsel, zu große Antwort und Timeout werden abgelehnt
- [ ] RED: Request-/Exception-Text enthält keinen API-Key
- [ ] gehärteten async-httpx-Transport mit festem Endpoint und `params` implementieren
- [ ] Caps abrufen und benötigte Suchtypen/Kategorien prüfen
- [ ] GREEN: Transport-/Caps-Tests bestehen
- [ ] Commit: `feat(mediacenter): Newznab-Verbindung absichern`

### E2 Task 3: Sicheres Newznab-Parsing und Suchvertrag

- [ ] RED: DTD, externe Entity und Entity Expansion werden abgelehnt
- [ ] RED: übergroße XML-, Titel- und Attributwerte werden begrenzt
- [ ] RED: malformed XML, fehlende/duplizierte Attribute, Namespace-Varianten, ungültige Größen/Datumswerte und unbekannte Kategorien werden stabil behandelt
- [ ] RED: jeder Medientyp erzeugt exakt seinen Suchtyp und seine Kategorien
- [ ] RED: Tool-/REST-Input kann Host, Pfad, URL oder Credential nicht beeinflussen
- [ ] XXE-sicheren Parser und bereinigtes internes Release-Modell implementieren
- [ ] `movie`, `tvsearch`, `book`, `search` und `music` anbinden
- [ ] GREEN: XML-/Suchtests bestehen
- [ ] Commit: `feat(mediacenter): Treasure Maps durchsuchen`

### E2 Task 4: Video-Profil

- [ ] RED: 1080p/1080i/2160p/UHD werden erkannt; 720p/SD/unbekannt abgelehnt
- [ ] RED: deutsche Kategorien/Metadaten bestätigen Deutsch; unbestätigtes `MULTI` reicht nicht
- [ ] RED: alle in der Spec genannten CAM-/Screener-/TS-/TC-/Workprint-/R5-Varianten werden abgelehnt
- [ ] RED: tokenbasierte Erkennung produziert keine offensichtlichen Teilstring-Falschpositive
- [ ] normalisierte Tokenisierung, Merkmalsextraktion und begründete Entscheidung implementieren
- [ ] GREEN: parametrisiertes positives/negatives Titelkorpus besteht
- [ ] Commit: `feat(mediacenter): Video-Releases sicher klassifizieren`

### E2 Task 5: Buch-, Hörbuch-, Hörspiel- und Musikprofile

- [ ] RED: deutsche EPUB/PDF zulässig, MOBI/AZW3 und nicht-deutsche Bücher abgelehnt
- [ ] RED: deutsche MP3/M4B-Hörmedien zulässig; Samples/Ausschnitte/unvollständig abgelehnt
- [ ] RED: Hörspiel und Hörbuch verwenden dieselbe Kategorie, bleiben aber als Medientyp getrennt
- [ ] RED: Musik akzeptiert alle Sprachen sowie FLAC/MP3 und bevorzugt innerhalb MP3 höhere Bitrate
- [ ] RED: Profilantwort setzt gruppenweit `quality_preference_required` bei geeigneten 1080+2160 und `format_preference_required` bei geeigneten FLAC+MP3
- [ ] RED: Sortierung und Ranking bleiben bei gleicher Eingabe deterministisch
- [ ] Profile und deterministisches Ranking implementieren
- [ ] GREEN: alle Medienprofiltests bestehen
- [ ] Commit: `feat(mediacenter): Buch- und Audio-Releases klassifizieren`

### E2 Task 6: Kurzlebige Result-IDs und Suchroute

- [ ] RED: IDs besitzen mindestens 128 Bit Entropie und laufen nach 15 Minuten ab
- [ ] RED: IDs sind an Benutzer und Medientyp gebunden
- [ ] RED: fremde, manipulierte und abgelaufene IDs werden ohne Informationsleck abgelehnt
- [ ] RED: Auswahlstatus wird mit der Ergebnisgruppe gespeichert und kann nicht per Enqueue-Argument verändert werden
- [ ] RED: Ergebniszahl und Feldlängen sind begrenzt; URLs/GUIDs bleiben intern
- [ ] RED: leere, Unicode-, Grenzlängen- und übergroße Suchanfragen liefern deterministische validierte Antworten
- [ ] thread-/async-sicheren TTL-Store und strukturierte Suchantwort implementieren
- [ ] Status-, Verbindungstest- und Suchroute mit per-User-Rate-Limit registrieren
- [ ] RED/GREEN: Suchlimit wird pro Benutzer erzwungen, andere Benutzer besitzen getrennte Buckets, Retry-Informationen enthalten keine Upstream-Details
- [ ] GREEN: Store-/Route-/Auth-Tests bestehen
- [ ] Security-Audit E2, vollständige Modultests, Ruff und Typ-/Import-Sanity
- [ ] Commit: `feat(mediacenter): sichere Suchergebnisse bereitstellen`
- [ ] Push und E2-PR; CI grün

### E3 Task 1: SABnzbd-Verbindung und Kategorieprüfung

- [x] RED: `sabnzb_token` wird nur für den aufrufenden Benutzer geladen
- [x] RED: SAB-Origin wird einmal kanonisiert, exakt gepinnt und kann nicht über Input geändert werden
- [x] RED: Redirects, Secret-Leaks und unerwartete JSON-Strukturen werden abgelehnt
- [x] RED: alle sechs Medientypen prüfen ihr festes Zielmapping gegen `get_cats`
- [x] Version-/Kategorie-Client und Verbindungstest implementieren
- [x] GREEN: SAB-Verbindungstests bestehen
- [x] Commit: `feat(mediacenter): SABnzbd-Verbindung prüfen`

### E3 Task 2: Sicherer NZB-Abruf

- [x] RED: nur gespeicherte, valide, `eligible` und nicht verbrauchte `result_id` ist zulässig
- [x] RED: NZB-Download darf ausschließlich von der festen Treasure-Maps-Origin kommen
- [x] RED: Redirect, falscher Content-Type, DTD/XXE, ungültiges XML und Größenlimit werden abgelehnt
- [x] Newznab-Identifier serverseitig auflösen und NZB mit harten Limits laden
- [x] keine Upstream-URL außerhalb des lokalen Call-Scopes speichern oder ausgeben
- [x] GREEN: SSRF-/XML-/Limit-Tests bestehen
- [x] Commit: `feat(mediacenter): NZB-Dateien sicher abrufen`

### E3 Task 3: Idempotenter SABnzbd-Upload

- [x] RED: Enqueue-Schema akzeptiert keine URL, Kategorie, Host oder Credential-Ref
- [x] RED: Kategorie stammt ausschließlich aus `media_type`
- [x] RED: parallele/repetierte Enqueue-Aufrufe erzeugen maximal einen SAB-Job
- [x] RED: Grant wird atomar bei `available → claimed` und vor dem Netzwerkzugriff verbraucht
- [x] RED: definitiver Fehler vor Request-Write setzt kontrolliert auf `available` zurück und erhöht den Versuchszähler, reaktiviert den Grant aber nicht
- [x] RED: Timeout/Abbruch nach möglichem Request-Write setzt `uncertain` und löst keinen Auto-Retry aus
- [x] RED: Queue-/History-Aufruf und erneutes Enqueue triggern Reconciliation über den deterministischen Übergabe-Identifier
- [x] RED: Fund in Queue/History setzt `uncertain → consumed`; Nichtfund oder Reconciliation-Fehler lässt `uncertain` unverändert und Enqueue liefert `enqueue_status_uncertain` ohne Upload
- [x] RED: nach 24 Stunden ohne Fund setzt Reconciliation `manual_review_required`; V1 erlaubt auch dann keinen erneuten Upload
- [x] RED: erst eine bestätigte oder reconciliierte SAB-Job-ID setzt `consumed`
- [x] atomare Zustandsmaschine und multipart NZB-Upload implementieren
- [x] SAB-Job-ID bereinigt zurückgeben
- [x] GREEN: Upload-/Replay-/Parallelitätstests bestehen
- [x] Commit: `feat(mediacenter): Treffer idempotent an SABnzbd übergeben`

### E3 Task 4: Job-Persistenz, Audit, Queue und Historie

- [x] RED: Migration ist idempotent und Tabellen sind modulpräfixiert
- [x] RED: Job gehört stabil zu Benutzer, Agent/Session und Medientyp
- [x] RED: Queue/History zeigen ausschließlich getrackte Job-IDs des aufrufenden Benutzers
- [x] RED: fremde SAB-Jobs, Secrets, Pfade und rohe Upstream-Fehler werden ausgefiltert
- [x] Job-/Audit-Store, Queue-/History-Abbildung und Routen mit strengem per-User-Enqueue-Limit implementieren
- [x] RED/GREEN: Enqueue-Rate-Limit, Queue-/History-Limits und getrennte Benutzer-Buckets funktionieren
- [x] GREEN: Migrations-/Isolations-/Audit-/Routentests bestehen
- [x] Security-Audit E3 und Live-Verbindungstest ohne echten Download
- [x] Commit: `feat(mediacenter): Queue und Historie benutzergebunden anzeigen`
- [x] Push und E3-PR; CI grün

### Core-Voraussetzung: Vertrauenswürdiger aktueller Benutzerturn im ToolContext

- [ ] RED: ein lokales Test-Tool erhält exakt den unveränderten Text des aktuellen authentifizierten Benutzerturns
- [ ] RED: Tool-Argumente, Assistant-Text und vorherige Tool-Ausgaben können dieses Feld nicht setzen oder verändern
- [ ] RED: Listen-/Multimodal-Input wird über dieselbe bestehende Runner-Normalisierung deterministisch zu Text; nicht-textuelle Blöcke erzeugen keine Aktionsabsicht
- [ ] optionales rückwärtskompatibles `current_user_input`-Feld in `ToolContext` ergänzen
- [ ] Runner setzt es ausschließlich beim Erzeugen des Kontexts aus `run(..., user_input)`
- [ ] bestehende ToolContext-Konstruktoren und Tests rückwärtskompatibel halten
- [ ] Core-Security-/Runner-Tests grün
- [ ] HydraHive-Strukturreview und separater Core-PR
- [ ] Commit: `feat(tools): aktuellen Benutzerturn vertrauenswürdig bereitstellen`

### E4 Task 1: Intent- und Auswahlgate

- [ ] RED: expliziter Downloadturn erzeugt einen kurzlebigen, einmaligen Grant; reine Suche/Verfügbarkeit und uneindeutige Texte nicht
- [ ] RED: Grant ist an Benutzer, Session, Medientyp und konkrete `result_id` gebunden
- [ ] RED: Indexer-Titel, Tool-Ausgaben und Modellargumente können keinen Grant erzeugen oder erweitern
- [ ] RED: offene 1080/2160- oder FLAC/MP3-Auswahl blockiert Enqueue trotz Downloadgrant
- [ ] RED: ein späterer vertrauenswürdiger Präferenzturn schaltet ausschließlich die passende Ergebnisgruppe frei
- [ ] konservative Intent-/Präferenzregeln mit sicherem False-negative-Verhalten implementieren
- [ ] keinen rohen Benutzerturn persistieren; nur nicht rückrechenbaren Fingerprint/Grantdaten
- [ ] GREEN: Intent-/Prompt-Injection-/Auswahltests bestehen
- [ ] Commit: `feat(mediacenter): Agentenaktionen an Benutzerintention binden`

### E4 Task 2: Lese-Tools

- [ ] RED: `mediacenter_search` verlangt Query und Media-Type mit engen Schemas
- [ ] RED: `mediacenter_queue` und `mediacenter_history` verwenden `ToolContext.user_id`
- [ ] RED: Tool-Ausgaben bleiben strukturiert, begrenzt und secret-/URL-frei
- [ ] dünne Wrapper um dieselbe Service-Schicht implementieren
- [ ] GREEN: Lese-Tool-Tests bestehen
- [ ] Commit: `feat(mediacenter): Such- und Status-Tools registrieren`

### E4 Task 3: Enqueue-Tool

- [ ] RED: Tool akzeptiert nur `result_id` und enge optionale Priorität
- [ ] RED: Profilablehnung, fehlender/fremder Grant, offener Auswahlstatus, falscher Benutzer, Ablauf und Replay scheitern
- [ ] RED: reine Suche plus manipulierter Release-Titel kann keinen Enqueue-Aufruf erfolgreich machen
- [ ] RED: Audit enthält Agent- und Session-ID, aber keine Secrets/URLs oder rohen Benutzerturn
- [ ] dünnen Wrapper um den idempotenten Enqueue-Service implementieren
- [ ] GREEN: Action-Tool-Tests bestehen
- [ ] Commit: `feat(mediacenter): Agenten an SABnzbd übergeben lassen`

### E4 Task 4: Manifest und Skill

- [ ] `default_agent_tools: true` und aktuelle V1-Beschreibung im Manifest setzen
- [ ] kanonischen Skill `mediacenter-workflow` mit eindeutiger Downloadabsicht, Medienart- und Format-/Qualitätsrückfragen schreiben
- [ ] Prompt-Injection-Regel und Verbot, Profilablehnungen zu umgehen, explizit aufnehmen
- [ ] Skill anhand repräsentativer Dialogfälle reviewen
- [ ] Security-Audit E4, vollständige Tool-/Modultests
- [ ] Commit: `feat(mediacenter): Agenten-Workflow dokumentieren`
- [ ] Push und E4-PR; CI grün

### E5 Task 1: Kanonisches Cockpit-Modul

- [ ] RED/Sanity: generierte/installierte Modulkopie übernimmt `cockpit: true` aus der Quelle
- [ ] `frontend/index.tsx` als kanonisches Cockpit-Modul markieren
- [ ] Radarr-/Sonarr-Dummytexte entfernen und V1-i18n ergänzen
- [ ] Frontend-Typen und API-Client erstellen
- [ ] TypeScript-Sanity grün
- [ ] Commit: `feat(mediacenter): Cockpit-Modul für V1 vorbereiten`

### E5 Task 2: Suche und Profilanzeige

- [ ] Verbindungsstatus und verständliche Konfigurationsfehler anzeigen
- [ ] Medien-Tabs und medientypspezifische Suchfelder bauen
- [ ] Treffer mit Größe, Alter, Sprache, Auflösung/Format, Ranking und Gründen anzeigen
- [ ] abgelehnte Treffer klar kennzeichnen und nicht enqueue-fähig machen
- [ ] zulässige Treffer an die Enqueue-Route übergeben
- [ ] Komponenten-/Browser-Test für Laden, Leerzustand, Fehler und Treffer
- [ ] Commit: `feat(mediacenter): Indexer-Suche im Cockpit bereitstellen`

### E5 Task 3: Queue, Historie und E2E

- [ ] eigene Queue mit Fortschritt, Geschwindigkeit, Restzeit und Status anzeigen
- [ ] eigene Historie mit abgeschlossen/fehlgeschlagen und bereinigtem Fehler anzeigen
- [ ] keine Cancel-/Delete-Aktion rendern
- [ ] Frontend-Build und Backend-/Tool-Gesamttests ausführen
- [ ] Browser-Boot und responsive Cockpit-Navigation prüfen
- [ ] Live-E2E: Suche → Profilbewertung → bewusst ausgewählter Testtreffer → SAB-Queue → Historie
- [ ] dabei Logs/Audit/API-/Tool-Ausgaben auf Secret-/URL-Leaks prüfen
- [ ] finaler Security- und HydraHive-Strukturreview
- [ ] Commit: `feat(mediacenter): Queue und Historie im Cockpit anzeigen`
- [ ] Push und E5-PR; CI grün

## Globale Definition of Done

- [ ] Alle Akzeptanzkriterien aus `SPEC-V1.md` sind nachweisbar erfüllt.
- [ ] Alle sechs PRs (E1–E5 plus Core-Voraussetzung) sind einzeln reviewbar, CI-grün und ohne fremde Änderungen.
- [ ] Treasure Maps und SABnzbd wurden live getestet, ohne API-Keys offenzulegen.
- [ ] Kein Endpoint oder Tool erlaubt frei eingebbare Netzwerkziele.
- [ ] Agenten können den vollständigen erlaubten Workflow ausführen und halten alle Rückfrageregeln ein.
- [ ] Das Mediacenter bleibt eigenständig und die kanonische Modulquelle enthält die Cockpit-Markierung.

## Bewusst später

- Multi-Indexer/Prowlarr
- Radarr/Sonarr
- Cancel/Delete mit eigenem Bestätigungs- und Rechtekonzept
- Reader/Player, Plex-Scan und lokale Bibliotheksorganisation
- Formatkonvertierung
- periodische oder Butler-gesteuerte automatische Suche
