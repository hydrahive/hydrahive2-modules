# Plan: Zerlege-Werkstatt V2

**Stand:** 03.11.2026
**Status:** Freigegeben am 03.11.2026
**Spezifikationen:** [`SPEC-V2.md`](SPEC-V2.md), [`SPEC-V2-ARCHITEKTUR.md`](SPEC-V2-ARCHITEKTUR.md), [`SPEC-V2-UX.md`](SPEC-V2-UX.md)

## Ziel

Nach Abschluss dieses Plans existiert eine transparente HydraHive-Zerlege-Werkstatt,
die das echte REA als MCP-Server in isolierten Untersuchungsumgebungen nutzt. Alle
REA-Werkzeuge sind kataloggetrieben erreichbar; Agent und Nutzer können gemeinsam
planen, analysieren, eingreifen, Evidence prüfen und ein belastbares
Rekonstruktionsdossier erzeugen. Das Modul bildet keine eigene fachliche
REA-Untermenge mehr.

## Harte Regeln für die Umsetzung

1. Kein Produktcode vor ausdrücklicher Freigabe aller V2-Dokumente.
2. Jeder Implementierungstask beginnt mit einem fehlschlagenden Test.
3. Kein fachliches REA-Tool wird im Modul hardcodiert.
4. Keine vollständige Evidence wird durch eine gekürzte LLM-Ansicht ersetzt.
5. Jede Etappe hat einen realen End-to-End-Nachweis, nicht nur Mocks.
6. Statische und dynamische Analyseumgebungen bleiben getrennt.
7. Keine Etappe heißt fertig, solange ein High-/Medium-Security-Fund offen ist.
8. Änderungen in `hydrahive2` und `hydrahive2-modules` werden in getrennten Branches und PRs geführt.
9. Vor jedem Commit: relevante Tests, Ruff/TypeScript, `hh-review`; bei Security-Code zusätzlich `security-audit`.
10. Alte 0.4.0-Daten werden nie für Tests oder Migrationen gelöscht.

## Repositories und geplante Dateien

### HydraHive Core

- `core/src/hydrahive/mcp/client/base.py` – strukturierter MCP-Vertrag.
- `core/src/hydrahive/mcp/client/http.py` – strukturierte HTTP-Ergebnisse erhalten.
- `core/src/hydrahive/mcp/client/stdio.py` – strukturierte stdio-Ergebnisse erhalten.
- `core/tests/test_mcp_structured_content.py` – Transportparität und Rückwärtskompatibilität.
- optional `frontend/src/features/chat/*` – nur falls ein bestehendes Run-/Tool-Event nicht verlustfrei eingebettet werden kann.

### Modulbackend

- `migrations/002_zerlegewerkstatt_v2.sql` – V2-Tabellen neben Legacy.
- `backend/v2_models.py` – Investigation-, Plan-, Call-, Grant- und Obligationmodelle.
- `backend/v2_store.py` – DB-Zugriff und Revisionen.
- `backend/v2_files.py` – V2-Dateibaum, Digests und atomare Publikation.
- `backend/v2_events.py` – geordneter Eventstrom und Snapshots.
- `backend/v2_access.py` – Projekt-/Owner-/Share-Prüfung.
- `backend/rea_catalog.py` – Live-/Paketkatalog, Suche und Digests.
- `backend/rea_client.py` – eine MCP-Verbindung je Untersuchung.
- `backend/rea_gateway.py` – generisches Catalog/Schema/Call/Result-Gateway.
- `backend/rea_results.py` – vollständige Ablage, Views und Paging.
- `backend/v2_containers.py` – Basisimage und statische Untersuchungscontainer.
- `backend/runtime_sandboxes.py` – wegwerfbare Runtime-Container.
- `backend/v2_grants.py` – wirkungsgebundene Freigaben.
- `backend/v2_plan.py` – Planrevisionen und Zustandsmaschine.
- `backend/v2_obligations.py` – Rekonstruktionspflichten.
- `backend/v2_reports.py` – versioniertes Dossier aus Evidence-Referenzen.
- `backend/v2_tools.py` – generische Agentenwerkzeuge.
- `backend/v2_routes_*.py` – getrennte REST-Routen nach Domäne.
- `backend/legacy_migration.py` – kontrollierte Übernahme aus 0.4.0.
- `backend/__init__.py` – Registrierung der V2-Router, Tools und Jobs.

### Container/Installer

- `extension/install.sh` – Basisimage v2 bauen und prüfen.
- `extension/uninstall.sh` – Laufzeit stoppen, Daten nicht ungefragt löschen.
- `extension/rea-image-manifest.json` – gepinnte Versionen und Digests.
- `extension/rea-healthcheck.sh` – Katalog-/Provider-/MCP-Prüfung.
- `scripts/rea_catalog_diff.py` – reproduzierbarer Katalogdiff.
- `scripts/rea_live_e2e.py` – opt-in reale Referenzjourneys.

