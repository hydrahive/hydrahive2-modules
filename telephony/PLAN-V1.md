# Plan: Telefonie-Modul V1

## Ziel

Ein optionales HydraHive-Modul verbindet einen projektgebundenen VoIP-Zugang mit einem
spezialisierten Telefon-Agenten. Der Pilot beantwortet echte FRITZ!Box-Anrufe und führt
menschlich freigegebene Informationsanrufe sofort oder geplant aus. Mitglieder arbeiten
gemeinsam, während Mitgliederkreis, Eigentum und Projektlöschung owner-only bleiben.

Die verbindlichen Produkt-, Sicherheits- und Akzeptanzregeln stehen in `SPEC-V1.md`.

## Voraussetzungen und Abhängigkeiten

1. Der vorhandene strikte `AuthPrincipal` wird für alle neuen Core- und Modulrouten
   verwendet.
2. Core-Projekte erhalten unveränderliche Typ-/Policy-Felder und einen generischen,
   sicheren Eigentumsübertragungsvertrag.
3. Projektbezogene Secrets werden verschlüsselt und sind nur verwendbar/ersetzbar, nie
   revealbar.
4. Der Gatewayvertrag wird mit einem Fake implementiert und getestet, bevor ein
   Tel-Agent-/SIP-Adapter angeschlossen wird.
5. Ein echter FRITZ!Box-Spike ist ein Release-Gate; Unit-Tests dürfen ihn nicht ersetzen.
6. Tel-Agent wird nur als separater AGPL-Sidecar verwendet. Lizenzprüfung und
   Veröffentlichung etwaiger Sidecar-Änderungen erfolgen vor Distribution.

## Geplante Dateien

Die Liste beschreibt die beabsichtigten Verantwortungen. Produktionsdateien bleiben
möglichst unter 200 Zeilen und werden bei wachsender Verantwortung weiter aufgeteilt.

### Core — separater PR 1: Projekt-Policies und Eigentum

- `core/src/hydrahive/projects/config.py` — `project_type`, `membership_policy`,
  `lifecycle_policy` und stabile `created_by_user_id` bei serverseitiger Anlage setzen
  und gegen normale Updates schützen
- `core/src/hydrahive/projects/ownership.py` — Zwei-Parteien-Eigentumsübertragung
- `core/src/hydrahive/projects/_members_model.py` — Memberships auf stabile `user_id`
  migrieren, Anzeigenamen nur darstellen und Owner-/Policy-Guards bereitstellen
- `core/src/hydrahive/api/routes/projects.py` — owner-only Member-/Delete-Vertrag und
  Ownership-Endpoints
- `core/src/hydrahive/db/` — persistente Ownership-Transfer-Tabelle/Migration
- `core/tests/test_project_policies.py` — Rollen, owner-only und Systemadmin-Break-glass
- `core/tests/test_project_ownership_transfer.py` — Ablauf, Annahme, Atomizität und
  ehemaliger Owner als Mitglied

### Core — separater PR 2: projektbezogener Secret-Vertrag

- `core/src/hydrahive/credentials/project_store.py` — verschlüsseltes Speichern,
  Verwenden, Ersetzen und Löschen ohne Reveal
- `core/src/hydrahive/credentials/crypto.py` — Key-Wrapping und redaktionssichere Fehler
- `core/src/hydrahive/api/routes/project_credentials.py` — projektgebundene, policy-
  geprüfte API
- `core/tests/test_project_credentials.py` — IDOR, Maskierung, Rotation, Delete und Logs
- Installer/Settings-Datei für den installationsweiten Secret-Masterkey

### Modul-Grundgerüst

- `telephony/manifest.json` — Modulmetadaten, Navigation, Migrationen, Servicevertrag
- `telephony/backend/__init__.py` — Router, Migrationen, Jobs und Modul-Hooks registrieren
- `telephony/backend/models.py` — Pydantic-Request-/Response-Verträge
- `telephony/backend/access.py` — Principal- und Projektzuordnung, 404-Isolation
- `telephony/backend/repository.py` — DB-Zugriff und Revisions-/Projektgrenzen
- `telephony/migrations/001_telephony_core.sql` — Verbindungen, Settings, Preferences,
  Profile, Jobs, Attempts, Calls, Artifacts und Audit
