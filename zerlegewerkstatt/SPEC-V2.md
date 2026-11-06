# Zerlege-Werkstatt V2 – Produktspezifikation

**Stand:** 03.11.2026
**Status:** Freigegeben am 03.11.2026
**Dach-Task:** `ef76dc07`
**Modul-ID:** `zerlegewerkstatt`
**Ergänzende Dokumente:**

- [`SPEC-V2-ARCHITEKTUR.md`](SPEC-V2-ARCHITEKTUR.md) – technische Architektur, MCP, Container und Sicherheit
- [`SPEC-V2-UX.md`](SPEC-V2-UX.md) – transparente Bedienung und aktive Zusammenarbeit
- [`PLAN-V2.md`](PLAN-V2.md) – TDD-Implementierungs- und Abnahmeplan

> Diese Spezifikation ersetzt die fachliche Zielarchitektur aus `SPEC.md`,
> `SPEC-E2.md` und den bisherigen E1/E2-Plänen erst nach ausdrücklicher Freigabe.
> Die alten Dokumente bleiben als Historie des ausgelieferten Moduls 0.4.0 erhalten.

## 1. Problem

Ein Nutzer möchte eine autorisierte Software, App oder Firmware in HydraHive ablegen und deren Aufbau und Verhalten so weit untersuchen, dass eine funktional kompatible eigene Implementierung geplant, erstellt und gegen das beobachtete Originalverhalten geprüft werden kann.

Das bisherige Modul 0.4.0 erfüllt dieses Ziel nicht. Es reduziert REA 6.8.0 auf 18 fest programmierte statische Operationen, drei kleine Agentenwerkzeuge und eine eigene Fallakten-/Berichtsschicht. Vollständige REA-Sitzungen, Extraktion, dynamische Analyse, Provider, Vergleichs- und Rekonstruktionsfunktionen sind dadurch nicht verfügbar.

## 2. Produktziel

Die Zerlege-Werkstatt V2 ist ein transparentes, agentisch gesteuertes Reverse-Engineering-Labor für eigenes oder ausdrücklich autorisiertes Material.

Der Nutzer kann:

1. eine Datei, ein Verzeichnis, eine installierte Anwendung, eine Firmware, einen Mitschnitt oder ein erreichbares autorisiertes Ziel auswählen,
2. das Untersuchungsziel in natürlicher Sprache beschreiben,
3. den vorgeschlagenen Analyseplan prüfen und ändern,
4. alle beteiligten Agenten, REA-Werkzeugaufrufe, Parameter, Ergebnisse, Grenzen und Belege beobachten,
5. die Arbeit pausieren, abbrechen, umpriorisieren oder durch eigene Hinweise und manuelle Analysen ergänzen,
6. extrahierte Dateien und vollständige Evidence untersuchen,
7. offene Fragen und Widersprüche nachvollziehen,
8. ein evidenzbasiertes Rekonstruktionsdossier erzeugen,
9. daraus einen funktionalen Nachbau planen und in einer späteren Ausbaustufe als neues Projekt erzeugen,
10. den Nachbau mit kontrollierten Testfällen gegen das Originalverhalten vergleichen.

## 3. Leitentscheidung

REA wird nicht erneut nachgebaut oder in eine eigene kleine Befehlsliste übersetzt.

REA läuft als echter MCP-Server in einer isolierten Analyseumgebung. Das Modul stellt davor einen **kataloggetriebenen, semantikfreien MCP-Gateway** bereit:

- Der Gateway liest den tatsächlichen `tools/list`-Katalog des installierten REA-Servers.
- Jedes dort veröffentlichte Werkzeug bleibt auffindbar und aufrufbar.
- Eingabeschema, Ergebnis, Evidence, Fehler und Limitations bleiben REA-eigen.
- Es existiert keine fest codierte Liste fachlicher REA-Unterbefehle.
- Neue REA-Werkzeuge werden nach einem geprüften Versionsupdate automatisch im Katalog sichtbar.
- Der Gateway ergänzt nur Projektzugriff, Arbeitsbereich, Berechtigungen, Audit, Ergebnisablage und begrenzte Ansichten großer Resultate.