### Skills

- `SKILL-zerlege-koordinator.md`
- `SKILL-rea-artefakte.md`
- `SKILL-rea-native.md`
- `SKILL-rea-managed.md`
- `SKILL-rea-android.md`
- `SKILL-rea-javascript-electron.md`
- `SKILL-rea-firmware.md`
- `SKILL-rea-runtime.md`
- `SKILL-rea-evidence-rekonstruktion.md`

### Frontend

- `frontend/v2/api.ts`
- `frontend/v2/types.ts`
- `frontend/v2/InvestigationList.tsx`
- `frontend/v2/NewInvestigationDialog.tsx`
- `frontend/v2/InvestigationWorkspace.tsx`
- `frontend/v2/InvestigationHeader.tsx`
- `frontend/v2/PlanPanel.tsx`
- `frontend/v2/AgentPanel.tsx`
- `frontend/v2/ActivityTimeline.tsx`
- `frontend/v2/ReaCallCard.tsx`
- `frontend/v2/InterventionPanel.tsx`
- `frontend/v2/GrantDialog.tsx`
- `frontend/v2/ArtifactTree.tsx`
- `frontend/v2/EvidenceExplorer.tsx`
- `frontend/v2/ResultViewer.tsx`
- `frontend/v2/ReconstructionPanel.tsx`
- `frontend/v2/EnvironmentPanel.tsx`
- `frontend/v2/i18n.de.ts`
- `frontend/v2/i18n.en.ts`
- zu jeder nichttrivialen Komponente eine co-lokierte Testdatei.

## Abhängigkeitsreihenfolge

```text
P0 Spec-Freigabe
  ↓
P1 strukturierter Core-MCP-Client
  ↓
P2 V2-Domäne und Dateiintegrität
  ↓
P3 Basisimage und Untersuchungscontainer
  ↓
P4 kataloggetriebener REA-Gateway
  ├───────────────┐
  ↓               ↓
P5 Plan/Events    P6 Skills/Agententeam
  └───────┬───────┘
          ↓
P7 transparente UI
          ↓
P8 statische Referenzjourneys
          ↓
P9 Firmware und rekursive Handoffs
          ↓
P10 Runtime-Sandbox und Grants
          ↓
P11 Rekonstruktionsdossier
          ↓
P12 Nachbau-/Vergleichsarbeitsraum
          ↓
P13 Legacy-Migration und Release
```

---

## P0: Spezifikation freigeben und Legacy einfrieren

### Task P0.1: V2-Entscheidung dokumentieren

- [ ] Nutzerfreigabe für alle vier V2-Dokumente einholen.
- [ ] Test/Guard schreiben: `tests/test_v2_spec_contract.py` prüft vorhandene Dokumente, Status und gegenseitige Links.
- [ ] Test rot ausführen.
- [ ] `SPEC.md` und `SPEC-E2.md` mit einem kurzen historischen Hinweis versehen, ohne Inhalt zu löschen.
- [ ] Test grün ausführen.
- [ ] Commit: `docs(zerlegewerkstatt): V2-Zielarchitektur freigeben`

### Task P0.2: Legacy-Funktionsfreeze absichern

- [ ] Regressionstest schreiben, der Legacy-Tabellen und Artefaktpfade vor V2-Migration inventarisiert.
- [ ] Test rot ausführen.
- [ ] Exportfixture und dokumentierte Legacy-Schnittstelle ergänzen.
- [ ] Test grün ausführen.
- [ ] Commit: `test(zerlegewerkstatt): Legacy-Bestand vor V2 einfrieren`

**Gate P0:** Keine weitere Implementierung ohne freigegebene Spezifikation und reproduzierbaren Legacy-Bestand.

---

## P1: Strukturierte MCP-Ergebnisse im Core

### Task P1.1: MCP-Datenklassen erweitern

