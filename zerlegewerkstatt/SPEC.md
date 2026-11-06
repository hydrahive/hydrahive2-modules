# Zerlege-Werkstatt – Spezifikation E1

> **Historischer Stand (Modul 0.4.0).** Dieses Dokument beschreibt die ausgelieferte E1-Architektur und bleibt als Nachweis erhalten. Es ist nicht mehr die Zielarchitektur. Verbindlich für V2 ist [`SPEC-V2.md`](SPEC-V2.md).

**Stand:** 02.11.2026  
**Status:** E1 umgesetzt; E2-Ausbau in Arbeit (0.2.0)
**Task:** `ba8d88b3`  
**Modul-ID:** `zerlegewerkstatt`  
**Nachweis:** 116 Backendtests, 7 Frontendtests, `tsc`, Ruff und Isolationstest grün; E2E am echten Container mit Windows-OpenSSH-PE und WLED-APK

## 1. Problem

Für viele Smart-Home-Geräte existieren nur Hersteller-Apps für Windows oder Android. Ohne eine nachvollziehbare statische Untersuchung bleiben lokale Protokolle, Geräteerkennung und Firmware-Aufbau unbekannt; HydraHive kann deshalb keine eigene lokale Schnittstelle anbieten und bleibt von Hersteller-Clouds abhängig.

Die Untersuchung soll rechtmäßige Interoperabilität mit eigenen oder ausdrücklich freigegebenen Geräten ermöglichen. Sie darf keine hochgeladenen Programme auf dem HydraHive-Host ausführen und keine Schutzmaßnahmen, Lizenzprüfungen, Authentifizierung oder fremde Dienste umgehen.

## 2. Ziel E1

HydraHive bekommt eine „Zerlege-Werkstatt“, in der berechtigte Nutzer:

1. eine Fallakte anlegen,
2. EXE/DLL, APK, Firmware oder aufgezeichneten Netzwerkverkehr hochladen,
3. eine rein statische, isolierte Untersuchung starten,
4. Fortschritt, Befunde, Belege und offene Fragen sehen,
5. die Dateien optional über die bestehende Projekt-Samba-Freigabe ablegen können.

Ein eigener Incus-Container enthält REA, Ghidra, JDK und JADX. Der Kern übergibt Dateien und startet ausschließlich eine feste Positivliste von Analysebefehlen. Das Sprachmodell sieht nur eine kleine HydraHive-Werkzeugschnittstelle, nie den kompletten REA-MCP-Katalog.

## 3. Nicht-Ziele E1

- Keine Ausführung hochgeladener EXE/APK/Firmware.
- Keine Windows-VM, kein Android-Emulator und kein automatisches Flashen.
- Kein Andocken an fremde Geräte oder Prozesse.
- Kein TLS-Pinning-, DRM-, Lizenz-, Authentifizierungs- oder Cloud-Schutz-Bypass.
- Kein automatisches Erzeugen oder Veröffentlichen einer fertigen Home-Assistant-Integration.
- Kein allgemeiner Agentenzugriff auf Shell oder REA-MCP im Analysecontainer.
- Noch keine Binwalk-3.1-/Unblob-Firmwareextraktion; E1 nimmt die portable REA-Artefaktanalyse und sichere String-/Hash-Inventur. Ausbau folgt in E2.

## 4. Berechtigung und zulässiger Zweck

Das Modul ist standardmäßig `admin_only`. Jede Fallakte speichert:

- Projekt-ID und Ersteller,
- Ziel/Gerät und kurze Fragestellung,
- Zweck: `interoperability`, `security_audit`, `debugging`, `preservation` oder `other_authorized`,
- Bestätigung, dass der Nutzer das Material untersuchen darf,
- optional Herkunft/Hersteller und Notiz zur Berechtigung.

Ohne Bestätigung kann keine Analyse starten. Die Bestätigung ist keine Rechtsberatung und ersetzt keine Prüfung durch den Nutzer. Fälle, deren Ziel ausdrücklich Schutzumgehung, Zugang zu fremden Systemen, Cheats oder Schadsoftwareeinsatz ist, werden abgelehnt.

