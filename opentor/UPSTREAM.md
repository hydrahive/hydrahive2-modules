# OpenTor-Upstream-Pinning

Technische Referenz:

- Repository: https://github.com/vichhka-git/OpenTor
- geprüfter Stand: `f3b87546f9699f9a319b94fb08b02849881f7fa6`
- Lizenz laut Upstream: MIT
- Abrufdatum: 2026-09-07

Der HydraHive-Adapter akzeptiert nur einen serverseitig konfigurierten Checkout
(`HYDRAHIVE_OPENTOR_ROOT`). Vor einem Update muss dieser Commit erneut auditiert
werden. Insbesondere sind Änderungen an `scripts/torcore.py`, `scripts/osint.py`,
`scripts/engines.py` und `scripts/setup.py` sicherheitsrelevant.

Der Upstream-Setup-Wizard wird nicht aus HydraHive heraus ausgeführt. Paket-
installation, Tor-Konfiguration und Prozessrechte bleiben Administrator-
aufgaben in einer dedizierten Umgebung.