- [ ] `core/tests/test_mcp_structured_content.py` mit RED-Tests für `outputSchema`, `annotations`, originale Contentblöcke, `structuredContent`, `isError` und Metadaten anlegen.
- [ ] Bestehendes Text-Rendering als Rückwärtskompatibilität testen.
- [ ] Tests rot ausführen.
- [ ] `McpTool` und `McpToolResult` in `mcp/client/base.py` erweitern.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(mcp): strukturierte Toolverträge verlustfrei erhalten`

### Task P1.2: stdio- und HTTP-Transport angleichen

- [ ] RED-Tests für identische strukturierte Ergebnisse über Fake-stdio und Fake-HTTP schreiben.
- [ ] Tests rot ausführen.
- [ ] `stdio.py` und `http.py` auf den erweiterten Vertrag umstellen.
- [ ] Sicherstellen, dass `tool_bridge.py` weiterhin nur begrenzte Textansicht an normale Agenten gibt.
- [ ] Tests grün ausführen.
- [ ] Vollständige Core-MCP- und Runner-Regression ausführen.
- [ ] Commit: `feat(mcp): strukturierte Resultate über alle Transporte`

### Task P1.3: Security- und Leak-Review

- [ ] Tests für Secret-Redaktion in strukturierten und gerenderten Feldern ergänzen.
- [ ] Mutationstest: Secret in `structured_content` darf nicht in Toolereignis oder LLM-Text gelangen.
- [ ] Security-Review durchführen.
- [ ] Commit: `test(mcp): strukturierte Inhalte gegen Secret-Leaks härten`

**Gate P1:** Core-PR gemergt; bestehende MCP-Nutzer unverändert grün.

---

## P2: V2-Domäne, Migration und Dateiintegrität

### Task P2.1: Additive V2-Migration

- [ ] RED-Tests für alle V2-Tabellen, FKs, Indizes und unveränderte Legacy-Tabellen schreiben.
- [ ] Migration `002_zerlegewerkstatt_v2.sql` implementieren.
- [ ] Migration zweimal gegen frische und bestehende 0.4.0-DB ausführen.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): additive V2-Datenbasis`

### Task P2.2: Untersuchungs- und Planmodelle

- [ ] RED-Tests für Zustandsübergänge, ungültige Sprünge, optimistic revisions und Projektzugriff schreiben.
- [ ] `v2_models.py`, `v2_store.py` und `v2_access.py` implementieren.
- [ ] Race-Test: parallele Nutzer-/Agentenänderung erzeugt `revision_conflict`.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): Untersuchungen und revisionssichere Pläne`

### Task P2.3: V2-Dateibaum

- [ ] RED-Tests für Streaming, SHA-256, atomare Veröffentlichung, Verzeichnissnapshot, Symlinks, Devices, Tiefen-/Entry-/Bytegrenzen und Deduplizierung schreiben.
- [ ] `v2_files.py` implementieren; bewährte sichere Legacy-Helfer nur nach Review wiederverwenden.
- [ ] Crash-/Cleanup-Tests für `.part` und halbe Manifeste ausführen.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): integrer V2-Artefaktspeicher`

**Gate P2:** Bestehende 0.4.0-Fälle bleiben lesbar; V2-Originale sind unveränderlich und digestgebunden.

---

## P3: Reproduzierbares REA-Basisimage und Untersuchungscontainer

### Task P3.1: Image-Manifest und Supply Chain

- [ ] RED-Tests für feste Versionen, SHA-256, verbotene `latest`-Verwendung und fehlende Digests schreiben.
- [ ] `rea-image-manifest.json` ergänzen.
- [ ] Installer liest ausschließlich das Manifest und bricht fail-closed ab.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): verifiziertes REA-V2-Basisimage`

### Task P3.2: Basisimage bauen

- [ ] Script-Tests für unprivilegierten Benutzer, keine Secrets/Sockets, Providerpfade, Ressourcenprofil und MCP-Start schreiben.
- [ ] Tests rot ausführen.
- [ ] `install.sh` auf versioniertes Basisimage erweitern.
- [ ] Frisches Image bauen und `rea mcp` über `incus exec` initialisieren.
- [ ] Live-Katalogzahl und Digest gegen Paketkatalog prüfen.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): REA-MCP-Basisimage bereitstellen`

### Task P3.3: Untersuchungscontainer-Lifecycle

- [ ] RED-Tests für Create/Start/Stop/Resume/Archive/Delete, Namensvalidierung, Limits, Netzlosigkeit und Crash-Recovery schreiben.
- [ ] `v2_containers.py` implementieren.
- [ ] Reale Wegwerfcontainer-Tests ausführen.
- [ ] Sicherstellen: keine Wiederverwendung zwischen Untersuchungen.
- [ ] Commit: `feat(zerlegewerkstatt): isolierte Untersuchungscontainer`

**Gate P3:** Ein realer Untersuchungscontainer startet REA-MCP ohne Netzwerk und ohne Host-Secrets.

---

## P4: Kataloggetriebener REA-MCP-Gateway

### Task P4.1: Live-Katalog und Digest

- [ ] RED-Tests mit synthetischem MCP-Server für 229+ Tools, Katalogänderung, doppelte Namen und Serverdrift schreiben.
- [ ] `rea_catalog.py` implementieren.
- [ ] Suche nach Name, Beschreibung, Providerhinweis und Annotation testen.
- [ ] Toolanzahl und Digests persistieren.
- [ ] Commit: `feat(zerlegewerkstatt): REA-Livekatalog indexieren`