Der Unterschied zum Modul 0.4.0 ist damit verbindlich:

| Modul 0.4.0 | Modul V2 |
|---|---|
| 18 fest programmierte REA-Aufrufe | vollständiger aktueller REA-MCP-Katalog |
| eigene Analysearten | dynamische Katalog- und Schemaabfrage |
| eigene reduzierte Ergebnisnormalisierung | originale REA-Ergebnisse und Evidence |
| drei Werkzeuge mit funktionaler Teilmenge | wenige generische Gateway-Werkzeuge mit vollständiger Reichweite |
| manuelle Analyseknöpfe | Agentenplan plus manuelle Experteneingriffe |
| Fallbericht als Endprodukt | Evidence, Extraktionsbaum und Rekonstruktionsdossier |

## 4. Produktprinzipien

### 4.1 REA ist Source of Truth

REA definiert verfügbare Werkzeuge, Eingabeschemas, Provider, Sitzungen, Evidence, Coverage und Limitations. Das Modul dupliziert diese Verträge nicht.

### 4.2 Vollständige Verfügbarkeit bedeutet nicht gleichzeitige Werbung

Alle veröffentlichten REA-Werkzeuge müssen erreichbar sein. Sie müssen aber nicht gleichzeitig als 229 Einzelschemas in jeder LLM-Anfrage stehen. Agenten entdecken bei Bedarf relevante Werkzeuge und deren exaktes Schema über den Gateway.

### 4.3 Evidence vor Behauptung

Jede fachliche Aussage wird als eine der folgenden Klassen dargestellt:

- `observed` – direkt beobachtet,
- `derived` – nachvollziehbar aus Evidence abgeleitet,
- `suspected` – begründete Hypothese,
- `unknown` – nicht geklärt,
- `contradicted` – aktive widersprüchliche Evidence.

Eine Vermutung darf nicht als beobachtete Tatsache erscheinen. Unbekannte Punkte werden nicht durch Modellwissen geschlossen.

### 4.4 Transparenz ist Standard, nicht Expertenoption

Der Nutzer sieht standardmäßig:

- den Plan,
- die aktiven und wartenden Agenten,
- aktuelle Schritte,
- verwendete REA-Werkzeuge,
- Ziel und wesentliche Parameter,
- Laufzeit und Status,
- Ergebniszusammenfassung,
- Evidence-IDs,
- Coverage und Limitations,
- offene Fragen,
- erforderliche Freigaben.

Rohschemas, vollständige JSON-Ergebnisse und Diagnosen sind zusätzlich in der Expertenansicht verfügbar.

### 4.5 Nutzer kann jederzeit mitarbeiten

Der Nutzer darf eine Untersuchung:

- nach dem aktuellen sicheren Schritt pausieren,
- einen laufenden Schritt gezielt abbrechen,
- vollständig stoppen,
- fortsetzen,
- einen Planpunkt deaktivieren oder verschieben,
- einen neuen Planpunkt oder eine Frage ergänzen,
- einen Spezialisten zuweisen,
- eine weitere Datei oder einen Mitschnitt hinzufügen,
- eine Hypothese als zu prüfen markieren,
- einen REA-Aufruf manuell vorbereiten und starten,
- eine Berechtigung erteilen oder widerrufen.

### 4.6 Untrusted by default

Dateien, Strings, Pseudocode, Webseiten, Logs, Netzwerkdaten und alle Zielinhalte gelten als nicht vertrauenswürdig. Darin enthaltene Anweisungen dürfen niemals als Agenten- oder Systemanweisung ausgeführt werden.

### 4.7 Autorisierte Nutzung

Eine Untersuchung startet nur nach Bestätigung, dass der Nutzer das Ziel untersuchen darf. Das Modul unterstützt Interoperabilität, Sicherheitsprüfung, Debugging, Forschung und Erhaltung. Es ist kein Freibrief zur Umgehung fremder Zugänge oder zur Beeinträchtigung fremder Systeme.

## 5. Nutzerrollen

