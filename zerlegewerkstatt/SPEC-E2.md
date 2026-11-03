# Zerlege-Werkstatt – Spezifikation E2: native statische Analysebreite

**Status:** in Umsetzung

## 1. Ziel

Die Werkstatt bildet die statisch und offline nutzbaren Fähigkeiten des REA-Vorbilds als eigene HydraHive-Funktionen ab. Nutzer wählen eine fachliche Analyse, niemals einen REA-Befehl. HydraHive kontrolliert Dateityp, Argumente, Grenzen, Evidenz, Bericht und Oberfläche. REA 6.8.0 bleibt eine gepinnte Analyse-Engine im isolierten Container; ein REA-MCP-Server ist ausdrücklich ausgeschlossen.

Erfolg wird nicht an der Zahl sichtbarer Knöpfe gemessen, sondern an echten Fragen, die ein Fall beantworten kann:

- Was ist in der Datei enthalten und wie ist sie aufgebaut?
- Welche externen Bibliotheken, APIs, Berechtigungen und Protokolle verwendet sie?
- Welche Klassen, Mitglieder, Zeichenketten, Exporte und Ressourcen sind belegt?
- Welche Endpunkte, DNS-Namen und TLS-Ziele enthält ein passiver eigener Mitschnitt?
- Welche Befunde sprechen für eine lokale Geräteschnittstelle, und welcher Beleg trägt die Aussage?

## 2. Unveränderliche Grenzen

- Keine Ausführung des Zielartefakts.
- Kein Browser-, ADB-, Frida-, Debugger-, Prozess-, Geräte- oder Live-Capture-Zugriff.
- Kein freier REA-Unterbefehl und keine freien Optionen aus API, UI oder Agentenwerkzeug.
- Netzwerk während jeder Analyse aus; Arbeitsordner danach entfernt.
- Prozess als Benutzer `rea`, `no-new-privs`, alle Linux-Capability-Sets leer.
- Ergebnisgröße und Laufzeit begrenzt; vollständige Evidenz getrennt von der kompakten Ansicht.
- Jeder Typ braucht mindestens einen echten Positivtest mit einem zulässigen Artefakt und einen Negativtest gegen einen unpassenden Typ.

## 3. Etappen und Funktionsmatrix

### E2a – spezifizierte Lücken und benutzbarer Einstieg

| Fachfunktion | REA-Engine | Dateiart | Status |
|---|---|---|---|
| Allgemeine Inventur | `inspect-artifact` | PE, APK, ELF, Firmware, PCAP | vorhanden |
| Android-Manifest/Paket | `inspect-android-package` | APK | vorhanden |
| .NET-Identität | `inspect-managed-artifact` | PE | vorhanden |
| .NET-Typen/Mitglieder/Signaturen/Strings | `inspect-managed-members` | PE/CLI | umgesetzt, E2E belegt |
| Passiver Netzwerk-Mitschnitt | `inspect-pcap-capture` | PCAP/PCAPNG | umgesetzt, E2E belegt |
| Native Übersicht | `analyze --provider ghidra` | PE, ELF, Firmware | vorhanden, echter Tiefentest offen |

### E2b – tiefe Inventur vorhandener Dateiarten

Die folgenden Funktionen brauchen keine neuen Uploadformate. Elf davon sind in 0.2.0 umgesetzt und jeweils durch den vollständigen Offline-`IncusRuntime`-Pfad belegt:

| Gruppe | Fachfunktion | REA-Engine |
|---|---|---|
| alle | Blockentropie/Packungsindikatoren | `inspect-byte-entropy` |
| PE/ELF | Exporte | `inspect-native-exports` |
| PE | Imports und Delay-Loads | `inspect-pe-imports` |
| PE | Ressourcen und eingebettete Nutzlasten | `inspect-pe-resources` |
| PE | TLS-Callbacks und Load-Config | `inspect-pe-load-config` |
| PE | Authenticode-Zertifikatstabelle | `inspect-pe-certificates` |
| ELF | Notes/Build-ID/ABI-Hinweise | `inspect-elf-notes` |
| ELF/PE | Go-Build- und Modulinfos | `inspect-go-binary` |
| ELF/PE | Rust/cargo-auditable-Abhängigkeiten | `inspect-rust-binary` |
| ELF | Kernelmodul-Metadaten | `inspect-kernel-module` |
| APK | Signaturschemata, Signierer und Digests | `inspect-apk-signature` |
| Firmware | Signaturkandidaten/Regionen | `inspect-firmware-regions` |
| ELF | Dateilayout | `inspect-binary-layout` – erst nach gepinntem pwntools-Preflight |
| PE/ELF | Header, Sektionen, Symbole, Relokationen | `inspect-with-objdump` mit vier festen Betriebsarten |