- `telephony/tests/conftest.py` — isolierte DB, Benutzer, Projekte und Fake-Gateway
- `telephony/tests/test_migrations.py` — Tabellen, Indizes, Constraints und Idempotenz

### Setup, Einstellungen und Profile

- `telephony/backend/setup.py` — Verbindungstest und kompensierende Projektanlage
- `telephony/backend/settings.py` — Projektsettings, persönliche Preferences und Profile
- `telephony/backend/routes_setup.py` — Setup-/Connection-API
- `telephony/backend/routes_settings.py` — Settings-/Preferences-/Profile-API
- `telephony/tests/test_setup.py` — Erfolg, Rollback, Quota, Halbzustand und Repair
- `telephony/tests/test_preferences.py` — persönliche Defaults, Teilen, Kopieren, Revision

### Gateway und Voice-Runner

- `telephony/backend/gateway/protocol.py` — typisierter Kontroll-/Eventvertrag
- `telephony/backend/gateway/client.py` — authentifizierter REST-/Stream-Client
- `telephony/backend/gateway/auth.py` — Maschinenidentität, Rotation und Replay-Schutz
- `telephony/backend/gateway/fake.py` — deterministischer Testgateway
- `telephony/backend/voice/runner.py` — normale HydraHive-Session, gestreamte Agentenantwort
- `telephony/backend/voice/policy.py` — unveränderliches Informationsmandat und Toolset
- `telephony/tests/test_gateway_protocol.py` — Sequenz, Auth, Replay, Disconnect, Idempotenz
- `telephony/tests/test_voice_policy.py` — Zusage-, Nummern-, Tool- und Datenabflussgrenzen
- `telephony/tests/test_voice_stream.py` — Partial/Final, TTS-Abbruch und Barge-in

### Aufträge, Scheduler und Retry

- `telephony/backend/jobs.py` — Draft, Approval-Snapshot, Mutationen und Zustände
- `telephony/backend/scheduler.py` — Window-Scheduling, Lease/Claim und Neustart
- `telephony/backend/retry.py` — statusabhängige Retry-Entscheidung
- `telephony/backend/routes_jobs.py` — Auftrag, Freigabe, Run, Cancel und Attempts
- `telephony/tests/test_jobs.py` — Mandat, Revision, Freigabe und Statusmaschine
- `telephony/tests/test_scheduler.py` — Zeitzone, DST, Ablauf, Pause und konkurrierender Claim
- `telephony/tests/test_retry.py` — busy/no-answer/transient/connected und Obergrenzen
- `telephony/tests/test_idempotency.py` — Timeout und Neustart erzeugen keinen Doppelanruf

### Speicherung, Archiv und Benachrichtigung

- `telephony/backend/artifacts/crypto.py` — projektbezogene authentifizierte Verschlüsselung
- `telephony/backend/artifacts/store.py` — sichere Pfade, atomare Writes und Streaming
- `telephony/backend/retention.py` — Fristen, Papierkorb, Purge und Restore-Tombstones
- `telephony/backend/reports.py` — Zusammenfassung und strukturiertes Ergebnis
- `telephony/backend/notifications.py` — Kanal-/Ergebnis-Matrix und sichere Detailgrade
- `telephony/backend/routes_calls.py` — Calls, Audio, Transkript, Archiv, Delete und Export
- `telephony/tests/test_artifacts.py` — Traversal, Verschlüsselung, Integrität und Isolation
- `telephony/tests/test_retention.py` — 30 Tage, Custom, Archiv, Trash, Purge und Restore
- `telephony/tests/test_notifications.py` — Checkboxen, Ruhezeiten und kein externer
  Volltranskript-/Audioversand

### Frontend

