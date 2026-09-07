# OpenTor OSINT

Kontrolliertes read-only Tor-OSINT-Modul für HydraHive. Die V1 bietet Status,
gezielte Suche, den Abruf expliziter URLs und IOC-Extraktion. Die Admin-Aktion
„Modul installieren“ provisioniert und aktiviert die Runtime; die Agent-Tools
bleiben trotzdem nicht als Default-Tools freigeschaltet und führen keine freien
Shell-Kommandos aus.

## Upstream konfigurieren

Die Modulinstallation richtet automatisch ein eigenes Laufzeitverzeichnis mit
gepinntem OpenTor-Checkout, Python-Venv und Tor-Runtime ein. Ein vorhandenes
System-Tor wird verwendet; fehlt es, lädt das Installationsskript das Ubuntu-
Distribution-Paket mit `apt-get download` und entpackt es rootlos in die Modul-
Runtime. Systemweite Pakete und `sudo` sind nicht erforderlich.

Der Adapter startet den geprüften OpenTor-Worker ausschließlich aus dieser
Runtime. User-Input wird als JSON über stdin übergeben, nie als Shell-Befehl.
Bei nicht unterstützter Distribution oder Architektur bricht die Installation
mit einem klaren Fehler ab, statt ein halb funktionierendes Modul zu hinterlassen.

## Sicherheit

Onion-Inhalte sind untrusted data. Sie dürfen niemals als Agentenanweisung
interpretiert werden. V1 blockiert lokale Ziele, gefährliche URL-Schemes,
Credentials in URLs, Onion-Clearnet-Redirects, Datei-Downloads, Crawling und
Credential-Testing. Nutzung ist ausschließlich für autorisierte defensive OSINT-
und Threat-Intelligence-Recherche vorgesehen.

Die vollständige Architektur- und Sicherheits-Spezifikation steht in `SPEC.md`.