### Task P4.2: Verbindung je Untersuchung

- [ ] RED-Tests für langlebige stdio-Verbindung über Fake-`incus exec`, Serialisierung, Reconnect und Close schreiben.
- [ ] `rea_client.py` implementieren.
- [ ] Nicht-idempotenter Call darf nach Verbindungsabbruch nicht automatisch wiederholt werden.
- [ ] Reale Folgecalls in einer REA-Sitzung ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): REA-MCP-Sitzungen pro Untersuchung`

### Task P4.3: Generischer Callpfad

- [ ] RED-Tests: beliebiges Live-Tool aufrufen; unbekanntes Tool ablehnen; keine fachliche Toolallowlist; Pfade außerhalb des Roots ablehnen; Argumente unverändert weitergeben.
- [ ] `rea_gateway.py` implementieren.
- [ ] Testtool nach Katalogrefresh hinzufügen; es muss ohne Modulcodeänderung aufrufbar sein.
- [ ] Commit: `feat(zerlegewerkstatt): vollständigen REA-Katalog durchleiten`

### Task P4.4: Vollständige Resultatablage

- [ ] RED-Tests für kleine, große, strukturierte, mehrblockige, fehlerhafte und truncated Ergebnisse schreiben.
- [ ] `rea_results.py` implementieren.
- [ ] Vollständige Datei vor Summary veröffentlichen und digestprüfen.
- [ ] Paging/View/Rawdownload testen.
- [ ] Regressionstest für den 8-MiB-Fehler aus 0.4.0: nie abgeschnittenes JSON parsen.
- [ ] Commit: `feat(zerlegewerkstatt): REA-Evidence verlustfrei speichern`

### Task P4.5: Generische Agentenwerkzeuge

- [ ] RED-Tests für Projektbindung, Investigation-Scope, untrusted-Markierung, Ergebnislimits und Toolregistrierung schreiben.
- [ ] `v2_tools.py` mit `reverse_investigation`, `rea_catalog`, `rea_schema`, `rea_call`, `rea_result`, `reverse_plan` implementieren.
- [ ] Test: jedes Live-REA-Tool ist über Catalog→Schema→Call erreichbar.
- [ ] Commit: `feat(zerlegewerkstatt): vollständigen REA-Gateway für Agenten`

**Gate P4:** Der Gateway kennt keine 18er- oder andere fachliche Toolallowlist; vollständige REA-Evidence bleibt erhalten.

---

## P5: Plan, Events, Intervention und Audit

### Task P5.1: Plan-Zustandsmaschine

- [ ] RED-Tests für alle Planpunktzustände, Abhängigkeiten, Skip-Gründe, `partial` und Revisionen schreiben.
- [ ] `v2_plan.py` implementieren.
- [ ] Nutzeränderung gewinnt nicht still gegen parallelen Agentenwrite.
- [ ] Commit: `feat(zerlegewerkstatt): kollaborativen Analyseplan verwalten`

### Task P5.2: Geordneter Ereignisstrom

- [ ] RED-Tests für Sequenzen, Reconnect `after_seq`, Snapshot, Retention und Eventlücken schreiben.
- [ ] `v2_events.py` und Eventroute implementieren.
- [ ] Agent-, Plan-, REA-, Evidence-, Grant- und Cleanup-Ereignisse integrieren.
- [ ] Commit: `feat(zerlegewerkstatt): lückenlosen Untersuchungsstream`

### Task P5.3: Pause, Cancel und Quarantäne

- [ ] RED-Tests: Pause blockiert neue Calls; laufender Call läuft definiert aus; Cancel sendet MCP-Cancel; unsicheres Cleanup quarantänisiert.
- [ ] Control-Plane-Zustände implementieren.
- [ ] Reale lange Testoperation abbrechen und Restprozesse prüfen.
- [ ] Commit: `feat(zerlegewerkstatt): Untersuchungen sicher unterbrechen`

### Task P5.4: Append-only Audit

- [ ] RED-Tests für Initiator, Tool, redigierte Argumente, Grant, Ergebnis, Retry und Cleanup schreiben.
- [ ] Auditpersistenz implementieren.
- [ ] Secret-/Zielinhalts-Leaktests ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): Agenten- und REA-Aktionen auditieren`

**Gate P5:** Nutzer kann pausieren, abbrechen und nach Reconnect ohne Zustandsverlust fortsetzen.

---

## P6: Agententeam und Skills

### Task P6.1: Koordinator-Skill