- `telephony/frontend/index.tsx` — Route, Navigation und Modulregistrierung
- `telephony/frontend/api.ts` — typisierte Modul-API
- `telephony/frontend/types.ts` — Connection-, Job-, Call-, Profile- und Archivverträge
- `telephony/frontend/TelephonyPage.tsx` — Projekt-Cockpit-Shell
- `telephony/frontend/SetupWizard.tsx` — FRITZ!Box/PBX-Verbindung und Test
- `telephony/frontend/OverviewView.tsx` — Status und offene Entscheidungen
- `telephony/frontend/JobEditor.tsx` — Mandat, Sofort/Window, Retry, Kanäle, Retention
- `telephony/frontend/QueueView.tsx` — geplante/aktive Versuche und Abbruch
- `telephony/frontend/CallsView.tsx` — Liste, Filter und Ergebnis
- `telephony/frontend/CallDetail.tsx` — Audio, Transkript, Zusammenfassung und Attempts
- `telephony/frontend/ArchiveView.tsx` — Aufbewahrung, Trash, Export und getrennte Löschung
- `telephony/frontend/SettingsView.tsx` — Verbindung, gemeinsame/persönliche Defaults
- `telephony/frontend/MembersView.tsx` — owner-only Mitgliedschaft und Transfer
- `telephony/frontend/i18n/de.json` und `en.json` — vollständige UI-Texte

### Gateway-Paket/Sidecar

Das genaue Repository folgt der Lizenzentscheidung; es wird nicht in den Core kopiert.
Der Vertrag verlangt mindestens:

- eigene Runtime und Service-/Container-Lifecycle
- direkte lokale SIP-Registrierung oder dokumentierten lokalen PBX-/LiveKit-Adapter
- RTP/Codec, Streaming-STT/TTS, VAD/Endpointing und Barge-in
- authentifizierten HydraHive-Kontrollkanal
- Health, strukturierte Fehler und redaktionssichere Logs
- keine eigene Benutzer-/Projektentscheidung

## Implementierungsreihenfolge

### Task 0: Lizenz- und Transport-Gate

- [ ] Tel-Agent-Version/Commit pinnen und AGPL-Verpflichtungen dokumentieren
- [ ] RED: Gateway-Contract-Test gegen einen noch nicht existierenden Adapter
- [ ] Minimalen Fake-Gateway implementieren und Contract-Test grün machen
- [ ] echten FRITZ!Box-SIP-Weg auswählen: direkter SIP-Client als Ziel; lokaler
  Asterisk/FreeSWITCH-/LiveKit-Adapter nur als kompatibler Fallback
- [ ] dedizierte, ausgehend beschränkte Testnebenstelle dokumentieren
- [ ] Commit: `test(telephony): Gatewayvertrag festlegen`

### Task 1: Core-Projekt-Policies

- [ ] RED: Telefonieprojekt kann `owner_only` serverseitig setzen
- [ ] RED: Eigentümer und Mitglieder werden über stabile `user_id` autorisiert; eine
  Benutzerlöschung mit gleichnamiger Neuanlage erbt keinen Zugriff
- [ ] RED: Umbenennung eines Benutzers verliert keine legitime Mitgliedschaft
- [ ] RED: Projektadmin kann bei `owner_only` keine Mitglieder ändern
- [ ] RED: nur Eigentümer löscht das Projekt
- [ ] RED: normale Projekte behalten das bestehende Rollenverhalten
- [ ] Legacy-Projekte rückwärtskompatibel auf stabile Member-/Owner-IDs migrieren
- [ ] unveränderliche Typ-/Policy-Felder implementieren
- [ ] zentrale Principal-Guards in allen Member-/Delete-Pfaden anwenden
- [ ] GREEN: Core-Projekttests vollständig grün
- [ ] Security-Review und separater Core-PR
- [ ] Commit: `feat(projects): owner-only Projekt-Policies ergänzen`

### Task 2: Eigentumsübertragung