### 5.1 Untersuchungsleiter

Der angemeldete Nutzer ist Untersuchungsleiter. Er genehmigt Ziel, Zweck, Plan und erhöhte Berechtigungen und kann jederzeit eingreifen.

### 5.2 Zerlege-Koordinator

Ein sichtbarer HydraHive-Agent:

- formuliert mit dem Nutzer das Untersuchungsziel,
- inventarisiert die Eingaben,
- schlägt einen Plan vor,
- delegiert an sichtbare Spezialisten,
- führt Ergebnisse zusammen,
- verwaltet offene Rekonstruktionspflichten,
- erstellt das Dossier,
- behauptet keinen Abschluss bei offenen Pflichtpunkten.

Der Koordinator erhält keine freie Host-Shell und nicht automatisch alle REA-Schemas.

### 5.3 Spezialisten

Mindestens folgende sichtbare Rollen sind vorgesehen:

- Artefakt- und Paketanalyst,
- Native-Binary-Analyst,
- Managed-Code-Analyst,
- Android-/Flutter-Analyst,
- JavaScript-/Electron-Analyst,
- Firmware-Analyst,
- Browser-/Web-Analyst,
- Runtime-/Frida-/ADB-Analyst,
- Netzwerk-/Protokollanalyst,
- Rekonstruktionsarchitekt.

Ein Spezialist ist eine Arbeitsrolle, keine funktionale Beschränkung des Produkts. Er kann über den Gateway jedes für den freigegebenen Auftrag erforderliche REA-Werkzeug entdecken.

### 5.4 REA

REA ist Analyse- und Evidence-Engine. REA entscheidet nicht selbst über Nutzerberechtigungen oder Produktstatus; diese Verantwortung bleibt bei HydraHive.

## 6. Unterstützte Zielklassen

V2 darf keine künstliche Upload-Positivliste aus wenigen Typen als Produktgrenze verwenden. Die Aufnahme akzeptiert reguläre Dateien und Verzeichnisse innerhalb der konfigurierten Größen- und Sicherheitsgrenzen. Die tatsächliche Verwendbarkeit ergibt sich aus REAs Katalog und den installierten Providern.

Die Oberfläche muss mindestens folgende REA-Zielklassen darstellen können:

- Desktop-Installationen und Anwendungsverzeichnisse,
- PE/EXE/DLL, ELF und Mach-O,
- .NET-Assemblies,
- JavaScript-, Node- und Electron-Anwendungen,
- Android-APKs, Ressourcen und angeschlossene autorisierte Geräte,
- Flutter- und IL2CPP-Metadaten,
- Firmware-Images und extrahierte Dateisysteme,
- Websites und Browserbeobachtungen,
- Prozesse und kontrollierte Laufzeitaufzeichnungen,
- PCAP, HAR, SAZ und andere unterstützte Mitschnitte,
- SQLite, WASM, EVM, BEAM, Python-PYC und PyInstaller,
- Go-, Rust-, Kernel- und GPU-Artefakte,
- Godot-, Unity- und weitere von REA erkannte Paketformate,
- Crashberichte, Modellartefakte und Signalmitschnitte.

Optionale kommerzielle oder externe Provider wie Hopper, IDA, Kuna oder JEB müssen nicht gebündelt werden. Die Oberfläche unterscheidet klar:

- Werkzeug im REA-Katalog vorhanden,
- Provider installiert und bereit,
- Provider nicht installiert,
- Provider benötigt Lizenz oder externen Dienst,
- Ziel auf diesem Host nicht unterstützt.

„Vollständiger REA-Zugriff“ bedeutet, dass das Modul keine REA-Funktion entfernt. Es bedeutet nicht, dass jede optionale Drittanbieter-Lizenz mitgeliefert wird.

## 7. Untersuchungslebenszyklus

Eine Untersuchung besitzt genau einen der folgenden Zustände:

| Zustand | Bedeutung |
|---|---|
| `draft` | Ziel und Eingaben werden zusammengestellt |
| `planning` | Koordinator erstellt oder überarbeitet den Plan |
| `awaiting_plan_approval` | Nutzer muss den initialen oder wesentlich geänderten Plan freigeben |
| `running` | Mindestens ein freigegebener Schritt wird ausgeführt |
| `waiting_user` | Eine Frage, Datei, Entscheidung oder Berechtigung fehlt |
| `paused` | Keine neuen Schritte starten; laufender Schritt darf definiert auslaufen |
| `cancelling` | Abbruch und Cleanup laufen |
| `blocked` | Technischer oder fachlicher Blocker verhindert Fortsetzung |
| `review` | Ergebnisse und Rekonstruktionspflichten werden geprüft |
| `completed_with_gaps` | Auftrag abgeschlossen, aber ausdrücklich benannte Lücken bleiben |
| `completed` | Alle für den gewählten Scope erforderlichen Pflichten sind evidenzbasiert geschlossen |
| `failed` | Untersuchung endete technisch ohne verwertbaren Abschluss |
| `archived` | Arbeitscontainer entfernt; Evidence und Dossier bleiben lesbar |

`completed` darf nicht allein durch eine Agentenantwort gesetzt werden. Es erfordert einen maschinenlesbaren Rekonstruktionsstatus ohne offene erforderliche Pflicht.

## 8. Standardworkflow

### 8.1 Aufnahme

Der Nutzer:

1. wählt ein HydraHive-Projekt,
2. legt eine neue Untersuchung an,
3. beschreibt Ziel und gewünschte Kompatibilität,
4. bestätigt Berechtigung und Zweck,
5. fügt Dateien, Verzeichnisse oder vorhandene Projektartefakte hinzu.

Jede Eingabe erhält mindestens:

- unveränderliche Artefakt-ID,
- Originalname,
- Größe,
- SHA-256,
- Herkunft,
- Aufnahmezeitpunkt,
- Besitzer/Projekt,
- erkannte Grundklassifikation,
- Containerpfad und Hostspeicherreferenz.

### 8.2 Discovery

Der Koordinator verwendet nur zielunabhängige und statische Discovery-Funktionen, um:

- Zieltypen zu bestimmen,
- REA- und Providerfähigkeiten zu prüfen,
- eingebettete Komponenten zu erkennen,
- einen ersten Plan zu erstellen.

Discovery führt das Ziel nicht aus und öffnet kein Netzwerk.

### 8.3 Planfreigabe

Der Plan enthält:

- Fragestellungen,
- Schritte und Abhängigkeiten,
- zuständigen Agenten,
- erwartete REA-Werkzeuge oder Werkzeugkategorien,
- benötigte Berechtigungsstufe,
- erwartete Ausgaben,
- Abbruch- und Erfolgskriterien.

Der Nutzer kann den Plan ändern und freigeben. Neue Schritte mit höherer Wirkung benötigen eine erneute passende Freigabe; reine statische Folgeproben innerhalb des freigegebenen Scopes nicht.

### 8.4 Ausführung

Agenten arbeiten den Plan ab. Jeder REA-Aufruf wird vor dem Start als sichtbares Ereignis erfasst. Große Ergebnisse werden vollständig gespeichert; dem Modell wird nur eine begrenzte Ansicht mit stabiler Ergebnisreferenz gegeben.

### 8.5 Iteration

Ein Befund kann neue Schritte erzeugen, etwa:

- extrahiertes ELF nativ untersuchen,
- eine APK-Methode verfolgen,
- einen Netzwerkendpunkt mit einem Mitschnitt abgleichen,
- zwei Versionen vergleichen,
- eine unbekannte Region erneut untersuchen,
- einen kontrollierten Lauf vorschlagen.

Der Nutzer sieht diese Änderung und kann sie bearbeiten.

### 8.6 Review und Rekonstruktionsabschluss

Der Koordinator erzeugt einen Pflichtenkatalog und prüft mindestens:

- Komponenten und Zuständigkeiten,
- öffentliche und interne Schnittstellen,
- Datenmodelle und Dateiformate,
- relevante Funktionsabläufe,
- Zustandsmaschinen,
- Netzwerk- und Geräteprotokolle,
- Konfiguration und Persistenz,
- Start, Update und Fehlerverhalten,
- beobachtete Laufzeitvarianten,
- verbleibende Unbekannte und Widersprüche,
- Nachweisbarkeit jeder für den Nachbau wesentlichen Behauptung.

## 9. Rekonstruktionsdossier

Das Dossier ist versioniert und enthält:

1. **Scope und Ziel** – Was soll funktional nachgebaut werden?
2. **Artefaktinventar** – Originale, extrahierte Komponenten, Hashes und Herkunft.
3. **Architektur** – Komponenten, Prozesse, Daten- und Kontrollflüsse.
4. **Funktionskatalog** – relevante Funktionen, Klassen, Pseudocode und Beziehungen.
5. **Protokolle und APIs** – Nachrichten, Felder, Reihenfolge, Fehler und Beispiele.
6. **Datenmodelle** – Dateien, Datenbanken, Konfigurationen und Zustände.
7. **UI und Verhalten** – sichtbare Abläufe, Eingaben und Ausgaben.
8. **Boot/Installation/Update** – soweit für den Scope relevant und beobachtet.
9. **Evidence-Matrix** – jede Behauptung mit Evidence-Referenzen.
10. **Unbekannte und Widersprüche** – Auswirkungen und empfohlene nächste Proben.
11. **Clean-Room-Nachbauplan** – Komponenten, Schnittstellen, Reihenfolge und Tests.
12. **Kompatibilitätstests** – Testvektoren und erwartetes beobachtetes Verhalten.
13. **Rekonstruktionsstatus** – `ready`, `partial`, `unknown` oder `blocked`.

Der Dossiertext ist eine Ansicht. Die vollständigen REA-Evidence-Bundles bleiben die primäre Quelle.

## 10. Nachbau und Vergleich

Der Zielzustand der V2-Produktfamilie umfasst einen optionalen Nachbau-Arbeitsbereich:

- neues, getrenntes Quellprojekt,
- keine Änderung des Originalartefakts,
- generierter Grundaufbau aus dem freigegebenen Dossier,
- für jede Komponente verknüpfte Rekonstruktionspflichten,
- Tests gegen dokumentierte Protokolle und Dateiformate,
- kontrollierte Differentialtests Original gegen Kandidat,
- keine Gleichheitsbehauptung bei fehlender Beobachtung.

Die Implementierung dieses Arbeitsbereichs erfolgt nach der belastbaren Analyse-, Evidence- und Dossier-Pipeline. Sie ist im Plan als eigene Etappe enthalten und darf nicht die vorherigen Abnahmekriterien ersetzen.

## 11. Transparenz und Kontrolle

Drei Arbeitsmodi sind verbindlich:

### 11.1 Geführt – Standard

- Initialer Plan muss freigegeben werden.
- Statische, read-only Folgeanalysen innerhalb des Plans laufen automatisch.
- Netzwerk, Zielausführung, Browserinteraktion, ADB, Frida, Gerätezugriff und externe Effekte benötigen gesonderte Freigabe.
- Nutzer kann jederzeit pausieren oder eingreifen.

### 11.2 Manuell

- Jeder Analyseaufruf benötigt eine Freigabe.
- Geeignet für Lernen, besonders sensible Ziele und genaue Reproduktion.

### 11.3 Autopilot

- Statische und bereits pauschal freigegebene Schritte laufen ohne Einzelbestätigung.
- Wirkungsvolle Kategorien behalten zwingende Freigaben.
- Autopilot kann Sicherheitsgrenzen nicht deaktivieren.

Die UI-Spezifikation definiert die konkreten Anzeigen und Aktionen.

## 12. Daten- und Evidence-Vertrag

Das Modul speichert keine fachlich reduzierte Kopie als alleinige Wahrheit. Es speichert:

- vollständige originale REA-Ergebnisse oder exportierte Evidence-Bundles,
- kryptografischen Digest,
- REA-Version und Katalogdigest,
- Provider und Providerprofil,
- exakten Werkzeugnamen,
- redigierte Argumente,
- Start, Ende und Status,
- Nutzer-/Agenten-/Sessionbezug,
- Coverage, Limitations und Fehler,
- kleine abgeleitete UI-Indizes und Ansichten.

UI-Indizes müssen jederzeit aus der vollständigen Quelle neu erzeugbar sein. Eine abgeschnittene LLM-Ansicht darf nie eine vollständige Evidence-Datei überschreiben.

## 13. Sicherheits- und Freigabeklassen

| Klasse | Beispiel | Standard |
|---|---|---|
| A – statisch/read-only | Katalog, Hash, Header, Decompile, Xrefs | nach Planfreigabe automatisch |
| B – Arbeitsbereich schreibend | Extraktion, Evidence-Export, Snapshot | nach Planfreigabe im isolierten Arbeitsbereich |
| C – Zielausführung | Prozesslauf, Electron-/JS-Runtime | explizite zeitlich gebundene Freigabe |
| D – Netzwerk/offene Welt | Website, Browsernetz, externe API | explizite Ziel- und Zeitfreigabe |
| E – Gerät/Instrumentierung | ADB, Frida, USB, Gerätetransfer | explizite Geräte- und Operationsfreigabe |
| F – destruktive/externe Änderung | Schreiben auf Gerät, Installation, Flashen | nicht Bestandteil des Standardanalyseflusses; separate ausdrückliche Freigabe und eigene spätere Spezifikation |

Details stehen in der Architekturspezifikation.

## 14. Migration von Modul 0.4.0

- Version 0.4.0 wird bis zur V2-Migration funktional eingefroren.
- Alte Fälle, Artefakte, Jobs und Berichte bleiben lesbar.
- Es erfolgt keine automatische Löschung oder Neuinterpretation alter Evidence.
- Ein Nutzer kann einen alten Fall in eine neue V2-Untersuchung übernehmen.
- Dabei werden Originalartefakte mit neu berechnetem Hash referenziert oder kopiert.
- Alte normalisierte Berichte werden als Legacy-Quelle markiert, nicht als REA-Evidence umetikettiert.
- Die 18 statischen Adapter werden nach erfolgreicher V2-Abnahme nicht weiter als primärer Weg angeboten.
- Ein Rollback auf 0.4.0 darf V2-Daten nicht zerstören; 0.4.0 kann sie lediglich nicht bearbeiten.

## 15. Nicht-Ziele und ehrliche Grenzen

V2 verspricht nicht:

- den ursprünglichen Quellcode exakt zurückzugewinnen,
- unbekannte Verschlüsselung ohne Schlüssel zu brechen,
- Secure Boot oder Hardware-Sicherheitsmodule zu umgehen,
- nicht beobachtete Cloudserver-Logik zu rekonstruieren,
- jede proprietäre Architektur automatisch zu emulieren,
- jede optionale kommerzielle Analyseengine mitzuliefern,
- einen Nachbau ohne fachliche Prüfung als identisch zu erklären,
- Schutzmaßnahmen fremder Systeme zu umgehen.

Das Produktziel ist eine möglichst vollständige, nachvollziehbare und evidenzbasierte funktionale Rekonstruktion innerhalb des autorisierten Scopes.

## 16. Produktweite Akzeptanzkriterien

### 16.1 Katalogparität

- Der Installer pinnt REA-Version und Paketdigest.
- Der reale `tools/list`-Katalog wird mit Toolanzahl und Digest gespeichert.
- Jedes dort gelistete Tool ist über Katalogsuche und Schemaansicht auffindbar.
- Ein Tool wird nicht deshalb unaufrufbar, weil es nicht in HydraHive fest codiert ist.
- Nicht verfügbare Provider liefern ihren echten REA-Status und keine künstliche Modulfehlermeldung.

### 16.2 Native Referenzuntersuchung

Eine öffentliche, zulässige native Testanwendung wird:

- aufgenommen,
- inventarisiert,
- in einer REA-Sitzung geöffnet,
- nach Funktionen durchsucht,
- dekompiliert,
- über Xrefs/Calls verfolgt,
- als Evidence exportiert,
- in ein Rekonstruktionsdossier überführt.

