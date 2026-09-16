# Telefonie-Modul V1 — VoIP-Projekte und telefonischer HydraHive-Agent

**Status:** V1-Design; Grundlage, Gatewayvertrag/Fake und flüchtiger Settings-Registrierungstest implementiert, Telefoniefunktionen noch nicht aktiv

**Modul-ID:** `telephony` · **UI-Name:** VoIP

**Ausgangspunkt:** FRITZ!Box als lokaler SIP-Registrar; Transport austauschbar
**Referenzprojekt:** [Dpro-at/Tel-Agent](https://github.com/Dpro-at/Tel-Agent), AGPL-3.0

## 1. Ziel

HydraHive erhält ein optionales Telefonie-Modul, das einen VoIP-Zugang mit einem eigenen
HydraHive-Projekt verbindet. Beim Anlegen eines Zugangs entstehen automatisch ein
Telefonie-Projekt, ein spezialisierter Projekt-Agent, geschützte Telefoniedaten und ein
systemverwaltetes Archiv.

V1 beantwortet eingehende Anrufe und führt manuell freigegebene oder geplante
Informationsanrufe aus. Der Agent darf Informationen einholen, bestätigen und an die
Projektmitglieder zurückmelden. Er darf keine neuen verbindlichen Termine,
Reservierungen, Bestellungen, Zahlungen oder Vertragsänderungen zusagen.

## 2. Verbindliche Produktentscheidungen

1. Ein VoIP-Zugang gehört genau einem automatisch erzeugten Projekt des Typs
   `telephony`.
2. Der anlegende Benutzer wird Projekteigentümer. Bestehende HydraHive-Benutzer können
   durch ihn als vollberechtigte Mitglieder hinzugefügt werden.
3. Alle Mitglieder sehen und bearbeiten sämtliche Telefonie-Fachdaten und dürfen
   Telefonaufträge ausführen. Nur der Eigentümer verwaltet den Mitgliederkreis, löscht
   Verbindung oder Projekt und überträgt Eigentum.
4. Eigentum kann in einem bestätigten Zwei-Parteien-Verfahren an ein bestehendes Mitglied
   übertragen werden. Der bisherige Eigentümer bleibt danach vollberechtigtes Mitglied.
5. Gemeinsame Projektregeln und persönliche Einstellungen sind getrennt. Persönliche
   Einstellungsprofile können als gemeinsame Projektprofile freigegeben oder kopiert
   werden.
6. Ausgehende V1-Anrufe dienen ausschließlich der Informationsbeschaffung und der
   Bestätigung bereits vorgegebener Fakten. Eine interaktive Benutzerfreigabe ist vor
   jedem Auftrag erforderlich; bei geplanten Aufträgen gilt die Planung selbst als
   Freigabe.
7. Ein Auftrag kann sofort oder in einem Zeitfenster ausgeführt werden. Standard ist
   höchstens ein Wiederholungsversuch; Zeitpunkte und Wiederholungsgründe sind global,
   persönlich und pro Auftrag konfigurierbar.
8. Die interne Ergebnisablage in HydraHive ist verpflichtend. Zusätzliche Rückmeldungen
   per Chat, HydraHive-Benachrichtigung, WhatsApp, E-Mail oder Task sind pro Auftrag über
   Checkboxen auswählbar.
9. Jeder Anruf wird technisch live transkribiert. Standardmäßig werden Zusammenfassung,
   strukturiertes Ergebnis und vollständiges Texttranskript gespeichert; Audio ist für
   archivierte Vorgänge eingeschlossen. Die Speicherung setzt die erforderliche
   transparente Ansage und Einwilligungs-/Rechtsgrundlagenlogik voraus.
10. Nicht archivierte Volltranskripte haben standardmäßig 30 Tage Aufbewahrungszeit.
    Frist, Zusammenfassung-only und bewusste Archivierung sind pro Auftrag auswählbar.
11. Ein Archiveintrag umfasst standardmäßig Auftrag, Versuche, Audio, Volltranskript,
    Zusammenfassung, strukturiertes Ergebnis und Metadaten. Bestandteile oder der ganze
    Vorgang können manuell gelöscht werden.
12. Geheimnisse liegen nie als Workspace-Dateien vor und werden nach dem Speichern nie
    im Klartext zurückgegeben.
13. Der Telefonietransport läuft als isolierter Sidecar. HydraHive bleibt Source of Truth
    für Benutzer, Projekte, Rechte, Aufträge, Agenten, Ergebnisse und Archivmetadaten.
14. Die FRITZ!Box oder PBX wird nicht aus dem Internet erreichbar gemacht. Der Gateway
    läuft im selben vertrauenswürdigen LAN oder auf demselben Host.

## 3. Problem und Nutzerablauf

Ein Benutzer soll keine SIP-, RTP-, systemd- oder Containerdetails verstehen müssen.
Der erwartete Ablauf ist:

1. Telefonie-Modul installieren.
2. „VoIP-Zugang anlegen“ öffnen.
3. FRITZ!Box/PBX auswählen und SIP-Registrar, Benutzername und Passwort eingeben.
4. Verbindung testen.
5. HydraHive erzeugt Projekt, Telefon-Agent, Verbindung und sichere Ablage.
6. Benutzer ordnet ein- und ausgehende Rufnummern beziehungsweise eine dedizierte
   FRITZ!Box-IP-Telefon-Nebenstelle zu.
7. Testanruf durchführen.
8. Mitglieder, Agent, Zeiten, Rückmeldungen und Aufbewahrung konfigurieren.

Ein Benutzer mit mehreren logisch getrennten Anschlüssen erhält mehrere
Telefonie-Projekte. Mehrere Rufnummern desselben Anschlusses dürfen später demselben
Projekt zugeordnet werden; V1 verwaltet genau eine aktive SIP-Registrierung pro Projekt.

## 4. Umfang V1

### 4.1 Eingehende Anrufe

- dedizierte SIP-Nebenstelle registrieren
- eingehenden Anruf annehmen oder nach Projektregeln ablehnen
- KI- und Aufzeichnungs-/Transkriptionshinweis abspielen
- Echtzeit-STT, HydraHive-Agentenantwort und Streaming-TTS
- Unterbrechung der Sprachausgabe bei neuer Sprache des Anrufers (`barge-in`)
- Wissensfragen beantworten und strukturierte Nachricht aufnehmen
- keine authentifizierungsbedürftige Aktion allein aufgrund der Rufnummer
- Gespräch beenden und Ergebnis im Projekt speichern
- menschliche Weiterleitung nur, wenn ein explizites Ziel konfiguriert ist; andernfalls
  Rückrufwunsch erfassen

### 4.2 Ausgehende Informationsaufträge

Beispiele:

- Liefer- oder Reparaturstatus erfragen
- Öffnungszeiten und Zuständigkeit klären
- bestehenden Termin bestätigen
- Verfügbarkeit erfragen, ohne verbindlich zu buchen
- Ansprechpartner oder benötigte Unterlagen erfragen

Jeder Auftrag enthält mindestens:

- Kontakt und normalisierte E.164-Zielnummer
- Ziel und Hintergrund
- erlaubte Informationen, die der Agent nennen darf
- konkrete Fragen beziehungsweise gewünschte Ergebnisfelder
- ausdrücklich verbotene Zusagen oder Aktionen
- Ausführungsmodus `now` oder `window`
- Zeitfenster und Zeitzone
- Wiederholungsregel
- Rückmeldekanäle und Detailgrad
- Aufbewahrungs-/Archiventscheidung
- Revision und Freigabe-Snapshot

Der Agent darf nur innerhalb dieses Mandats sprechen. Verlangt die Gegenseite eine
Entscheidung oder Zusage, antwortet er sinngemäß, dass er dies nicht bestätigen kann,
und meldet die offene Entscheidung zurück.

### 4.3 Nicht in V1

- verbindliche neue Termine, Reservierungen, Bestellungen oder Verträge
- Zahlungen oder Preiszusagen
- unbestätigte, autonom vom LLM initiierte Anrufe
- Kampagnen, Rundruf oder Callcenter-Funktionen
- freie Wahl beliebiger vom LLM erzeugter Rufnummern
- Notruf-, Premium-, Satelliten- oder Mehrwertdienst-Anrufe
- Rufnummernverkauf oder Provider-Abrechnung
- Stimmerkennung als Authentifizierung
- verborgenes Aufzeichnen
- analoger Leitungsanschluss ohne vorgelagerten SIP-/ATA-/PBX-Adapter
- vollständige Übernahme des Tel-Agent-Dashboards, seiner Benutzerverwaltung oder DB

## 5. Architektur

```text
FRITZ!Box / PBX
   │ SIP-Signalisierung + RTP-Audio
   ▼
Telephony Gateway (isolierter Sidecar)
   │ Ereignisse, Live-Transkripte, gestreamter Antworttext
   ▼
HydraHive Telephony Module
   ├── Projekt- und Rechteprüfung
   ├── Auftrags-/Call-State-Machine
   ├── Zeitplanung und Retry
   ├── dedizierter Telefon-Agent / Runner
   ├── Ergebnis, Benachrichtigung, Audit
   └── verschlüsselter Artifact Store
```

### 5.1 Verantwortungsgrenzen

**HydraHive/Core besitzt:**

- stabile Benutzeridentität und Authentifizierung
- Projekt, Projekt-Agent, Mitglieder, Eigentum und Audit
- allgemeinen Credential-/Secret-Grundvertrag
- Agenten-Runner, Sessions, Tools und Benachrichtigungen
- Modul-Lifecycle und Backup-Orchestrierung

**Telefonie-Modul besitzt:**

- VoIP-Verbindungen als projektgebundene Fachressource
- persönliche und gemeinsame Telefonie-Einstellungen
- Telefonaufträge, Versuche und Call-Metadaten
- Zeitfenster, Retry und Freigaben
- telefoniespezifischen Agentenvertrag
- verschlüsselte Audio-/Transkript-Artefakte und Aufbewahrung
- Telefonie-Cockpit und Telefonie-Audit

**Gateway besitzt:**

- SIP-Registrierung und Rufaufbau
- RTP, Codec und Audio-Puffer
- Streaming-STT und Streaming-TTS
- Voice Activity Detection, Endpointing und Barge-in
- Leitungskapazität und technische Call-Steuerung
- technische Providerzustände

Der Gateway darf weder HydraHive-Mitgliedschaften verwalten noch selbstständig
Telefonaufträge erfinden oder dauerhaft führende Fachdaten halten.

### 5.2 Tel-Agent-Entscheidung

Tel-Agent ist eine geeignete Referenz und mögliche Sidecar-Basis, aber kein ungeprüfter
Runtime-Download für V1. Der aktuelle Upstream enthält Voice-Interfaces, Anbieter,
Call-Archivlogik und eine LiveKit-Bindung; sein direkter SIP-Modus ist noch nicht als
vollständiger FRITZ!Box-Client nachgewiesen, und die LiveKit-Bindung bezeichnet sich
selbst als nicht auf einer echten Leitung bewiesen.

Daher gelten folgende Gates:

1. Kein Produktversprechen „FRITZ!Box-kompatibel“ vor einem echten E2E-Test.
2. Der HydraHive-Gatewayvertrag bleibt unabhängig von Tel-Agent.
3. Ein Tel-Agent-Fork läuft ausschließlich als separater Prozess/Container; kein
   AGPL-Code wird in den HydraHive-Core kopiert.
4. Änderungen am AGPL-Sidecar werden gemäß Lizenz als Quellcode bereitgestellt.
5. Falls der direkte SIP-Transport nicht tragfähig ist, darf Asterisk, FreeSWITCH oder
   ein lokaler LiveKit-SIP-Aufbau denselben Gatewayvertrag implementieren, ohne das
   Modul-Datenmodell zu ändern.

### 5.3 Gateway-Vertrag

Der Sidecar bindet standardmäßig nur an Loopback oder einen Unix-Socket. Wenn er auf
einem anderen LAN-Host läuft, sind mTLS oder ein rotierbares maschinengebundenes Token
und eine feste Ziel-Allowlist verpflichtend.

Kontrolloperationen:

- Verbindung testen, registrieren, pausieren und Status lesen
- ausgehenden Versuch mit idempotentem `attempt_id` starten
- Anruf abbrechen oder auflegen
- eingehenden Anruf annehmen oder ablehnen
- TTS-Ausgabe streamen und sofort abbrechen

Gateway-Ereignisse:

- `incoming`, `dialing`, `ringing`, `connected`, `speech.partial`, `speech.final`
- `playback.started`, `playback.stopped`, `dtmf`, `voicemail.detected`
- `busy`, `no_answer`, `rejected`, `failed`, `disconnected`

Jedes Ereignis trägt `project_id`, `connection_id`, `call_id`, `attempt_id`, monotone
Sequenznummer und Zeitstempel. HydraHive verwirft fremde Projekt-/Verbindungs-Kombinationen
und bereits verarbeitete Sequenzen.

Audio bleibt im Gateway-Pfad. HydraHive erhält Live-Text und schreibt nur dann Audio in
den Artifact Store, wenn die Aufzeichnung für den konkreten Call erlaubt ist.

## 6. HydraHive-Projektintegration

### 6.1 Automatische Anlage

Das Modul bietet einen authentifizierten Setup-Endpunkt für normale Benutzer. Es lockert
nicht den generischen, derzeit admin-only geschützten Core-Endpunkt zur freien
Projektanlage.

Nach erfolgreichem Verbindungstest führt ein Orchestrator aus:

1. Projekt mit `project_type="telephony"`,
   `created_by_user_id=<principal.user_id>`, dem aktuellen Anzeigenamen des Erstellers,
   `membership_policy="owner_only"` und `lifecycle_policy="owner_only"` anlegen.
2. dedizierten Projekt-Agenten erzeugen
3. projektbezogene Verbindung und verschlüsseltes Secret anlegen
4. persönliche Default-Einstellungen für den Eigentümer anlegen
5. geschützten Projekt-Artifact-Bereich erzeugen
6. Gatewayregistrierung aktivieren

Scheitert ein Schritt, entfernt eine kompensierende Transaktion alle bereits erzeugten
Bestandteile oder markiert das Setup sichtbar als `repair_required`. Es darf kein
unsichtbares Halbprojekt entstehen.

Default-Quota: höchstens zehn aktive Telefonie-Projekte pro Eigentümer; Systemadmins
können die Grenze konfigurieren.

### 6.2 Mitglieder und Rechte

Vorhandene Core-Projektrollen werden verwendet, aber ihre Identitäten müssen vor dem
Telefonie-Release auf unveränderliche Core-`user_id`s gehärtet werden. Das heutige
username-only-Format reicht für sensible Gesprächsarchive nicht aus: Ein gelöschter und
unter demselben Namen neu angelegter Benutzer darf keine alte Mitgliedschaft erben.
Member-Einträge speichern daher `user_id`, Anzeigename und Rolle; Namensänderungen
ändern nicht die Identität.

- Eigentümer: über `created_by_user_id` implizites Projekt-`admin` plus exklusive
  Mitglieds-/Lifecycle-Rechte
- freigegebenes Mitglied: Projekt-`admin` für alle operativen Telefoniefunktionen

Alle Mitglieder dürfen:

- alle Telefoniedaten sehen und bearbeiten
- Aufträge erstellen, freigeben, planen, starten, abbrechen und archivieren
- Audio, Transkript und Berichte lesen beziehungsweise fachlich löschen
- Agent, gemeinsame Regeln und Profile ändern
- VoIP-Verbindung testen und gespeicherte Zugangsdaten ersetzen

Nur der aktuelle Principal mit `project.created_by_user_id == principal.user_id` darf:

- Mitglieder hinzufügen, entfernen oder Rollen ändern
- Eigentum übertragen
- Verbindung endgültig entfernen
- gesamtes Telefonie-Projekt löschen

`membership_policy="owner_only"` muss in den zentralen Core-Projektrouten durchgesetzt
werden; eine nur im Telefonie-Frontend versteckte Schaltfläche reicht nicht. Ein
Systemadmin besitzt ausschließlich einen separat auditierten Break-glass-Pfad für ein
verwaistes Projekt.

### 6.3 Eigentumsübertragung

- Ziel muss ein aktuelles Projektmitglied sein.
- aktueller Eigentümer authentifiziert sich erneut
- Übertragungsanfrage läuft nach 48 Stunden ab
- Ziel nimmt mit eigener aktiver Session ausdrücklich an
- höchstens eine offene Anfrage pro Projekt
- Annahme ändert Eigentümer und Mitgliedschaften atomar
- bisheriger Eigentümer wird als Projekt-`admin` in `members` aufgenommen
- neuer Eigentümer wird aus der expliziten Memberliste entfernt und ist über
  `created_by_user_id` implizit Eigentümer; `created_by` bleibt nur kompatibler
  Anzeigename
- VoIP-Verbindung, Archive und laufende Aufträge bleiben unverändert
- alle Mitglieder werden informiert; Audit enthält keine Secrets

## 7. Einstellungen

### 7.1 Gemeinsame Projekteinstellungen

- Anzeigename und Rufnummern
- Telefon-Agent und Stimme
- Sprache, Zeitzone und Geschäftszeiten
- eingehend aktiv/pausiert
- ausgehend aktiv/pausiert
- erlaubte Länder und Kontakte
- maximale Call-Dauer, Versuche pro Stunde und Anrufe pro Tag
- Retry-Obergrenze; hart maximal drei weitere Versuche
- Einwilligungs-/Ansagetext
- Default-Aufbewahrung und Archivvorschläge
- menschliches Übergabe-/Rückrufziel
- Providerstatus und Kostenwarnschwellen

### 7.2 Persönliche Einstellungen je Mitglied

- bevorzugte Rückmeldekanäle
- Detailgrad je Kanal
- persönliche Ruhezeiten
- Default-Retry innerhalb der Projektobergrenze
- Default-Aufbewahrung
- persönliche Auftragsvorlagen
- bevorzugte Sprache und Zeitzone für UI/Benachrichtigung

### 7.3 Gemeinsame Einstellungsprofile

Ein persönliches Profil kann:

- privat bleiben
- als gemeinsames Profil veröffentlicht werden
- von Mitgliedern direkt verwendet werden
- als unabhängige persönliche Kopie übernommen werden

Gemeinsame Profile sind von allen Projektmitgliedern bearbeitbar, besitzen eine Revision
und erzeugen Audit-Ereignisse. Änderungen gelten nur für zukünftige Aufträge. Jeder
freigegebene Auftrag speichert einen unveränderlichen Einstellungs-Snapshot; spätere
Profiländerungen verändern ihn nicht still.

## 8. Zustandsmodelle

### 8.1 Telefonauftrag

```text
draft
  → pending_approval
  → approved
  → queued | scheduled
  → active
  → succeeded | needs_review | exhausted | cancelled | failed | expired
```

- Nur eine interaktive, aktuell authentifizierte Person kann `approved` erzeugen.
- Ein Agent oder externer Callback darf höchstens `draft` erzeugen.
- Änderung von Nummer, Ziel, Mandat, Zeitfenster oder Sicherheitsgrenzen nach Freigabe
  setzt den Auftrag zurück auf `pending_approval`.
- Der Scheduler startet nur `approved`-Snapshots.

### 8.2 Anrufversuch

```text
queued → claimed → dialing → ringing → connected → completed
                           ↘ busy | no_answer | rejected | failed | cancelled
```

Ein atomarer Lease/Claim und die gatewayweit eindeutige `attempt_id` verhindern doppelte
Anrufe nach Neustart, Timeout oder konkurrierenden Workern. Pro Auftrag darf nur ein
Versuch aktiv sein.

### 8.3 Retry

Default:

- ein weiterer Versuch
- bei `busy` nach 15 Minuten
- bei `no_answer` nach 30 Minuten
- bei eindeutig transientem technischem Fehler nach 5 Minuten
- keine Mailboxnachricht

Kein automatischer Retry bei:

- erfolgreicher Verbindung, auch wenn die gewünschte Information fehlt
- falschem Ansprechpartner
- ungültiger Nummer
- ausdrücklicher Ablehnung weiterer Anrufe
- rechtlicher/technischer Sperre
- abgelaufenem Zeitfenster

Nennt die erreichte Person einen konkreten späteren Zeitpunkt, erzeugt der Agent nur
einen Vorschlag `needs_review`; V1 plant daraus nicht eigenmächtig einen neuen Call.

## 9. Agentenvertrag

Das Telefonie-Projekt erhält einen spezialisierten Agenten mit kleinem, fest begrenztem
Toolset. Ein normaler Projekt-Agent mit allen Coding-, Shell-, Datei- oder
Administrationswerkzeugen wird nicht an die Telefonleitung gehängt.

Pflichtregeln:

- als digitaler Assistent und Auftraggeber identifizieren
- Aufzeichnungs-/Transkriptionsstatus transparent nennen
- nur Informationen einholen oder vorgegebene Fakten bestätigen
- keine verbindlichen neuen Zusagen, Buchungen, Bestellungen oder Zahlungen
- keine geheimen Projektinformationen nennen, die nicht im Mandat freigegeben sind
- keine Person anhand der Rufnummer als sicher authentifiziert behandeln
- bei sensiblen oder unerwarteten Fragen ablehnen und `needs_review` melden
- bei Tool-/Providerfehlern nicht halluzinieren
- keine neue Zielnummer aus Gespräch oder Modelltext selbst wählen
- Gespräch nach Zielerreichung oder Zeitlimit höflich beenden

Erlaubte Tools in V1:

- projektbezogene, freigegebene Wissenssuche
- strukturierte Nachricht/Ergebnisfelder schreiben
- Call beenden
- menschliche Übergabe beziehungsweise Rückrufwunsch anfordern

Alle weiteren HydraHive-Tools sind standardmäßig aus. Spätere Tools benötigen eine
separate Spec und explizite Bestätigungsgates.

Jeder Call erzeugt eine normale HydraHive-Session mit `project_id`, `call_id` und
`direction` in den Metadaten. Die Session ist für Projektmitglieder im Cockpit sichtbar.
Der Telefonie-Runner streamt LLM-Text zum Gateway; ein vollständiges Antwort-zu-Datei-TTS
oder der heutige Batch-STT-Endpunkt genügt nicht für Live-Telefonie.

## 10. Speicherung und Archiv

### 10.1 Source of Truth

Strukturierte Metadaten und Zustände liegen in den Modul-Tabellen der gemeinsamen
HydraHive-Datenbank. Binäre und umfangreiche sensible Artefakte liegen im geschützten,
systemverwalteten Projektbereich.

Nicht verwenden:

- normale, agentenbeschreibbare Workspace-Pfade für Originale
- Klartext-SIP-Secrets in `config.json`, `.env`, Logs oder Auftrags-Snapshots
- personenbezogene Daten in Dateinamen

Vorgesehener Bereich:

```text
$HH_DATA_DIR/projects/<project_id>/telephony/
├── objects/<call_id>/
│   ├── audio.ogg.enc
│   ├── transcript.jsonl.enc
│   ├── summary.md.enc
│   └── result.json.enc
├── exports/
└── trash/
```

Die normalen Projekt-Workspaces unter
`$HH_DATA_DIR/workspaces/projects/<project_id>/` erhalten nur bewusst erzeugte Exporte,
zum Beispiel eine redigierte Zusammenfassung. Agenten greifen auf Originale nur über
telefoniespezifische, autorisierte Tools zu.

### 10.2 Verschlüsselung

- eigener zufälliger Data Encryption Key pro Telefonie-Projekt
- Verschlüsselung großer Artefakte mit authentifizierter Verschlüsselung
- Projektkey durch einen installationsweiten Masterkey geschützt
- Masterkey nicht in DB, Logs oder normalen Projektbackups
- SIP-Passwort und Providerkeys im projektbezogenen Secret Store
- gespeicherte Secrets sind nur ersetzbar, nie revealbar
- Exporte entschlüsselt nur nach erneuter Authentifizierung; Ausgabeort und Inhalt werden
  ausdrücklich bestätigt

### 10.3 Transkript, Zusammenfassung und Audio

- Live-Transkript: zur Gesprächsführung temporär erforderlich
- Volltranskript: Sprecher, Zeitstempel, STT-Konfidenz und Sprache
- Zusammenfassung: kurz und menschenlesbar
- strukturiertes Ergebnis: gewünschte Felder, offene Fragen, Ergebnisstatus,
  `commitment_made=false`
- Audio: Ogg/Opus oder ein gleichwertig browserfähiges, dokumentiertes Format

Normale Rückmeldungen und externe Kanäle enthalten standardmäßig nur die
Zusammenfassung. Volltranskript oder Audio verlassen den geschützten Bereich nie ohne
expliziten Export.

### 10.4 Einwilligung und Ablehnung

Vor persistenter Audio-/Volltranskript-Speicherung spielt der Agent die konfigurierte
Ansage ab. Die Projektkonfiguration entscheidet rechtskonform zwischen:

- Zustimmung erkannt: konfigurierte Speicherung beginnt
- Ablehnung erkannt: keine persistente Audioaufnahme und kein Volltranskript; temporäre
  Sprachdaten nach Abschluss verwerfen; nur zulässige sachliche Zusammenfassung speichern
- unklar: einmal nachfragen, danach wie Ablehnung behandeln

Die Einwilligungsentscheidung wird ohne unnötigen Gesprächsinhalt auditiert. Das Modul
behauptet keine pauschale Rechtskonformität; Betreiber müssen Ansage, Rechtsgrundlage und
Fristen für ihren Einsatz prüfen.

### 10.5 Aufbewahrung

Pro Auftrag genau eine Regel:

- Standard: Volltranskript nach 30 Tagen löschen
- benutzerdefinierte Frist
- nach Zusammenfassung Volltranskript/Audio löschen
- vollständig archivieren

Archiviert werden standardmäßig:

- Auftrag und Freigabe-Snapshot
- alle Versuche
- Audioaufnahme
- Volltranskript
- Zusammenfassung
- strukturiertes Ergebnis
- Anhänge und technische Metadaten

Ein Archiv kann eine definierte Frist oder `unlimited` tragen. Unbegrenzt ist nie der
unbemerkte globale Default.

### 10.6 Manuelles Löschen

Projektmitglieder können bei einem Fachvorgang getrennt löschen:

- Audio
- Volltranskript
- Anhänge
- gesamten Fachvorgang

Normale Löschung verschiebt verschlüsselte Artefakte standardmäßig für sieben Tage in
den Papierkorb. „Sofort endgültig löschen“ überspringt ihn. DB-Referenzen, Suchdaten,
abgeleitete Inhalte und Caches werden gemeinsam bereinigt. Im Audit bleibt nur ein
inhaltsloser Löschvermerk ohne Rufnummer, Zusammenfassung oder Gesprächsinhalt.

Backups können gelöschte Daten bis zum Ende ihrer konfigurierten Backup-Frist enthalten.
Die UI muss diese Grenze ehrlich benennen; Restore-Prozesse wenden persistente
Löschtombstones erneut an, bevor wiederhergestellte Telefoniedaten freigegeben werden.

## 11. Datenmodell

Vorgesehene Tabellen mit Präfix `module_telephony_`:

### `connections`

- `connection_id`, `project_id` (unique), `status`, `transport`
- `registrar_host`, `registrar_port`, `sip_user_display_mask`
- `credential_ref`, `inbound_number`, `outbound_number`
- `gateway_id`, `last_registered_at`, `last_error_code`
- `revision`, `created_by_user_id`, `created_at`, `updated_at`

### `project_settings`

- `project_id` (unique), `timezone`, `language`
- `inbound_enabled`, `outbound_enabled`, `business_hours_json`
- `allowed_countries_json`, `max_call_seconds`, `calls_per_hour`, `calls_per_day`
- `max_retries`, `consent_prompt`, `default_retention_policy_json`
- `revision`, `updated_by_user_id`, `updated_at`

### `user_preferences`

- `project_id`, `user_id` (unique pair)
- `notification_channels_json`, `detail_by_channel_json`
- `quiet_hours_json`, `retry_defaults_json`, `retention_default_json`
- `locale`, `timezone`, `revision`, `updated_at`

### `setting_profiles`

- `profile_id`, `project_id`, `owner_user_id`, `name`
- `visibility` (`private|project`), `settings_json`, `revision`
- `created_at`, `updated_at`

### `call_jobs`

- `job_id`, `project_id`, `created_by_user_id`, `approved_by_user_id`
- `direction` (`outbound`; eingehend entsteht direkt als Call)
- `contact_label`, `target_e164`, `purpose`, `context`
- `allowed_disclosures_json`, `questions_json`, `forbidden_actions_json`
- `execution_mode`, `window_start`, `window_end`, `timezone`
- `retry_policy_json`, `notification_policy_json`, `retention_policy_json`
- `approval_snapshot_hash`, `status`, `revision`
- `next_attempt_at`, `created_at`, `updated_at`, `finished_at`

### `call_attempts`

- `attempt_id`, `job_id`, `ordinal`, `status`, `lease_until`
- `gateway_call_ref`, `started_at`, `connected_at`, `ended_at`
- `failure_code`, `failure_detail_safe`, `retry_at`

### `calls`

- `call_id`, `project_id`, `job_id` nullable, `connection_id`
- `direction`, `remote_e164`, `status`, `consent_state`
- `session_id`, `started_at`, `connected_at`, `ended_at`, `duration_seconds`
- `result_status`, `result_encrypted`, `summary_encrypted`
- `archived_at`, `retention_until`, `deleted_at`, `revision`

### `artifacts`

- `artifact_id`, `call_id`, `kind` (`audio|transcript|summary|result|attachment`)
- `storage_key`, `cipher`, `content_type`, `size_bytes`, `sha256`
- `retention_until`, `trash_until`, `deleted_at`, `created_at`

### `ownership_transfers`

Core-Projektressource, nicht modulspezifisch:

- `transfer_id`, `project_id`, `from_user_id`, `to_user_id`
- `status`, `expires_at`, `created_at`, `accepted_at`
- `revision`

### `audit_events`

- `event_id`, `project_id`, `actor_user_id`, `action`
- `entity_type`, `entity_id`, `safe_details_json`, `created_at`

Alle Fremdschlüssel tragen Projektgrenzen. Ein Service darf nie nur über eine globale
`call_id` autorisieren; er lädt Ressource plus Projekt und prüft die aktuelle
Mitgliedschaft mit stabilem `AuthPrincipal.user_id`. Fremde oder entfernte Ressourcen
antworten mit 404 statt ihre Existenz offenzulegen.

## 12. Zeitplanung und Nebenläufigkeit

Telefonaufträge verwenden eigene One-shot-/Window-Daten und nicht die bestehende
Intervalltabelle `scheduled_agent_tasks`. Wiederverwendet werden dürfen Scheduler-
Lifecycle, Wake-up-Mechanismus und atomare Claim-Patterns.

Regeln:

- DB ist Source of Truth für `next_attempt_at`
- atomarer Claim mit Lease; abgelaufene Lease darf sicher übernommen werden
- Gateway-Aufruf immer idempotent über `attempt_id`
- verpasste Zeitfenster werden `expired`, nicht nachträglich blind gewählt
- Neustart rekonstruiert fällige Aufträge aus der DB
- Projekt- oder Verbindungspause verhindert neue Claims
- maximal ein aktiver Versuch je VoIP-Verbindung, sofern der Gateway keine höhere
  explizit konfigurierte Leitungskapazität meldet
- persönliche Ruhezeiten verändern nur Rückmeldungen; Projektgeschäftszeiten begrenzen
  tatsächliche Anrufe
- Uhrzeiten werden als UTC plus ursprünglicher IANA-Zeitzone gespeichert
- Sommerzeitlücken werden auf den nächsten gültigen Zeitpunkt geschoben;
  doppelte Ortszeiten führen nur zu einem Versuch

## 13. Benachrichtigungen und Berichte

Pro Auftrag auswählbar:

- verpflichtende interne Ablage
- Antwort in der erzeugenden HydraHive-Session
- HydraHive-Benachrichtigung
- WhatsApp
- E-Mail
- neuen persistenten Task anlegen

Pro Ergebnis (`success`, `needs_review`, `unreachable`, `technical_failure`) kann ein
anderes Kanalset gewählt werden. Detailgrade:

- nur Status
- kurze Zusammenfassung
- vollständiger Bericht

Volltranskripte und Audio werden nicht automatisch über externe Kanäle versendet.
Externe Zustellung verwendet die persönlichen Credentials des Empfängers und respektiert
seine Ruhezeiten. Ein fehlgeschlagener Benachrichtigungskanal ändert nicht das fachliche
Call-Ergebnis; er wird separat sichtbar wiederholt.

## 14. API-Oberfläche

Vorgesehen unter `/api/modules/telephony`.

### Setup und Verbindung

- `POST /connections/test`
- `POST /connections` — legt Verbindung plus Telefonie-Projekt an
- `GET /projects/{project_id}/connection`
- `PATCH /projects/{project_id}/connection`
- `PUT /projects/{project_id}/connection/credentials`
- `POST /projects/{project_id}/connection/test`
- `POST /projects/{project_id}/connection/pause`
- `POST /projects/{project_id}/connection/resume`
- `DELETE /projects/{project_id}/connection` — owner-only

### Einstellungen und Profile

- `GET|PATCH /projects/{project_id}/settings`
- `GET|PATCH /projects/{project_id}/preferences/me`
- `GET|POST /projects/{project_id}/profiles`
- `PATCH|DELETE /projects/{project_id}/profiles/{profile_id}`
- `POST /projects/{project_id}/profiles/{profile_id}/copy`

### Telefonaufträge

- `GET|POST /projects/{project_id}/jobs`
- `GET|PATCH|DELETE /projects/{project_id}/jobs/{job_id}`
- `POST /projects/{project_id}/jobs/{job_id}/approve`
- `POST /projects/{project_id}/jobs/{job_id}/run`
- `POST /projects/{project_id}/jobs/{job_id}/cancel`
- `GET /projects/{project_id}/jobs/{job_id}/attempts`

### Calls und Archiv

- `GET /projects/{project_id}/calls`
- `GET /projects/{project_id}/calls/{call_id}`
- `GET /projects/{project_id}/calls/{call_id}/transcript`
- `GET /projects/{project_id}/calls/{call_id}/audio` — authentifizierter Stream,
  keine Query-JWTs oder dauerhaften Dateilinks
- `POST /projects/{project_id}/calls/{call_id}/archive`
- `PATCH /projects/{project_id}/calls/{call_id}/retention`
- `DELETE /projects/{project_id}/calls/{call_id}/artifacts/{kind}`
- `DELETE /projects/{project_id}/calls/{call_id}`
- `POST /projects/{project_id}/trash/{call_id}/restore`
- `POST /projects/{project_id}/export`

### Eigentum

Generischer Core-Vertrag für `owner_only`-Projekte:

- `POST /api/projects/{project_id}/ownership-transfer`
- `POST /api/projects/{project_id}/ownership-transfer/{transfer_id}/accept`
- `DELETE /api/projects/{project_id}/ownership-transfer/{transfer_id}`

### Gateway-intern

- kurzlebige maschinengebundene Authentifizierung
- feste Gateway-ID und Connection-Bindung
- Rate Limit und Body Limits
- Replay-Schutz über Event-ID/Sequenz
- keine aus dem Internet erreichbare Callback-Route als Default

## 15. Frontend

Telefonie-Projekte erscheinen im normalen Projekt-Cockpit und öffnen eine
modulspezifische Ansicht mit:

1. **Übersicht** — Registrierung, aktive Leitung, Calls heute, offene Entscheidungen
2. **Neuer Auftrag** — Ziel, Mandat, Vorschau, Sofort/Planung, Retry,
   Rückmelde-Checkboxen und Aufbewahrung
3. **Warteschlange** — geplant, wartet, aktiver Versuch, abbrechen
4. **Gespräche** — Filter nach Richtung, Kontakt, Status und Zeitraum
5. **Archiv** — archivierte Vorgänge, Frist, Export, getrennte Löschung
6. **Telefon-Agent** — Persona, Stimme, Sprache, freigegebenes Wissen
7. **Einstellungen** — Verbindung, Zeiten, Grenzen, Ansage, persönliche Defaults,
   gemeinsame Profile
8. **Mitglieder** — sichtbar für alle; Änderungen ausschließlich für Eigentümer
9. **Audit** — sichere Ereignisse ohne Gesprächsinhalte oder Secrets

Pflichtzustände jeder Ansicht: leer, lädt, offline, Fehler, Konflikt (HTTP 409), Erfolg.
Aktive Calls und irreversible Aktionen werden nicht allein durch Farbe dargestellt.

## 16. Sicherheit

### 16.1 Autorisierung

- alle Fachrouten verwenden `require_principal`, nicht Legacy-Rollen-Snapshots
- aktuelle Projektmitgliedschaft bei jedem Request und jedem Scheduler-Claim prüfen
- `project_id` nie aus Body vertrauen, wenn er bereits im Pfad steht
- owner-only zentral und serverseitig durchsetzen
- entfernte Mitglieder verlieren Zugriff und laufende persönliche Streams sofort
- Systemadminzugriff auf Gesprächsinhalte ist kein stiller Default; Break-glass wird
  begründet und auditiert

### 16.2 Telefonie- und Kostenmissbrauch

- ausgehend zunächst standardmäßig deaktiviert
- Freigabe-Snapshot durch einen Menschen
- E.164-Parsing mit bewährter Bibliothek
- Default nur gespeicherte beziehungsweise ausdrücklich bestätigte Kontakte
- Länder-Allowlist
- Notruf-, Premium-, Satelliten- und internationale Sonderbereiche hart sperren
- Projekt-/Benutzer-/Zielnummer-Limits pro Stunde und Tag
- maximale Gesprächsdauer
- Provider-/FRITZ!Box-Wahlsperren als zusätzliche äußere Schutzschicht
- keine Shell-Interpolation oder frei konstruierte SIP-URIs
- „Stop all calls“-Schalter und sofortige Credential-Revocation

### 16.3 Prompt Injection und Datenabfluss

- Telefoninhalt ist untrusted input
- spezialisiertes minimales Toolset
- Mandat und verbotene Aktionen stehen in nicht überschreibbaren Systemregeln
- externe Person kann keine neuen Tools, Nummern oder Ziele freigeben
- Projektwissen nur nach expliziter Zuordnung zum Telefon-Agenten
- keine Secrets, internen Prompts oder vollständigen Mitgliederlisten nennen
- sensible Datenfreigabe ist pro Auftrag als strukturierte Allowlist gespeichert

### 16.4 Netzwerk und Secrets

- keine SIP-/RTP-Freigabe ins Internet für die FRITZ!Box
- Sidecar auf Loopback/Unix-Socket oder authentifiziertem privaten LAN
- SSRF-Schutz für Registrar-Hosts und Gatewayziele; nur erlaubte lokale/private Ziele
  beziehungsweise explizit konfigurierte Provider
- Credentials verschlüsselt, maskiert und redaktionssicher geloggt
- Fehlermeldungen zeigen keine SIP-Challenges, Passwörter oder internen Stacktraces
- Installer legt Firewall-/Service-Defaults deny-by-default an

### 16.5 Datenschutz

- transparente KI-Identifikation
- konfigurierbare, rechtlich geprüfte Aufzeichnungsansage
- Datensparsamkeit und klare Fristen
- getrennte Löschung von Audio, Transkript und Ergebnis
- Zugriff und Export auditieren
- keine personenbezogenen Inhalte in normalen Logs, Metriken oder Dateinamen
- externe Benachrichtigungen standardmäßig nur als Zusammenfassung

## 17. Betrieb und Beobachtbarkeit

Health-Status umfasst:

- Gateway erreichbar
- SIP registriert
- STT/LLM/TTS verfügbar
- Projektkey/Artifact Store verfügbar
- Scheduler aktiv
- Leitungskapazität
- letzter erfolgreicher Testanruf

Metriken ohne Gesprächsinhalt:

- Rufaufbauzeit
- End-of-speech bis erstes Audio
- STT-/LLM-/TTS-Latenz
- Barge-in-Anzahl
- Ergebnis-/Fehlerklassen
- Retry-Anzahl
- aktive und wartende Calls

Ziel für natürliche V1-Gespräche: erstes Audio möglichst unter 800 ms nach erkanntem
Sprechende; über 1,5 Sekunden gilt als nicht produktionsreif. Ein Providerfehler erzeugt
keine stille tote Leitung, sondern definierte Ansage, Abbruch und Alarm.

## 18. Backup, Restore und Deinstallation

- Modulbackup umfasst DB-Fachdaten und verschlüsselte Artefakte.
- Secrets und Schlüsselmaterial folgen dem HydraHive-Secret-Backupvertrag und werden
  nicht ungeschützt neben dem Datenbackup abgelegt.
- Restore prüft Projektmitgliedschaft, Key-Verfügbarkeit und Löschtombstones vor Freigabe.
- Deinstallation des Moduls pausiert Verbindungen und Calls, löscht aber keine Daten
  automatisch.
- Projektlöschung ist owner-only, zeigt Anzahl von Calls/Archiven/Artefakten, bietet
  Export und verlangt doppelte Bestätigung.
- Erst danach werden Gatewayregistrierung, Secrets, DB-Zeilen, Projekt-Agent,
  System-Artefakte und Workspace kaskadierend entfernt.
- Eine Deinstallation oder ein Projektdelete darf niemals in einen eingebundenen
  Fremdpfad hinein löschen.

## 19. Rollout-Stufen

### V0 — Transport-Spike, kein Kundenrelease

- dedizierte FRITZ!Box-IP-Telefon-Nebenstelle
- echter eingehender Testanruf
- echter ausgehender Testanruf an freigegebene eigene Testnummer
- Audio in beide Richtungen, STT, Hydra-Runner, TTS und Barge-in messen
- Gateway nach Neustart ohne Doppelanruf

### V1a — Eingehender Pilot

- Setup erzeugt Telefonie-Projekt und Agent
- eingehende Gespräche, Nachricht, Zusammenfassung
- Einwilligung, sichere Ablage, Health und Pause

### V1b — Ausgehende Informationsaufträge

- Draft, Vorschau und Human Approval
- Sofort- und Zeitfenster-Ausführung
- ein konfigurierbarer Retry
- strukturierter Bericht und flexible Benachrichtigungen

### V1c — Teilen und Archiv

- Vollzugriff für Mitglieder
- owner-only Mitglieder/Lifecycle
- Eigentumsübertragung
- persönliche und gemeinsame Profile
- verschlüsseltes Vollarchiv, Fristen, Papierkorb und Export

Kein Schritt wird als fertig bezeichnet, bevor der vorherige auf einer echten Leitung
unter realen Neustart-, Besetzt-, Keine-Antwort- und Barge-in-Bedingungen bestanden hat.

## 20. Akzeptanzkriterien

### Projekt und Rechte

- [ ] Ein authentifizierter Benutzer kann nach erfolgreichem SIP-Test ein
  Telefonie-Projekt ohne Systemadmin anlegen.
- [ ] Projekt, Telefon-Agent, Verbindung, Preferences und geschützter Store entstehen
  konsistent oder werden vollständig zurückgerollt.
- [ ] Alle Mitglieder sehen und bedienen alle Telefonie-Funktionen.
- [ ] Nur der Eigentümer ändert Mitglieder, löscht Verbindung/Projekt oder startet eine
  Eigentumsübertragung.
- [ ] Übertragung benötigt Annahme, ist atomar und lässt den alten Eigentümer als
  Vollmitglied zurück.
- [ ] Ein entferntes Mitglied erhält auf alte IDs und Streams 404/Abbruch.

### Telefonie

- [ ] Ein echter FRITZ!Box-Anruf erreicht den dedizierten Telefon-Agenten mit Audio in
  beiden Richtungen.
- [ ] Der Agent ist unterbrechbar und redet nach Barge-in nicht weiter.
- [ ] Eingehende und ausgehende Calls erzeugen normale sichtbare HydraHive-Sessions.
- [ ] Der Agent hält das Informationsmandat ein und macht keine verbindliche Zusage.
- [ ] Ausgehende Calls benötigen einen unveränderten menschlichen Freigabe-Snapshot.
- [ ] Sofort- und Zeitfenster-Aufträge überstehen Backend-/Gateway-Neustarts ohne
  Doppelanruf.
- [ ] Retry folgt Status, Abstand, Zeitfenster und Obergrenze; Default ist genau ein
  weiterer Versuch.

### Daten und Archiv

- [ ] Secrets erscheinen nie in API-Responses, LLM-Kontext, Logs oder Workspace.
- [ ] Audio, Transkript, Zusammenfassung und Ergebnis sind projektverschlüsselt.
- [ ] Standardfrist für nicht archivierte Volltranskripte ist 30 Tage und pro Auftrag
  überschreibbar.
- [ ] Archiv enthält standardmäßig alle vereinbarten Bestandteile.
- [ ] Audio, Transkript und Gesamtvorgang können getrennt beziehungsweise vollständig
  gelöscht werden; Suchdaten und Caches folgen.
- [ ] Restore respektiert Löschung und gibt Daten erst nach Rechte-/Key-Prüfung frei.

### Benachrichtigung und Einstellungen

- [ ] Jedes Mitglied besitzt eigene Defaults und kann Profile privat, geteilt oder als
  Kopie verwenden.
- [ ] Ein freigegebener Auftrag hält seinen Einstellungs-Snapshot trotz Profiländerung.
- [ ] Rückmeldekanäle und Detailgrad sind pro Auftrag per Checkbox konfigurierbar.
- [ ] Volltranskript und Audio werden nie automatisch an externe Kanäle gesendet.

### Sicherheit und Betrieb

- [ ] Rufnummernvalidierung, harte Nummernsperren, Länder-Allowlist, Limits und
  Stop-Schalter sind serverseitig getestet.
- [ ] Prompt-Injection kann weder Nummer, Freigabe, Toolset noch Mandat erweitern.
- [ ] Gateway ist standardmäßig nicht öffentlich erreichbar und authentifiziert alle
  Steuer-/Eventpfade.
- [ ] Health erkennt verlorene SIP-Registrierung und Providerfehler.
- [ ] Latenz und Barge-in werden auf mindestens 20 realen deutschsprachigen Testcalls
  gemessen und dokumentiert.
- [ ] Tel-Agent-/Gateway-Lizenzpflichten sind vor Distribution geklärt und erfüllt.

## 21. Referenzen

- Tel-Agent README: <https://github.com/Dpro-at/Tel-Agent/blob/main/README.md>
- Tel-Agent Voice-Status: <https://github.com/Dpro-at/Tel-Agent/blob/main/agent/README.md>
- Tel-Agent LiveKit-Bindung: <https://github.com/Dpro-at/Tel-Agent/blob/main/agent/session/livekit_room.py>
- Tel-Agent Lizenz: <https://github.com/Dpro-at/Tel-Agent/blob/main/LICENSE>
- HydraHive Projektrollen: `core/src/hydrahive/projects/_members_model.py`
- HydraHive Projektanlage: `core/src/hydrahive/projects/config.py`
- HydraHive strikter Principal: `core/src/hydrahive/api/middleware/auth.py`
- HydraHive Scheduler-Pattern: `core/src/hydrahive/schedules/`