- [ ] RED: nur Eigentümer kann Transfer an bestehendes Mitglied anfragen
- [ ] RED: Ziel muss selbst annehmen; Fremde und abgelaufene Requests liefern 404/409
- [ ] RED: höchstens ein offener Transfer
- [ ] RED: Annahme ist atomar und alter Eigentümer bleibt Projektadmin
- [ ] RED: fehlender Eigentümer kann nur über auditierten Break-glass repariert werden
- [ ] Migration, Service und Endpoints implementieren
- [ ] GREEN: Transfer-/Regressionstests grün
- [ ] Security-Review und separater Core-PR
- [ ] Commit: `feat(projects): bestätigte Eigentumsübertragung hinzufügen`

### Task 3: Projektbezogener Secret Store

- [ ] RED: Secrets sind verschlüsselt und API-Responses immer maskiert
- [ ] RED: Mitglieder dürfen verwenden/ersetzen, nur Eigentümer vollständig löschen
- [ ] RED: fremdes Projekt, Logs, Exceptions und LLM-Kontext leaken nichts
- [ ] RED: Rotation unterbricht keine andere Projektverbindung
- [ ] Masterkey-/Key-Wrapping-Lifecycle implementieren
- [ ] Backup-/Restore-Vertrag und Verlustmeldung implementieren
- [ ] GREEN: Credential-/Security-Tests grün
- [ ] separater Core-PR
- [ ] Commit: `feat(credentials): projektbezogenen Secret Store bereitstellen`

### Task 4: Modul-Migration und Zugriffskern

- [ ] RED: Migration erzeugt Tabellen, Indizes, Unique- und Project-FK-Constraints
- [ ] RED: alle Fachressourcen sind strikt projektisoliert
- [ ] RED: entfernte/gelöschte Benutzer werden über `require_principal` abgewiesen
- [ ] Modulgrundgerüst, Repository, Access-Guard und Audit implementieren
- [ ] Migration zweimal idempotent ausführen
- [ ] GREEN: SQLite-/PostgreSQL- beziehungsweise unterstützte DB-Tests grün
- [ ] Commit: `feat(telephony): Daten- und Zugriffskern anlegen`

### Task 5: Setup und automatische Projektanlage

- [ ] RED: Verbindungstest persistiert kein Secret und redigiert Fehler
- [ ] RED: normales Mitglied kann nur über den Modul-Setupflow ein Telefonieprojekt anlegen
- [ ] RED: Fehler in jedem Orchestratorschritt rollt Vorgänger zurück oder markiert
  `repair_required`
- [ ] RED: Quota und doppelter SIP-Account werden abgefangen
- [ ] Setup, Projekt-/Agentanlage, Secret und Artifact-Verzeichnis implementieren
- [ ] GREEN: Setup-/Rollbacktests grün
- [ ] Commit: `feat(telephony): VoIP-Projekt per Wizard anlegen`

### Task 6: Einstellungen und Profile

- [ ] RED: gemeinsame Einstellungen sind für alle Mitglieder editierbar
- [ ] RED: persönliche Einstellungen sind nur für den Benutzer schreibbar
- [ ] RED: private Profile bleiben privat, Projektprofile sind gemeinsam sichtbar
- [ ] RED: Kopie driftet unabhängig; verwendetes Profil wirkt nur auf neue Jobs
- [ ] RED: Revision verhindert stilles Überschreiben
- [ ] Services, Routen und API-Verträge implementieren
- [ ] GREEN: Preferences-/Profiletests grün
- [ ] Commit: `feat(telephony): persönliche und gemeinsame Einstellungen ergänzen`

### Task 7: Auftrags- und Freigabekern

- [ ] RED: Agent/API-Maschine kann nur Draft, kein Approval erzeugen
- [ ] RED: interaktive Person genehmigt unveränderlichen Snapshot
- [ ] RED: sicherheitsrelevante Änderung setzt Approval zurück
- [ ] RED: Informationsmandat enthält erlaubte Offenlegungen und verbotene Aktionen
- [ ] RED: Nummernvalidierung und harte Zielbereichssperren greifen vor Approval und Run
- [ ] Jobs, State Machine, Revision und Endpoints implementieren
- [ ] GREEN: Job-/Securitytests grün
- [ ] Commit: `feat(telephony): freigegebene Informationsaufträge einführen`

