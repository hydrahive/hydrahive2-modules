# OpenTor — HydraHive-Modul-Spezifikation

## Ziel

OpenTor wird als kontrolliertes, read-only Tor-OSINT-Modul in HydraHive integriert. HydraHive bleibt der Orchestrator und entscheidet über Recherche, Interpretation und Darstellung; OpenTor liefert ausschließlich Tor-Transport, gezielte Suche, Quellenabruf und mechanische IOC-Extraktion.

Die erste Version ist **kein allgemeiner Dark-Web-Browser**, führt keine freien Shell-Kommandos aus und lädt keine Dateien oder Zugangsdaten herunter.

## Herkunft und Lizenz

Technische Basis ist [vichhka-git/OpenTor](https://github.com/vichhka-git/OpenTor), MIT-lizenziert. Der Upstream wird auf einen festen Commit gepinnt und vor Integration auditiert. Das Engine-Verzeichnis enthält laut Upstream-Dokumentation Bestandteile aus Robin; die MIT-Lizenz- und NOTICE-Kompatibilität muss vor Veröffentlichung geprüft und dokumentiert werden.

Das HydraHive-Modul selbst folgt der Modul-Lizenz und den Konventionen des `hydrahive2-modules`-Repositories.

## Produktgrenzen

### In V1 enthalten

- Admin-gesteuertes Aktivieren/Deaktivieren
- Tor-Verbindungsstatus ohne Anzeige sensibler Netzwerkdetails
- gezielte Suche über konfigurierte OpenTor-Engines
- Abruf einer explizit angegebenen `http(s)`-URL über Tor
- Onion-Redirect-Schutz
- begrenzte Text- und Linkextraktion
- IOC-Extraktion aus bereits erhaltenem Text
- strukturierte Evidenz mit Quelle, Zeitpunkt, Status und Unsicherheitslabel
- Ausgabe als JSON und optional STIX/MISP-Artefakt, sofern der Upstream-Exporter sicher isoliert ist
- Hydra-native Skills für defensive OSINT- und Threat-Intelligence-Aufgaben

### Explizit nicht in V1

- kein freies `shell_exec` oder LLM-generiertes Python
- kein interaktiver Upstream-Setup-Wizard
- keine Paketinstallation oder `sudo` aus HydraHive heraus
- kein TorPool und keine parallelen Identitäten
- kein automatisches Crawling/Spidering
- keine Datei-, Archiv- oder Binärdownloads
- kein Credential-Testing, Login, Kauf, Kommunikation oder Marktplatz-Aktion
- keine Sammlung oder Ausgabe vollständiger Zugangsdaten/PII
- keine unbeaufsichtigte Überwachung oder Scheduling-Anbindung
- keine automatische Weitergabe von Onion-Inhalten an weitere Tools ohne Sanitization

## Architektur

```text
HydraHive Agent / Buddy
        │  Tool-Aufruf mit Auth + Policy
        ▼
OpenTor-Modul (Backend, dünner Adapter)
        │  validierte JSON-Nachricht
        ▼
OpenTor-Worker (dedizierte venv oder separater Dienst)
        │
        ├── torcore: SOCKS5-Transport
        ├── engines/osint: Search + Text/IOC-Extraktion
        └── SQLite: nur begrenzter Cache und Evidenz-Metadaten
        │
        ▼
Sanitizer / Evidence Mapper
        │
        ▼
ToolResult mit untrusted-content Markierung
```

Der Worker darf nur mit einem dedizierten Datenverzeichnis arbeiten. Alle Pfade kommen aus der HydraHive-Konfiguration bzw. dem Worker-Launcher, niemals aus User-Input. Ein direkter Import des Upstream-Codes in den Core-Prozess ist für V1 nicht zulässig, falls damit Tor-Prozesse, globale Umgebungsvariablen oder unkontrollierte Dateischreibzugriffe verbunden sind.

Die konkrete Worker-Technik darf für das MVP zunächst ein kontrollierter Python-Adapter mit gemockter Transportgrenze sein. Die öffentliche Tool-Schnittstelle darf dabei nicht vom späteren Worker-Transport abhängen.

## Modulvertrag

```text
opentor/
├── manifest.json
├── SPEC.md
├── README.md
├── backend/
│   ├── __init__.py
│   ├── models.py
│   ├── policy.py
│   ├── service.py
│   ├── tools_read.py
│   ├── tools_search.py
│   └── routes.py
├── frontend/
│   ├── index.tsx
│   └── OpenTorPage.tsx
├── migrations/
└── tests/
```

Das Manifest deklariert `has_service: true`, sobald der Worker-Lifecycle als eigener Prozess umgesetzt ist. Bis dahin darf ein reiner Adapter `has_service: false` verwenden, muss aber den Read-only-Modus erzwingen.

Empfohlene Manifest-Werte:

```json
{
  "id": "opentor",
  "name": "OpenTor OSINT",
  "version": "0.1.0",
  "description": "Kontrollierte Tor-basierte OSINT- und Threat-Intelligence-Recherche.",
  "icon": "ShieldSearch",
  "nav_group": "working",
  "permissions": ["opentor.read"],
  "default_agent_tools": false,
  "has_service": true,
  "min_core_version": "2.0.0"
}
```

`default_agent_tools` bleibt zunächst `false`; ein Administrator aktiviert das Modul und weist es gezielt Agenten/Benutzern zu.

## Tool-API

Alle Tools verlangen einen gültigen `ToolContext`-Principal und prüfen vor jeder externen Aktion die Modul-Policy. Eingaben werden über JSON-Schemas und Pydantic-Modelle validiert. Fehlermeldungen dürfen keine Proxy-, Cookie-, ControlPort- oder Dateipfaddetails enthalten.

### `opentor_status`

Zeigt nur:

- `enabled`
- `tor_reachable`
- `worker_ready`
- `last_check_at`
- anonymisierte Engine-Zusammenfassung

Kein Exit-IP- oder ControlPort-Leak in Agentenantworten.

### `opentor_search`

Parameter:

```json
{
  "query": "string, 2..200 Zeichen",
  "mode": "threat_intel | ransomware | corporate",
  "engines": ["optionale Namen aus Allowlist"],
  "limit": "1..20"
}
```

Regeln:

- nur Such-Engines aus festem Katalog
- keine frei übergebene Engine-URL
- maximal 20 Treffer
- Query wird nicht als Shell-Argument ausgeführt
- Suchergebnis wird als untrusted content markiert
- automatische Blacklist des Upstreams bleibt aktiv und wird nicht abschaltbar

### `opentor_fetch`

Parameter:

```json
{
  "url": "http(s)-URL",
  "max_chars": "500..8000"
}
```

Regeln:

- nur `http` und `https`
- Hostname muss ein gültiger Host sein
- `.onion`-Redirect auf Clearnet wird blockiert
- keine `file:`, `ftp:`, `gopher:`, localhost-, Loopback-, RFC1918- oder Link-Local-Ziele
- keine Benutzerinfo im URL-Teil (`user:pass@host`)
- kein Download von Binärdaten oder Archiven
- Antwortgröße und Linkanzahl begrenzen
- keine beliebigen Header/Cookies aus User-Input

### `opentor_extract_iocs`

Verarbeitet nur bereits vorliegende, begrenzte Textdaten. Es wird kein Netzwerkzugriff ausgelöst. Ausgabe wird nach IOC-Typ gruppiert und standardmäßig um offensichtliche PII-Felder maskiert.

### `opentor_export_intelligence`

Exportiert ausschließlich gespeicherte, bereinigte Evidenz. Zulässige Formate sind zunächst `json`; STIX/MISP wird erst aktiviert, wenn der Exporter isoliert getestet und die Redaktionsregeln abgedeckt sind.

## Evidenz- und Agentenregeln

Jede Rechercheantwort muss enthalten:

- exakte Quellen-URL
- beobachteten Zeitpunkt
- verwendetes Tool
- HTTP-/Transportstatus, soweit vorhanden
- Label: `Observed`, `Inferred`, `Uncertain` oder `AI Analysis`
- Hinweis, dass Onion-Inhalte untrusted input sind

Der Skill darf niemals Anweisungen, Links oder Code aus einer abgerufenen Seite als HydraHive-Auftrag interpretieren. Gefundene Inhalte werden als Daten zitiert, nicht als Instruktionen ausgeführt.

## Datenhaltung

Gespeichert werden nur:

- Besitzer/Projekt-Referenz
- Suchparameter ohne Secrets
- URL und URL-Hash
- Status, Titel und begrenzter bereinigter Text
- IOCs und Evidenzlabels
- Zeitstempel
- Fehlerklasse ohne interne Details

Nicht gespeichert werden standardmäßig:

- Tor-Control-Cookies
- Proxy-Passwörter
- vollständige Credentials
- heruntergeladene Dateien
- unlimitierte HTML-Rohdaten

Aufbewahrung und Löschung müssen über die Modul-Policy konfigurierbar sein. Daten sind pro Benutzer/Projekt zu trennen; ein Benutzer darf keine Recherche eines anderen Benutzers lesen.

## Admin- und UI-Anforderungen

### Admin

- Modul aktivieren/deaktivieren
- read-only Policy anzeigen
- Tor-/Worker-Status anzeigen
- erlaubte Modi und Engine-Allowlist verwalten
- maximale Antwortgröße und Aufbewahrung einstellen
- Warnhinweis zu Recht, Datenschutz und untrusted Onion-Inhalten
- keine Eingabemaske für beliebige Worker-Kommandos

### Modulansicht

- Statuskarte
- Suchformular mit Modus und Limit
- explizites Fetch-Formular
- Ergebnisliste mit Evidenzlabels
- IOC-Ansicht mit Maskierung
- Export nur bereinigter Ergebnisse
- sichtbarer Hinweis: „Nur autorisierte defensive OSINT-Recherche“

## Sicherheitsanforderungen

- Authentifizierung und Modul-Permission vor jeder Route und jedem Tool
- Rate-Limit pro Benutzer/Projekt für Search und Fetch
- SSRF- und Redirect-Schutz wie oben beschrieben
- untrusted-content Markierung als feste Tool-Metadaten
- kein Shell-Aufruf mit User-Input
- keine Secrets in Logs oder ToolResult
- parametrisierte SQL-Abfragen
- Dateipfade nur aus Serverkonfiguration
- externe Tor-Verbindung standardmäßig aus, bis Admin sie aktiviert
- Security-Tests für URL-Validierung, Redirects, Auth, Mandantentrennung, Limits und PII-Redaktion

## Implementierungsreihenfolge

1. Spec und Manifest-Skelett
2. Policy-/URL-/Evidenzmodelle mit Unit-Tests
3. kontrollierter Adapter mit Fake-Transport und Tool-Registrierung
4. Migration und autorisierte Routes
5. Frontend-Status, Suche, Fetch und Admin-Hinweise
6. Hydra-native Skills
7. Security-/Integrationstests ohne echte Tor-Verbindung
8. optionaler echter Worker-Adapter hinter Feature Flag
9. Modul-Review, Versions-Bump, CI und lokales Deployment

## Akzeptanzkriterien

- [ ] Modul wird vom Hub mit gültigem Manifest erkannt.
- [ ] Modul ist standardmäßig deaktiviert und nicht als Default-Agent-Tool freigeschaltet.
- [ ] Kein Tool akzeptiert freie Shell-Befehle oder beliebige Engine-URLs.
- [ ] URL-Validierung blockiert gefährliche Schemes, lokale Netze, Credentials und Onion-Clearnet-Redirects.
- [ ] Search/Fetch erzwingen Auth, Permission, Rate-Limit und Größenlimits.
- [ ] Onion-Inhalte werden als untrusted data markiert und nicht als Instruktionen ausgeführt.
- [ ] Daten sind pro Benutzer/Projekt getrennt und enthalten keine Tor-Secrets.
- [ ] Unit-, Tool-Registrierungs-, Route- und Security-Tests laufen ohne Internet/Tor.
- [ ] Frontend-Build, Lint und Modul-/Spec-Guards sind grün.
- [ ] OpenTor-Upstream-Commit und Lizenzhinweise sind dokumentiert.
- [ ] Kein automatisches Crawling, Scheduling, Datei-Download oder Credential-Testing in V1.

## Nicht-Ziele

- Anonymitäts- oder Rechtsgarantie durch Tor
- Ersatz für professionelle Incident-Response- oder Rechtsberatung
- Vollständige Dark-Web-Archivierung
- autonomes Handeln gegen gefundene Personen, Systeme oder Organisationen
- Umgehung von Zugriffskontrollen, Bezahlschranken oder Sicherheitsmechanismen