- [ ] Skill-Conformance-Tests schreiben: Design-first, Katalogsuche, Planfreigabe, Evidencepflicht, kein Abschluss bei offenen Pflichten.
- [ ] `SKILL-zerlege-koordinator.md` schreiben.
- [ ] Prompt-Injection-Fixture: Zieltext fordert Download/Installation; Koordinator behandelt ihn als Befund.
- [ ] Commit: `feat(zerlegewerkstatt): transparenten Koordinator-Skill`

### Task P6.2: Fachskills

Für jeden Fachskill atomar:

- [ ] RED-Conformance-Test mit repräsentativem Auftrag und erlaubtem Scope schreiben.
- [ ] Skill schreiben, ohne feste REA-Toolliste; Start über `rea_catalog`/`rea_schema`.
- [ ] Test auf Evidence, Limitations und Handoff ausführen.
- [ ] Einzelcommit: `feat(zerlegewerkstatt): <fachbereich>-Analyse-Skill`

### Task P6.3: Agententeam einrichten

- [ ] RED-Tests für idempotente Anlage/Aktualisierung, Toolmenge, kein Shellzugriff und Rollen schreiben.
- [ ] Setup-Service und UI-Schritt implementieren.
- [ ] Koordinator plus Spezialisten erzeugen oder bestehende kompatible Rollen binden.
- [ ] Modell- und Fallbackwahl sichtbar, aber nicht hart an einen Anbieter koppeln.
- [ ] Commit: `feat(zerlegewerkstatt): sichtbares REA-Agententeam`

### Task P6.4: Delegations- und Handoffvertrag

- [ ] RED-Tests für Investigation-ID, Artefakte, Evidence, Scope, Grantklassen und Ergebnisreferenzen schreiben.
- [ ] Delegationsvorlagen implementieren.
- [ ] Abbruch/Verlust eines Spezialisten darf Hauptplan nicht als erledigt markieren.
- [ ] Commit: `feat(zerlegewerkstatt): evidenzbasierte Analyse-Handoffs`

**Gate P6:** Ein Koordinator delegiert eine reale statische Untersuchung; Nutzer sieht Auftrag und Ergebnis.

---

## P7: Transparente V2-Oberfläche

### Task P7.1: Liste und Anlage

- [ ] Frontendtests für leer, loading, error, permission, neue Untersuchung und Aufnahme schreiben.
- [ ] Tests rot ausführen.
- [ ] `InvestigationList`, `NewInvestigationDialog`, API und Typen implementieren.
- [ ] Tests und Core-Frontend-Build grün.
- [ ] Commit: `feat(zerlegewerkstatt): V2-Untersuchungen anlegen`

### Task P7.2: Arbeitsraum und Header

- [ ] RED-Tests für Status, Pause, Cancel, Stop, Resume, Modus und wartende Grants schreiben.
- [ ] `InvestigationWorkspace` und `InvestigationHeader` implementieren.
- [ ] Mobile- und Tastaturtest ergänzen.
- [ ] Commit: `feat(zerlegewerkstatt): steuerbaren Untersuchungsarbeitsraum`

### Task P7.3: Plan und Agenten

- [ ] RED-Tests für Bearbeiten, Reorder mit Abhängigkeiten, Priorität, Skip, Spezialist und RevisionConflict schreiben.
- [ ] `PlanPanel` und `AgentPanel` implementieren.
- [ ] Delegationen und Agentenstatus live anbinden.
- [ ] Commit: `feat(zerlegewerkstatt): Plan und Agenten transparent machen`

### Task P7.4: Live-Aktivität und REA-Calls

- [ ] RED-Tests für Eventreihenfolge, Reconnect, Callkarte, Details, partial/truncated und Cleanup schreiben.
- [ ] `ActivityTimeline` und `ReaCallCard` implementieren.
- [ ] Bestehende HydraHive-Tool-/Run-Komponenten wiederverwenden, nicht duplizieren.
- [ ] Commit: `feat(zerlegewerkstatt): REA-Arbeit live anzeigen`

### Task P7.5: Chat und Intervention

- [ ] RED-Tests für pending intervention, nach Schritt anwenden, abbrechen+neu planen und Notiz schreiben.
- [ ] `InterventionPanel` und eingebetteten Untersuchungs-Chat implementieren.
- [ ] Commit: `feat(zerlegewerkstatt): aktive Nutzerintervention`

### Task P7.6: Artefakte, Evidence und Results

- [ ] RED-Tests für Baum, Gaps, Handoff, Filter, Paging, Rawdownload und Digestanzeige schreiben.
- [ ] `ArtifactTree`, `EvidenceExplorer` und `ResultViewer` implementieren.
- [ ] Commit: `feat(zerlegewerkstatt): Artefakte und Evidence untersuchbar machen`