## 5. Fallakte und Dateibaum

Persistente Falldaten liegen auf dem Host unter:

`<data_dir>/zerlegewerkstatt/cases/<case-id>/`

Bewusst nicht unterhalb von `data_dir/modules/`: dort liegen die Moduldateien,
die ein Update überschreibt. So bleiben die Falldaten beim Update erhalten.

```text
case.json                 nur atomar geschriebene Metadaten
input/                    unveränderte Originale, nach Aufnahme nur lesbar
work/                     temporäre Arbeitsdateien
results/                  normalisierte kleine JSON-Ergebnisse
reports/                  Markdown-Bericht und Belegverzeichnis
logs/                     begrenzte, bereinigte Diagnosen
```

Dateinamen des Nutzers erscheinen nur in Metadaten. Auf Platte heißen Eingaben `<artifact-id>.<ext>`. IDs sind serverseitig erzeugt. `case-id` und `artifact-id` folgen festen regulären Ausdrücken; fremde Pfade sind nie API-Eingabe.

## 6. Upload und Samba

### 6.1 Web-Upload

- Höchstens 5 Dateien pro Anfrage.
- Höchstens 512 MiB je Datei und 2 GiB je Fall in E1.
- Streaming in eine `.part`-Datei; Größe und SHA-256 werden während des Schreibens berechnet.
- Leere Dateien, unbekannte Typen, Doppeldateien mit identischem Hash und überschrittene Grenzen werden abgelehnt.
- Anerkannte Typen werden anhand von Magic Bytes und Struktur erkannt, nicht nur anhand der Endung: PE/CLI, APK/ZIP, PCAP/PCAPNG, ELF, ESP/rohe Firmware als `firmware`.
- Atomare Veröffentlichung per `os.replace`; `.part` wird bei jedem Fehler entfernt.
- Originale werden nie an Browser zurückgesendet; Berichte dürfen keine Binärdaten enthalten.

### 6.2 Samba

E1 verwendet die bereits vorhandene **Projekt-Samba-Freigabe**. Im Projekt-Workspace wird ein Modulordner angelegt:

`zerlegewerkstatt/eingang/<case-id>/`

Der Nutzer kopiert dort Dateien hinein und klickt im Fall „Eingang prüfen“. Die Aufnahme:

1. öffnet keine Symlinks und folgt ihnen nicht,
2. nimmt nur reguläre Dateien unmittelbar in diesem Ordner an,
3. prüft Anzahl, Größe, Typ und Hash wie beim Web-Upload,
4. kopiert in eine private `.part`-Datei im Modul-Datenordner,
5. prüft vor und nach dem Kopieren Größe, Geräte-/Inode-Identität und Änderungszeit,
6. veröffentlicht atomar; die Eingangsdatei bleibt unverändert.

Die bestehende gemeinsame Samba-Anmeldung bleibt eine bekannte Grenze. Das Modul zeigt sie offen an; eine eigene per-Nutzer-Samba-Authentifizierung gehört nicht zu E1.

## 7. Container und Sicherheitsgrenze

Containername: `hh-zerlegewerkstatt`.

- Ubuntu 24.04, 6 vCPU, 12 GiB RAM, maximal 2 parallele Analysen (in E1 tatsächlich 1).
- Eigener unprivilegierter Benutzer `rea`, kein Host-Home, keine Host-Secrets.
- Kein Zugriff auf Docker-/Incus-Socket, `/dev`, GPU, USB oder Host-Projektordner.
- Netzwerk standardmäßig während der Analyse deaktiviert. Installations-/Updatephase darf ausgehend laden; Produktanalyse nicht.
- Dateien werden per `incus file push` in einen frischen Arbeitsordner kopiert; nur Ergebnisdateien werden zurückgeholt.
- Feste Befehls-Positivliste, Argumentliste ohne Shell:
  - `inspect-artifact`
  - `inspect-android-package`
  - `inspect-managed-artifact`
  - `inspect-managed-members`
  - `analyze --provider ghidra`
  - `inspect-pcap`/passive Capture-Inventur, soweit in der gewählten REA-Version vorhanden