Nicht jedes Artefakt enthält Go-, Rust-, Kernel- oder Zertifikatsdaten. „Nicht vorhanden“ muss als belegte Abwesenheit oder klare Nichtanwendbarkeit erscheinen, nicht als technischer Fehler.

### E2c – zusätzliche statische Dateiarten

Neue Uploadtypen werden nur zusammen mit Magic-/Strukturprüfung und echten Fixtures zugelassen:

- WASM (`inspect-wasm-artifact`, benötigt gepinntes WABT),
- SQLite (`inspect-sqlite-database`, zunächst nur Schema-Inventur, keine Tabellenzeilen),
- Erlang BEAM (`inspect-erlang-beam`),
- EVM-Bytecode (`inspect-evm-interface`, getrennte geprüfte Typen für raw/hex),
- GGUF/safetensors (`inspect-model-artifact`, nur Header-Hash),
- CPython-PYC 3.7–3.13 (`inspect-python-pyc`),
- Flattened Device Tree (`inspect-devicetree`).

### E2d – zielgerichtete Tiefenanalyse

Diese Funktionen benötigen zusätzliche strukturierte Parameter oder Beziehungen zwischen Artefakten und werden nicht als parameterlose Knöpfe vorgetäuscht:

- Android-Klassensuche und Auswahl einer exakten Klasse/Methode,
- native Funktion/decompile/search/xrefs/trace mit validierter Adresse oder Prozedur,
- IL2CPP-Metadaten plus zugehöriges natives Binary,
- Firmware-Extraktion mit zuvor belegter Region,
- Vergleich zweier Versionen/Evidence-Bundles.

## 4. Bericht und Evidenz

Jeder Befund erhält intern:

- stabile Beleg-ID,
- Artefakt-ID und SHA-256,
- Analysetyp und Engine-Version,
- Confidence (`observed`, `derived`, `suspected`),
- normalisierte Felder statt beliebig abgeflachtem JSON,
- Limitations und Coverage.

`derived` darf nur aus expliziten Regeln entstehen, zum Beispiel:

- DNS-Abfrage oder TLS-SNI auf privaten/lokalen Namen → „lokale oder LAN-nahe Kommunikation möglich“, mit Beleg-ID;
- importierte Netzwerkbibliothek allein → keine Protokollbehauptung, nur Untersuchungsansatz;
- Android-Berechtigung plus Manifest-Service → belegte Fähigkeit, nicht belegte tatsächliche Nutzung.

Seit 0.2.0 füllt eine deterministische Regelschicht `derived` und `suspected` für lokale PCAP-Indikatoren bzw. Windows-Netzwerkimporte und liefert ein Belegverzeichnis. Weitere Regeln folgen nur mit strukturierten Positiv- und Negativtests. Eine lokale Schnittstelle darf weiterhin nie ohne Beleg behauptet werden.

## 5. Oberfläche

- Projektname auswählen, keine Projekt-ID eintippen.
- Leerer Zustand, Ladefehler und fehlende Berechtigung sind unterscheidbar.
- Artefaktkarte gruppiert Analysen nach „Überblick“, „Aufbau“, „Code/Abhängigkeiten“, „Netzwerk“ und „Signaturen“.
- Bereits laufende oder erledigte Analyse ist sichtbar; derselbe Job wird nicht versehentlich erneut gestartet.
- Nicht anwendbare Analyse erscheint nicht.
- Berichtsabschnitte zeigen Aussage, Confidence, Beleg und Quelle statt unbeschrifteter JSON-Zeilen.

## 6. Abnahme je Etappe

Eine Etappe gilt erst als fertig, wenn:

1. Unit-/Integrationstests rot→grün dokumentiert sind,
2. mindestens ein echtes Artefakt je neuer Dateifamilie durch den vollständigen `IncusRuntime`-Pfad lief,
3. der Prozess nachweislich als `rea` ohne Capabilities lief,
4. kein Restprozess/Arbeitsordner blieb und das Netz wiederhergestellt wurde,
5. die Oberfläche auf einer installierten Modulversion im Browser durchgespielt wurde,
6. Bericht und Agentenwerkzeug denselben Befund mit Beleg-ID liefern,
7. Security-Review und HydraHive-Review keine offenen High-/Medium-Funde haben.