### Task P7.7: Grants und Umgebung

- [ ] RED-Tests für gebundene Freigaben, Ablehnung, Einschränkung, Ablauf und Providerstatus schreiben.
- [ ] `GrantDialog` und `EnvironmentPanel` implementieren.
- [ ] Accessibility-, i18n-, altlook-, Farbstufen- und 390×844-Tests grün.
- [ ] Commit: `feat(zerlegewerkstatt): Freigaben und Provider sichtbar machen`

**Gate P7:** Browser-E2E zeigt den vollständigen transparenten geführten Workflow mit Pause und Planeingriff.

---

## P8: Statische Referenzjourneys

### Task P8.1: Native Anwendung

- [ ] Öffentliche Fixture und Herkunft/Digest dokumentieren.
- [ ] RED-E2E: Aufnahme→Plan→open_binary→Suche→Funktion→Decompile→Xrefs→Evidence→Close.
- [ ] Nur fehlende generische Orchestrierung implementieren; keine Tool-Sonderadapter.
- [ ] Nutzerpause und Zusatzfrage im Browser testen.
- [ ] Commit: `test(zerlegewerkstatt): native REA-Journey vollständig abnehmen`

### Task P8.2: Managed oder APK

- [ ] RED-E2E für Manifest/Identität→Klasse/Methode→Referenzen→Evidence schreiben.
- [ ] Journey über denselben Gateway ausführen.
- [ ] Native/managed Handoff testen.
- [ ] Commit: `test(zerlegewerkstatt): App-Rekonstruktion abnehmen`

### Task P8.3: JavaScript/Electron

- [ ] RED-E2E für Modulgraph, Imports, IPC/Routen und gezielte View schreiben.
- [ ] Große Evidence-Datei und Paging prüfen.
- [ ] Commit: `test(zerlegewerkstatt): Electron-Journey abnehmen`

**Gate P8:** Drei unterschiedliche statische REA-Arbeitsabläufe ohne neue Fachadapter erfolgreich.

---

## P9: Firmware-Extraktion und rekursive Analyse

### Task P9.1: Firmware-Journey

- [ ] Öffentliche zulässige Firmwarefixture mit Digest dokumentieren.
- [ ] RED-E2E für `inspect_firmware_regions` und `extract_firmware` schreiben.
- [ ] Outputbaum, Hashes, Lineage, Gaps und fehlende Extractors prüfen.
- [ ] Commit: `feat(zerlegewerkstatt): REA-Firmwareextraktion veröffentlichen`

### Task P9.2: Rekursive Discovery

- [ ] RED-Test: extrahiertes ELF/APK/JS wird als Kindartefakt vorgeschlagen, nicht ungefragt vollständig analysiert.
- [ ] Planvorschläge und Artefaktbeziehungen implementieren.
- [ ] Mindestens ein extrahiertes ELF an Native-Spezialisten übergeben.
- [ ] Commit: `feat(zerlegewerkstatt): extrahierte Komponenten weiterreichen`

### Task P9.3: Firmwaregrenzen

- [ ] Tests für encrypted/unknown chunks, Depthlimit, >REA-Limit, fehlende Abhängigkeit und partial schreiben.
- [ ] UI und Dossier müssen Gaps erhalten.
- [ ] Kein `completed`, solange erforderliche Gaps offen sind.
- [ ] Commit: `test(zerlegewerkstatt): Firmwarelücken fail-closed behandeln`

**Gate P9:** Firmware wird wirklich extrahiert und weiter untersucht; keine bloße Signaturansicht.

---

## P10: Runtime-Sandbox und wirkungsgebundene Grants

### Task P10.1: Grantmodell

- [ ] RED-Tests für Nutzer/Projekt/Investigation/Plan/Tool/Ziel/Zeit/Once-Bindung schreiben.
- [ ] `v2_grants.py` implementieren.
- [ ] Replay, Zielwechsel und abgelaufenen Grant ablehnen.
- [ ] Commit: `feat(zerlegewerkstatt): Runtime-Aktionen eng freigeben`

### Task P10.2: Wegwerfcontainer

- [ ] RED-Tests für Create, minimale Artefaktkopie, kein Secret, Netz aus, Export, Destroy und Quarantäne schreiben.
- [ ] `runtime_sandboxes.py` implementieren.
- [ ] Reale harmlose Testanwendung ausführen und Containerentfernung belegen.
- [ ] Commit: `feat(zerlegewerkstatt): dynamische Analyse wegwerfbar isolieren`

### Task P10.3: Browser/Netz

- [ ] RED-E2E mit lokaler kontrollierter Testseite und gebundenem D-Grant schreiben.
- [ ] Egress-/Zielanzeige und Screenshots/Netz-Evidence prüfen.
- [ ] Ablehnung muss ohne Prozess-/Netzstart enden.
- [ ] Commit: `feat(zerlegewerkstatt): Browseranalyse kontrolliert freigeben`