Der Nutzer pausiert währenddessen, ergänzt eine Frage und ändert einen noch nicht gestarteten Planschritt.

### 16.3 Firmware-Referenzuntersuchung

Eine öffentliche Firmware wird:

- nach Regionen untersucht,
- mit REA/Unblob extrahiert,
- als veröffentlichter Dateibaum angezeigt,
- rekursiv klassifiziert,
- mindestens mit einem extrahierten nativen Kind weiter untersucht,
- mit Extraction Gaps und Limitations dokumentiert.

Kein Bericht behauptet vollständige Firmware-Rekonstruktion, wenn REA `partial` oder Gaps meldet.

### 16.4 App-Referenzuntersuchung

Mindestens eine APK oder Electron-Anwendung wird mit ihren nativen und verwalteten/JavaScript-Anteilen untersucht. Der Agent verfolgt eine konkrete Funktion bis zu Evidence und dokumentiert unbekannte Laufzeitanteile.

### 16.5 Dynamische Referenzuntersuchung

Eine harmlose Testanwendung wird ausschließlich nach gesonderter Freigabe in einer wegwerfbaren Laufzeitumgebung ausgeführt. Prozess-, Datei- oder Netzwerkbeobachtungen werden exportiert; die Laufzeitumgebung wird anschließend nachweislich entfernt.

### 16.6 Transparenz

Für jeden Agenten- und REA-Schritt sind sichtbar:

- Initiator,
- Ziel,
- Werkzeug,
- wesentliche Parameter,
- Status,
- Dauer,
- Ergebnisreferenz,
- Coverage und Limitations,
- Freigabeklasse.

### 16.7 Eingriff

Der Nutzer kann nachweislich:

- pausieren,
- den aktuellen Schritt abbrechen,
- einen Planpunkt ändern,
- eine Zusatzdatei aufnehmen,
- eine Frage an einen bestimmten Spezialisten richten,
- eine Freigabe verweigern,
- die Arbeit danach konsistent fortsetzen.

### 16.8 Sicherheit

- Kein Zielinhalt erreicht den Agenten als vertrauenswürdige Instruktion.
- Keine Analyseumgebung erhält Host-Secrets oder Incus-/Docker-Sockets.
- Statische Untersuchungen haben kein Netz.
- Dynamische und gerätebezogene Fähigkeiten sind an explizite Grants gebunden.
- Nach Abbruch bleiben keine unbestätigten Zielprozesse zurück.
- Unvollständiges Cleanup quarantänisiert die Umgebung und blockiert neue Arbeit.

### 16.9 Große Ergebnisse

Ein Ergebnis oberhalb des LLM-Ausgabelimits bleibt vollständig gespeichert und authentifiziert. Agent und Nutzer können es über Summary, Paging oder gezielte Ansichten lesen. Es wird nicht als abgeschnittenes JSON weiterverarbeitet.

### 16.10 Abschlusswahrheit

Eine Untersuchung kann nur `completed` heißen, wenn der gewählte Scope einen geschlossenen Pflichtenkatalog besitzt. Andernfalls lautet der Status `completed_with_gaps`, `unknown` oder `blocked`, und die Lücken sind sichtbar.

## 17. Freigabeentscheidung

Mit Freigabe dieser Spezifikation werden folgende Entscheidungen verbindlich:

1. V2 ersetzt den festen 18-Befehle-Adapter durch einen vollständigen kataloggetriebenen REA-MCP-Zugang.
2. REA-Evidence bleibt primäre Wahrheit.
3. Agenten und REA-Aktionen sind standardmäßig sichtbar.
4. Der Nutzer kann planen, pausieren, ändern, freigeben und manuell analysieren.
5. Zielausführung und offene Außenwirkung werden getrennt und explizit autorisiert.
6. Die alte Version wird migriert, nicht blind weitergepatcht und nicht sofort gelöscht.
7. Implementierung beginnt erst nach Freigabe aller vier V2-Dokumente.
