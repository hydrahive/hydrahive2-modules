# Zieldokument: HydraHive unter Windows mit einem Befehl installieren

> **Status:** FREIGEGEBEN (Till, 23.11.2026: „ok“)
> **Repo:** hydrahive2 (Kern), neue Datei `installer/windows/install.ps1` + README-Abschnitt
> **Auslöser:** Till, 23.11.2026: Die WSL-Anleitung in der README ist nicht idiotensicher (Ubuntu wieder öffnen?
> Autostart?). Wunsch: ein PowerShell-Skript, das alles macht.
> **Antworten Till:** Ubuntu-Benutzer abfragen · Autostart möglichst auch ohne Anmeldung, aber nur wenn es sauber
> geht · getestet wird von einem Nutzer auf echtem Windows.

## 1. Zielbild
Ein Laie öffnet eine PowerShell als Administrator, fügt **einen** Befehl ein, beantwortet nur die Fragen nach
Ubuntu-Benutzername und -Passwort, und hat danach HydraHive unter `https://localhost`. Nach einem Neustart von
Windows läuft HydraHive wieder von selbst.

## 2. Ablauf des Skripts (verbindlich)
1. **Vorprüfung:** Admin-Rechte (sonst klare Meldung, wie man PowerShell als Admin öffnet), Windows-Version
   (Windows 10 ab 19041 / Windows 11), Virtualisierung verfügbar. Bricht mit verständlicher deutscher Meldung ab,
   wenn etwas fehlt. Jede Meldung sagt, was der Nutzer jetzt tun soll.
2. **WSL und Ubuntu 26.04** (`Ubuntu-26.04`, laut Microsofts `DistributionInfo.json` verfügbar; Nachtrag Till
   23.11.2026: „24 ist veraltet“): installieren, falls nicht vorhanden; `wsl --update`. Ist ein Windows-Neustart nötig,
   meldet das Skript das, richtet einen einmaligen Weiterlauf nach der nächsten Anmeldung ein und macht danach
   an derselben Stelle weiter. Ist Ubuntu schon installiert, wird es weiterverwendet, nicht neu angelegt.
3. **Ubuntu-Benutzer:** Name und Passwort abfragen (Passwort verdeckt, zweimal), Benutzer anlegen, als
   Standardbenutzer setzen. Das Passwort wird nirgends gespeichert oder protokolliert.
4. **WSL-Einstellungen:**
   - `/etc/wsl.conf` in Ubuntu: `[boot] systemd=true` (vorhandene Abschnitte bleiben erhalten).
   - `%UserProfile%\.wslconfig`: `[general] instanceIdleTimeout=-1` – **zusammenführen**, vorhandene Einträge
     (z. B. `dnsTunneling`) bleiben unverändert. Vorher Sicherung `.wslconfig.bak`.
   - WSL neu starten und prüfen, dass systemd läuft.
5. **HydraHive installieren:** in Ubuntu ins Linux-Dateisystem klonen (nicht `/mnt/c`) und den normalen
   `installer/install.sh` ausführen – keine eigene zweite Installationslogik. DNS-Problem: dieselben Hinweise
   wie der Linux-Installer.
6. **Autostart:**
   - Stufe A (Pflicht): geplante Aufgabe „HydraHive (WSL)“, startet Ubuntu bei der Windows-Anmeldung.
   - Stufe B (nur wenn sauber möglich): Start beim Hochfahren **ohne** Anmeldung. Nur einbauen, wenn es ohne
     gespeichertes Windows-Passwort im Klartext und ohne Umbau des Systems geht. Ist das nicht belegbar machbar,
     bleibt es bei Stufe A und die README sagt das ehrlich. Entscheidung mit Quelle im PR begründen.
   - **Entscheidung 23.11.2026: Stufe B entfällt.** Quelle: microsoft/WSL Issue #9231 „Store WSL isn't accessible
     from Session 0“ (vom WSL-Team angelegt, offen, letzte Aktivität 28.07.2026): `wsl.exe` aus Session 0 – also
     Dienste und Aufgaben „unabhängig von der Anmeldung“ – endet mit „Access is denied“. Stufe A plus
     `instanceIdleTimeout=-1` (Microsoft-Doku wsl-config: Standard 15000 ms, `-1` schaltet das Beenden ab) hält
     HydraHive nach der Anmeldung dauerhaft am Laufen, auch ohne offenes Fenster.
7. **Abschluss:** wartet, bis `https://localhost` antwortet (mit Zeitlimit), zeigt Adresse und nächste Schritte.
   Bei Fehler: Meldung + Pfad zur Logdatei.

## 3. Weitere Regeln
- **Wiederholbar:** Ein zweiter Lauf beschädigt nichts (prüft jeden Schritt, überspringt Erledigtes).
- **Logdatei** unter `%LOCALAPPDATA%\HydraHive\install.log`, ohne Passwörter.
- **Start-Befehl** für die README: ein Einzeiler, der das Skript aus dem Repo (fester Tag/Branch main) lädt und
  ausführt. Kein `-ExecutionPolicy Bypass` dauerhaft setzen, nur für diesen Aufruf.
- **Deinstallation:** eigener Abschnitt in der README (Aufgabe entfernen, `wsl --unregister` mit Warnung, dass
  dabei alle Daten verloren gehen). Kein automatisches Löschen.
- Sprache der Meldungen: Deutsch, Englisch wenn die Windows-Oberfläche englisch ist.

## 4. Nicht-Ziele
- Kein eigener Windows-Dienst/Port von HydraHive außerhalb von WSL.
- Keine VMs, Container, Voice unter WSL (wie bisher).

## 5. Abnahme-Punkte
| # | Prüfung |
|---|---|
| W1 | Skript liegt unter `installer/windows/install.ps1`, PSScriptAnalyzer ohne Fehler; Ablauf wie §2 (Belegliste Abschnitt → Zeilen) |
| W2 | Statische Tests in CI (Pester oder Python-Textprüfung): Admin-Prüfung, `.wslconfig` wird zusammengeführt statt überschrieben (Test mit vorhandenem `dnsTunneling`), kein Passwort in Log/Datei, Linux-Installer wird aufgerufen statt nachgebaut |
| W3 | Zweiter Lauf ist harmlos (Test bzw. Logik-Beleg je Schritt) |
| W4 | Autostart Stufe A eingerichtet; Stufe B entweder umgesetzt mit Quelle oder begründet weggelassen |
| W5 | README (de + en): ein Befehl für die Installation, Abschnitt Autostart, Ubuntu wieder öffnen, Deinstallation; alte Schritt-für-Schritt-Anleitung bleibt als „Manuell“ |
| W6 | Test durch einen Nutzer auf echtem Windows (frisch, ohne WSL): Installation läuft durch, `https://localhost` zeigt HydraHive, nach Windows-Neustart läuft es wieder. Erst dann gilt das Ziel als erfüllt. |