### Task P10.4: ADB/Frida-Vertrag

- [ ] Tests mit Emulator/Fake-Gerät für Gerätebindung und Grant schreiben.
- [ ] Keine Hardwareannahme in Standard-CI; opt-in reale Lane.
- [ ] Frida-/ADB-Ergebnisse über denselben Evidencevertrag speichern.
- [ ] Commit: `feat(zerlegewerkstatt): Geräteanalyse sicher anbinden`

**Gate P10:** Kein Runtime-/Netz-/Gerätecall startet ohne passenden Grant; Cleanup ist nachgewiesen.

---

## P11: Rekonstruktionspflichten und Dossier

### Task P11.1: Obligation Ledger

- [ ] RED-Tests für required/optional, Owner, Evidence, unknown, contradiction und closure schreiben.
- [ ] `v2_obligations.py` implementieren.
- [ ] `completed` bei offener required obligation ablehnen.
- [ ] Commit: `feat(zerlegewerkstatt): Rekonstruktionspflichten nachweisbar schließen`

### Task P11.2: Evidence-Matrix und Dossier

- [ ] RED-Tests für jede Dossiersektion, Evidence-Links, unknowns und Versionierung schreiben.
- [ ] `v2_reports.py` implementieren.
- [ ] Aussagen ohne Evidence nur als Hypothese/unknown erlauben.
- [ ] Commit: `feat(zerlegewerkstatt): evidenzbasiertes Rekonstruktionsdossier`

### Task P11.3: Rekonstruktions-UI

- [ ] RED-Tests für Counts, Filter, Restfragen, Dossierversionen und keine falsche 100-%-Anzeige schreiben.
- [ ] `ReconstructionPanel` implementieren.
- [ ] Browser-E2E mit partial und ready durchführen.
- [ ] Commit: `feat(zerlegewerkstatt): Rekonstruktionsreife transparent zeigen`

**Gate P11:** Ein Dossier kann aus den Referenzjourneys erzeugt werden und nennt alle verbleibenden Lücken.

---

## P12: Nachbau- und Differentialvergleich

### Task P12.1: Getrennter Kandidatenarbeitsraum

- [ ] RED-Tests: neues Quellprojekt getrennt von Original/Evidence, explizite Nutzerfreigabe, sichere Pfade.
- [ ] Rekonstruktionsarbeitsraum implementieren.
- [ ] Kein Originalartefakt wird verändert oder als Quellcode ausgegeben.
- [ ] Commit: `feat(zerlegewerkstatt): Nachbauprojekt aus Dossier anlegen`

### Task P12.2: Testvektoren

- [ ] RED-Tests für Protokoll-, Datei- und Funktionsvektoren mit Evidence-Referenz schreiben.
- [ ] Generator für Testgerüste implementieren.
- [ ] Inferenz ohne beobachteten Erwartungswert als unknown markieren.
- [ ] Commit: `feat(zerlegewerkstatt): belegte Kompatibilitätstests erzeugen`

### Task P12.3: Kontrollierter Vergleich

- [ ] RED-E2E mit kleiner öffentlicher Fixture: Original und Kandidat in getrennten Runtime-Containern.
- [ ] REA-Vergleichs-/Rekonstruktionsfunktionen verwenden.
- [ ] Gleichheit nur für beobachtete Dimensionen behaupten.
- [ ] Commit: `feat(zerlegewerkstatt): Nachbau gegen Originalverhalten prüfen`

**Gate P12:** Mindestens ein kleiner Kandidat wird aus einem Dossier gebaut und in klar begrenzten Dimensionen verglichen.

---

## P13: Legacy-Migration, Release und Gesamtaufnahme

### Task P13.1: Legacy-Import

- [ ] RED-Tests mit realistischem 0.4.0-Fall, Artefakten, Jobs und Bericht schreiben.
- [ ] `legacy_migration.py` implementieren.
- [ ] Originalhash neu prüfen; Legacy-Bericht nicht als REA-Evidence umetikettieren.
- [ ] Rollbacktest durchführen.
- [ ] Commit: `feat(zerlegewerkstatt): Legacy-Fälle kontrolliert übernehmen`

### Task P13.2: Legacy-UI und Deprecation

- [ ] RED-Tests für read-only Ansicht und „Als V2-Untersuchung übernehmen“ schreiben.
- [ ] Alte Analysebuttons nach V2-Abnahme als Legacy markieren.
- [ ] Neue V2-Seite wird Standard; keine Datenlöschung.
- [ ] Commit: `feat(zerlegewerkstatt): sicheren V2-Übergang anbieten`