- Keine freie REA-Unterbefehlswahl über API oder Agentenwerkzeug.
- Zeitlimit je Operation, begrenzte Ausgabe, Prozessgruppe bei Abbruch beenden, Arbeitsordner anschließend löschen.
- Das E0 hat gezeigt, dass REA im Incus-Profil `signal` und `ptrace` zum Überwachen seiner **eigenen** Hilfsprozesse braucht. Die Produktinstallation ergänzt nur diese Regeln für den einen Container. Kein `lxc.apparmor.profile=unconfined`, kein privileged Container.
- Analyseergebnisse gelten als **nicht vertrauenswürdiger Inhalt**. Texte aus Programmen/Firmware dürfen keine Handlungsanweisungen an Agenten auslösen. Ein Hinweis im Systemprompt und Toolresult markiert `untrusted_target_content=true`.

## 8. REA-Version und Lieferkette

- E1 pinnt jede Version und SHA-256: Node, REA, Ghidra, JADX-Bridge.
- Keine Installation über `latest`.
- Der Installer bricht bei abweichender Prüfsumme ab.
- REA npm 6.8.0 unterstützt den dokumentierten Werkzeugfamilien-Filter noch nicht zuverlässig. Deshalb nutzt E1 die CLI hinter einem kleinen HydraHive-Adapter, nicht den vollständigen MCP-Server.
- Die Zerlege-Werkstatt bleibt bei nativen HydraHive-Werkzeugen und festen CLI-Adaptern. Ein zusätzlicher REA-MCP-Server ist ausdrücklich kein Ziel.

## 9. Backend

### 9.1 Datenhaltung

SQLite-Migration:

- `module_zerlege_cases`: ID, Projekt, Ersteller, Titel, Ziel, Frage, Zweck, Bestätigung, Status, Zeitstempel, Fehlercode.
- `module_zerlege_artifacts`: ID, Fall, Originalname, Typ, Größe, SHA-256, relativer Pfad, Zeitstempel.
- `module_zerlege_jobs`: ID, Fall, Artefakt, Analysetyp, Status, Fortschritt, Ergebnis-/Logpfad, Zeitstempel, Fehlercode.

Alle SQL-Abfragen sind parametrisiert. Dateiinhalte liegen nicht in SQLite.

### 9.2 API

Alle Routen liegen unter `/api/modules/zerlegewerkstatt` und brauchen Login plus Modulberechtigung; Projektzugriff wird zusätzlich pro Fall geprüft.

- `GET /cases?project_id=…`
- `POST /cases`
- `GET /cases/{case_id}`
- `DELETE /cases/{case_id}` mit Bestätigung, nur wenn kein Job läuft
- `POST /cases/{case_id}/artifacts` (Multipart)
- `POST /cases/{case_id}/intake/scan`
- `POST /cases/{case_id}/analyze`
- `GET /cases/{case_id}/report`
- `GET /runtime/status`

Fehler liefern stabile deutsche Codes, keine Hostpfade, Befehlszeilen oder Parser-Diagnosen.

### 9.3 Jobs

Ein prozessinterner, serieller Worker reicht für E1. Jobs sind in SQLite dauerhaft; nach Backend-Neustart werden `running`-Jobs als `interrupted` markiert. Ein zweiter Start desselben Artefakts/Analysetyps wird abgelehnt, solange der erste läuft.

## 10. HydraHive-Agentenwerkzeuge

E1 registriert nur:

- `reverse_cases` – Fälle des aktuellen Projekts auflisten.
- `reverse_inspect` – vorhandenes Artefakt statisch analysieren; verlangt Fall-/Artefakt-ID und zulässigen Analysetyp.
- `reverse_report` – Befunde/Belege einer Fallakte lesen.