### Task 8: Window-Scheduler und Retry

- [ ] RED: Sofort- und Zeitfenster-Jobs werden genau einmal geclaimt
- [ ] RED: Neustart, Lease-Ablauf und konkurrierende Worker wählen nicht doppelt
- [ ] RED: verpasstes Fenster wird `expired`
- [ ] RED: Default ist ein Retry; busy/no-answer/transient verwenden eigene Abstände
- [ ] RED: connected/falscher Kontakt/Ablehnung/ungültig erzeugen keinen Auto-Retry
- [ ] RED: DST-Lücke und doppelte Ortszeit erzeugen höchstens einen Call
- [ ] Scheduler, Lease und Retry implementieren
- [ ] GREEN: kontrollierte Uhr-/Nebenläufigkeitstests grün
- [ ] Commit: `feat(telephony): Anrufe planen und begrenzt wiederholen`

### Task 9: HydraHive-Voice-Runner mit Fake-Gateway

- [ ] RED: Call erzeugt sichtbare Projekt-Session
- [ ] RED: Final-Transkript geht in den Agenten, Partials nicht als Nutzerturn
- [ ] RED: Agententokens werden früh gestreamt und TTS bei Barge-in abgebrochen
- [ ] RED: Telefon-Agent besitzt keine Shell-/Admin-/freie HTTP-/Dial-Tools
- [ ] RED: Prompt-Injection kann Mandat und erlaubte Offenlegungen nicht erweitern
- [ ] minimalen Telefon-Agenten, Streaming-Bridge und Ergebnisabschluss implementieren
- [ ] GREEN: deterministische End-to-End-Fakes grün
- [ ] Commit: `feat(telephony): Calls an spezialisierten Agenten anbinden`

### Task 10: Verschlüsselter Artifact Store und Retention

- [ ] RED: Audio/Transkript/Resultat sind auf Disk nicht im Klartext
- [ ] RED: manipuliertes Ciphertext/Manifest wird abgewiesen
- [ ] RED: Path Traversal und Symlink-Escape sind blockiert
- [ ] RED: 30-Tage-Default, Custom, Summary-only und Archiv funktionieren
- [ ] RED: getrenntes Delete und Gesamtdelete bereinigen Ableitungen/Caches
- [ ] RED: Papierkorb, Sofort-Purge und Restore-Tombstone verhalten sich deterministisch
- [ ] Store, Streams, Retention-Job und Routen implementieren
- [ ] GREEN: Artifact-/Retentiontests grün
- [ ] Commit: `feat(telephony): verschlüsseltes Gesprächsarchiv bereitstellen`

### Task 11: Berichte und flexible Rückmeldung

- [ ] RED: jeder Abschluss erzeugt internes strukturiertes Ergebnis
- [ ] RED: pro Ergebnis gelten die ausgewählten Kanal-Checkboxen
- [ ] RED: externe Kanäle erhalten nie automatisch Audio/Volltranskript
- [ ] RED: persönliche Ruhezeiten verschieben nur Nachricht, nicht Call-Ergebnis
- [ ] RED: Benachrichtigungsfehler verändern den Fachstatus nicht
- [ ] Reporter und Kanaladapter implementieren
- [ ] GREEN: Benachrichtigungstests grün
- [ ] Commit: `feat(telephony): konfigurierbare Abschlussberichte senden`

### Task 12: Frontend-Setup und Aufträge

- [ ] Setup-Wizard mit Test, klarer FRITZ!Box-Anleitung und ehrlichen Fehlern
- [ ] Projekt-Cockpit-Shell und Health-Übersicht
- [ ] Jobeditor mit Mandat, Sofort/Window, Retry, Rückmelde-Checkboxen und Retention
- [ ] unveränderliche Gesprächsvorschau vor Approval
- [ ] Warteschlange, aktiver Versuch, Abbruch und Retrystatus
- [ ] owner-only Member-/Transfer-UI
- [ ] Loading/Empty/Offline/Error/409 und responsive Layout
- [ ] TypeScript, Produktionsbuild und Accessibility-Checks grün
- [ ] Commit: `feat(telephony): Setup und Telefonaufträge im Cockpit bauen`