### Task P13.3: Gesamtverifikation

- [ ] Alle Modul-Pytests und Frontendtests grün.
- [ ] Core-Gesamtsuite, Ruff, TypeScript und Produktionsbuild grün.
- [ ] `check_test_safety.py`, Isolationstest und Versionsprüfung grün.
- [ ] Native-, APK/Electron-, Firmware- und Runtime-E2E grün.
- [ ] Browserabnahme Desktop und 390×844.
- [ ] Prompt-Injection-, Secret-, Path-, Grant-, Cancel- und Cleanup-Gegentests grün.
- [ ] Katalogparität mit echter gepinnter REA-Version dokumentieren.
- [ ] Unabhängiges Security-, Backend-, UX- und Testreview ohne offene High/Medium-Funde.
- [ ] `hh-review`, `labor-review` und `verification-before-completion` durchführen.
- [ ] Release-Commit: `feat(zerlegewerkstatt): REA-basierte V2 veröffentlichen`

## Produktweite Abnahmeszenarien

### A. Native Desktopsoftware verstehen

1. Datei aufnehmen.
2. Nutzerziel formulieren.
3. Plan ändern und genehmigen.
4. Native Sitzung öffnen.
5. Funktion suchen, dekompilieren, Xrefs und Callpfad verfolgen.
6. Evidence exportieren.
7. Nutzer pausiert und ergänzt Frage.
8. Dossier erzeugen.

**Erfolg:** Funktionsbeschreibung mit Belegen; offene Laufzeitfragen bleiben sichtbar.

### B. Smart-Lampen-Firmware zerlegen

1. Firmware aufnehmen und hashen.
2. Regionen erkennen.
3. Dateisystem extrahieren.
4. Extraktionsbaum und Gaps anzeigen.
5. Init-Skripte, Konfiguration, Webressourcen und native Programme klassifizieren.
6. Ein natives Programm vertiefen.
7. Netzwerk-/Protokollhypothesen mit Evidence verbinden.
8. Nachbauplan für lokale Steuerung erstellen.

**Erfolg:** Echte Dateien und nachvollziehbare Lineage; keine Vollständigkeitsbehauptung bei Gaps.

### C. APK/Electron-Funktion nachvollziehen

1. Anwendung inventarisieren.
2. Manifest/Module/IPC/Routen bestimmen.
3. konkrete Funktion bis Methode/Modul und Referenzen verfolgen.
4. native Abhängigkeiten übergeben.
5. Evidence und unbekannte Runtimeanteile dokumentieren.

**Erfolg:** rekonstruierter Ablauf statt bloßer Stringliste.

### D. Dynamisches Verhalten kontrolliert beobachten

1. Agent schlägt Runtime-Schritt vor.
2. UI zeigt Wirkung, Ziel und Grant.
3. Nutzer begrenzt und genehmigt.
4. frischer Runtime-Container startet.
5. Verhalten wird aufgezeichnet.
6. Evidence exportiert.
7. Container zerstört.

**Erfolg:** kein Start ohne Grant, kein Restcontainer/Prozess, vollständiger Audit.

### E. Nutzer greift aktiv ein

1. Analyse läuft.
2. Nutzer pausiert.
3. ändert Priorität und Agent.
4. lädt Zusatzmitschnitt hoch.
5. verwirft dynamischen Schritt.
6. setzt statische Untersuchung fort.

**Erfolg:** keine verlorenen Events, keine heimlichen Schritte, Planrevision konsistent.

## Nicht in diesem Plan

- Umgehung von DRM, Authentifizierung, Lizenzprüfung oder fremden Zugriffskontrollen.
- Automatisches Flashen oder irreversible Geräteänderungen.
- Garantie auf ursprünglichen Quellcode oder vollständige Rekonstruktion unbekannter verschlüsselter Komponenten.
- Bündelung kommerzieller Providerlizenzen.
- Ersetzen oder Forken von REA.
- Weiterer Ausbau des alten 18-Befehle-Adapters als parallele V2-Architektur.

## Abschlussdefinition

V2 gilt erst als fertig, wenn:

- das echte REA als MCP-Server verwendet wird,
- der vollständige Live-Katalog erreichbar ist,
- Nutzer Agenten und Calls sehen und steuern können,
- vollständige Evidence erhalten bleibt,
- Firmware tatsächlich extrahiert und rekursiv untersucht wird,
- dynamische Arbeit getrennt und grantgebunden läuft,
- ein Rekonstruktionsdossier mit offenem Pflichtenkatalog entsteht,
- alte Daten sicher migrierbar bleiben,
- reale End-to-End-Journeys und unabhängige Reviews bestanden sind.
