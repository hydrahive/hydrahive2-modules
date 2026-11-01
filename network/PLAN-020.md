# Modul „Netzwerk“ 0.2.0 – UniFi auslesen und anzeigen

Stand 01.11.2026 · Task d2b126e4 · freigegeben von Till im Chat („ok fange an“). Nur lesend.

## Ziel
Die Dream Machine wie in der UniFi-Oberfläche ansehen und auswerten, direkt in HydraHive: Geräte, Clients, Netz,
Verkehr. Die bestehende Übersicht (Messung, Internet-Status) bleibt.

## Reiter
- **Geräte:** je Gerät Status, Modell, IP, Firmware (Update verfügbar?), Laufzeit, CPU/Speicher, Temperaturen,
  Clients, Verkehr, Uplink (an welchem Gerät/Port). Ports mit Status, Geschwindigkeit, PoE, Fehlern, Verkehr. Funk je
  Band mit Kanal, Sendeleistung, Auslastung, Clients, Zufriedenheit.
- **Clients:** alle aktiven und bekannten Clients. Suche, Filter (online/offline, WLAN/Kabel, Gast), Spalten Name,
  Hersteller, IP, Verbindung (WLAN mit Band und Signal bzw. Kabel mit Switch/Port), Netz, Laufzeit, Verkehr.
- **Netz:** Aufbau als Baum (Dream Machine → Switches/Access Point → Clients), Netze/VLANs mit DHCP-Bereich,
  WLANs (Name, Verschlüsselung, Bänder, Gast, versteckt), Portfreigaben, Firewall-Regeln und Routen (Anzahl).
- **Verkehr:** Clients nach Datenmenge, Verkehr je Gerät und Port.

## Quellen (gemessen 01.11., Network 10.6.109, API-Schlüssel)
`stat/device`, `stat/sta`, `rest/user`, `rest/networkconf`, `rest/wlanconf`, `rest/portforward`,
`rest/firewallrule`, `rest/routing`, v2 `topology`. Verkehr nach Apps (`stat/sitedpi`) liefert hier leer (App-Erkennung
in der Dream Machine aus) – kommt erst, wenn das Format an echten Daten geprüft ist. Verkehr in 0.2.0: je Client und
je Port. Richtung: UniFi zählt aus Sicht des Netzes, `tx` = zum Client (beim Client „empfangen“).

## Regeln
- **Geheimnisse:** UniFi legt Schlüssel und Passwörter in Feldern mit `x_` ab, z. B. das WLAN-Passwort in
  `x_passphrase`. Alle `x_`-Felder werden direkt nach dem Empfang verworfen, auf jeder Ebene, bevor etwas
  gespeichert, verarbeitet oder ausgegeben wird. Die Ausgabe enthält nur ausgewählte Felder (Positivliste). Ein Test
  mit Lockvogel-Werten prüft alle Routen.
- Abruf beim Öffnen der Seite, Zwischenspeicher 30 s. Ist die Dream Machine nicht erreichbar, wird der letzte Stand
  mit Hinweis gezeigt.
- Rechte wie bisher: ansehen `module.network`.

## Nicht in 0.2.0
Verwalten (sperren, umbenennen, neu starten, WLAN schalten) → 0.3.0 mit Bestätigung. Agenten-Werkzeuge danach.