Werkzeuge akzeptieren keine Dateipfade, keine REA-Befehle und keine URLs. `reverse_inspect` darf keinen Upload auslösen. Toolausgaben sind begrenzt und markieren Zieltexte als nicht vertrauenswürdig.

## 11. Bericht

Der Bericht trennt:

1. **Beobachtet:** Hashes, Dateiformat, Manifest, Strings, Funktionen, Imports, Aufrufe.
2. **Abgeleitet:** z. B. wahrscheinliche lokale HTTP-/UDP-/mDNS-Schnittstelle, jeweils mit Beleg-ID.
3. **Vermutet:** Hypothesen, die einen Mitschnitt oder Gerätetest brauchen.
4. **Unbekannt:** Verschlüsselung, dynamisch erzeugte Werte, serverseitige Logik.
5. **Nächste erlaubte Prüfung:** nur passive oder vom Nutzer ausdrücklich freigegebene Schritte.

Kein Bericht behauptet eine lokale Schnittstelle ohne Beleg.

## 12. Oberfläche

Route `/zerlegewerkstatt`, Navigationsgruppe „Arbeiten“.

- Projektwahl
- Fallliste mit Status
- Fall anlegen (inkl. Zweck/Berechtigungsbestätigung)
- Upload oder Samba-Eingang
- Artefakte mit Typ, Größe, Hash
- Analyseknöpfe passend zum erkannten Typ
- Fortschritt und verständliche Fehler
- Bericht mit Reitern Beobachtet / Abgeleitet / Vermutet / Unbekannt

Die Oberfläche nutzt die HydraHive-Farbstufen und enthält `altlook.test.ts` und `farbstufen.test.ts`.

## 13. Löschung und Aufbewahrung

- Fall löschen entfernt Hostdaten und Container-Arbeitsreste bestmöglich; SQLite-Zeilen werden in einer Transaktion gelöscht.
- Abgebrochene `.part`-Dateien und verwaiste Arbeitsordner werden beim Start und täglich entfernt.
- Keine automatische Cloud-Sicherung durch das Modul. Normale Server-Backups können Falldaten enthalten; darauf weist die Oberfläche hin.
- E1 hat keine automatische Ablaufzeit. Nutzer löscht Fälle bewusst.

## 14. Akzeptanzkriterien E1

- Eine PE-Datei und eine APK können hochgeladen, erkannt und statisch untersucht werden, ohne ausgeführt zu werden. **Erfüllt** — nachgewiesen am echten Container: OpenSSH-PE 2,3 s, WLED-APK 6,7 s, beide mit Confidence `observed`.
- Fall-, Artefakt- und Jobzugriff ist projekt- und berechtigungsgebunden. **Erfüllt**
- Traversal, Symlink, unbekannter Typ, leere Datei, >512 MiB und >2 GiB/Fall werden getestet abgelehnt. **Erfüllt**
- Analyse läuft nur im dedizierten Container und ohne Host-Secrets. **Erfüllt**
- Abbruch/Zeitlimit hinterlässt keinen laufenden Analyseprozess. **Erfüllt**
- Bericht enthält Hash, Werkzeugversion, Belegstatus und offene Fragen. **Erfüllt** — der Bericht nennt SHA-256, Format, Architektur und die Einschränkungen der Analyse; offene Fragen stehen unter „Unbekannt".
- Samba-Eingang nimmt nur stabile reguläre Dateien auf. **Erfüllt**
- Agent sieht höchstens drei kleine Werkzeuge, nicht 229 REA-Werkzeuge. **Erfüllt**
- Backendtests, Frontendtests, `check_test_safety.py`, Versionsprüfung und Kern-Frontend-Build sind grün. **Erfüllt**
- E2E-Gegenprobe mit öffentlicher WLED-App und offizieller Windows-OpenSSH-Datei ist dokumentiert. **Erfüllt**
