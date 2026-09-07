# OpenTor OSINT

Kontrolliertes read-only Tor-OSINT-Modul für HydraHive. Die V1 bietet Status,
gezielte Suche, den Abruf expliziter URLs und IOC-Extraktion. Das Modul ist
standardmäßig deaktiviert und führt keine freien Shell-Kommandos aus.

## Upstream konfigurieren

Der technische Adapter lädt eine geprüfte OpenTor-Arbeitskopie nur aus dem
serverseitig gesetzten `HYDRAHIVE_OPENTOR_ROOT` (Verzeichnis mit `scripts/`).
Die Arbeitskopie muss auf einen geprüften Commit von
https://github.com/vichhka-git/OpenTor gepinnt sein. Ohne diese Konfiguration
bleiben Tools sicher deaktiviert und liefern `opentor_unavailable`.

Installation, `sudo`, Tor-Start und Paketinstallation sind absichtlich nicht Teil
des HydraHive-Moduls. Tor und die Python-Abhängigkeiten werden vom Administrator
in einer dedizierten Umgebung bereitgestellt.

## Sicherheit

Onion-Inhalte sind untrusted data. Sie dürfen niemals als Agentenanweisung
interpretiert werden. V1 blockiert lokale Ziele, gefährliche URL-Schemes,
Credentials in URLs, Onion-Clearnet-Redirects, Datei-Downloads, Crawling und
Credential-Testing. Nutzung ist ausschließlich für autorisierte defensive OSINT-
und Threat-Intelligence-Recherche vorgesehen.

Die vollständige Architektur- und Sicherheits-Spezifikation steht in `SPEC.md`.