### Task 13: Frontend-Calls und Archiv

- [ ] Callliste und Detail mit Attempts, Summary und Ergebnis
- [ ] authentifizierter Audioplayer ohne dauerhafte/querybasierte Tokens
- [ ] Transkriptansicht mit Sprecher und Zeitstempel
- [ ] Archiv-, Frist-, Trash-, Restore- und getrennte Delete-Dialoge
- [ ] Export mit Re-Auth und klarer Inhaltsauswahl
- [ ] Auditansicht ohne sensitive Inhalte
- [ ] TypeScript, Produktionsbuild und Browser-Smokes grün
- [ ] Commit: `feat(telephony): Gespräche und Archiv darstellen`

### Task 14: Echte FRITZ!Box-E2E-Verifikation

- [ ] dedizierte Testnebenstelle ohne riskante Wahlrechte einrichten
- [ ] eingehend: ringing, answer, Ansage, listen, reply, barge-in, hangup
- [ ] ausgehend: approved job, busy, no-answer, Retry und successful report
- [ ] Gateway- und Backendneustart in `dialing`, `ringing` und `connected` testen
- [ ] mindestens 20 deutschsprachige Calls mit Namen, Nummern und Rückfragen messen
- [ ] P95 End-of-speech bis erstes Audio dokumentieren; über 1,5 s blockiert Release
- [ ] Consent-Ablehnung, Providerfehler, Stop-all und Credential-Revocation testen
- [ ] Ergebnisse ohne Gesprächsinhalte in einem Verifikationsbericht dokumentieren
- [ ] Commit: `docs(telephony): FRITZ!Box-Pilot verifizieren`

### Task 15: Installer, Upgrade und Abschluss

- [ ] Sidecar-Installation, Version-Pinning, Health und rollbackfähiges Update
- [ ] Deinstallation pausiert Services und erhält Daten
- [ ] Modulupdate migriert bestehende Daten idempotent
- [ ] Backup/Restore einschließlich Keys und Löschtombstones testen
- [ ] vollständige Backend-/Frontend-/Modultests
- [ ] Ruff, TypeScript, Build, Import-Linter und Secret-Scan
- [ ] Security-Review für Auth, IDOR, SSRF, SIP, Toll Fraud, Prompt Injection,
  Credentials, Dateipfade, Streams, Export, Delete und Restore
- [ ] Lizenz-/NOTICE-/Source-Offer für verwendeten Sidecar prüfen
- [ ] PR erst nach grüner CI und echtem Pilot-Gate mergen

## Akzeptanzkriterien

Die verbindlichen Kriterien stehen in `SPEC-V1.md`. Zusätzlich gilt:

- jede Implementierungsetappe ist ein fokussierter PR; Core-Voraussetzungen werden nicht
  zusammen mit dem gesamten Modul gemergt
- Tests werden vor der jeweiligen Implementierung geschrieben und müssen zunächst rot
  sein
- der Fake-Gateway bleibt als reproduzierbarer CI-Vertrag erhalten
- ein echter Telefonanruf ist ein explizites Release-Gate und darf nicht durch Mocks als
  erfüllt markiert werden
- keine Installation verändert die FRITZ!Box automatisch oder öffnet deren SIP/RTP-Ports
  ins Internet
- das Telefonie-Modul bleibt deinstallierbar, ohne den Core von Tel-Agent/LiveKit/SIP-
  Bibliotheken abhängig zu machen

## Nicht in diesem Plan

- verbindliche Buchungen, Bestellungen, Zahlungen oder Verträge
- autonome Massen-/Kampagnenanrufe
- Provider-Nummernverkauf und Billing
- analoge Hardware ohne SIP-Brücke
- Callcenter-Warteschlangen und mehrere parallele Agenten pro Anschluss
- biometrische Sprecheridentifikation
- freie Übergabe aller HydraHive-Tools an Telefonanrufer
