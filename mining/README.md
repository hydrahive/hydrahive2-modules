# Mining

HydraHive verwaltet GPU-Rechner im Netz und lässt jeden auf dem gerade
ertragreichsten Kryptex-Coin schürfen. Die Seite **Mining** zeigt die
Live-Erträge je Coin und die gekoppelten Rechner.

Stand 0.2.0: Ertragstabelle, Rechner koppeln, freigeben, an/aus, sperren.
Das Schürfen selbst (Miner, Messen, Umschalten) folgt in den nächsten Versionen.

## Einmalig in HydraHive

1. **Admin → Module → Mining** installieren.
2. Auf der Seite **Mining** unter *Einstellungen* den **Kryptex-Benutzernamen**
   eintragen, z. B. `krxAB12CD34`.
   - Nur den Namen. **Nicht** `krxAB12CD34.irgendwas`: Der Teil hinter dem
     Punkt ist bei Kryptex ein Rechnername. Den hängt HydraHive selbst an.
   - Kryptex prüft den Namen beim Anmelden nicht. Ein Tippfehler schürft ins
     Leere. Lieber zweimal hinschauen.

## Einen Rechner dazunehmen

**Voraussetzungen am Rechner:**

- Ubuntu 24.04 oder neuer, oder Debian 12 oder neuer (Python 3.11+ ist dort dabei)
- Grafikkarte mit installiertem Treiber
  - NVIDIA: `nvidia-smi` muss im Terminal funktionieren
  - AMD: Treiber `amdgpu` (bei Ubuntu/Debian Standard)
- `curl` und `sudo` (Debian minimal: `apt install curl sudo`)
- Der Rechner muss den HydraHive-Server per HTTPS erreichen. Am Rechner wird
  **kein Port geöffnet**, er verbindet sich von selbst zum Server.

**Ablauf:**

1. In HydraHive auf **Mining → Rechner koppeln** klicken und einen Namen
   vergeben, z. B. `rig-01`. Erlaubt sind Kleinbuchstaben, Ziffern und
   Bindestrich. Der Name erscheint auch bei Kryptex.
2. HydraHive zeigt einen fertigen Befehl. Diesen am Rechner in ein Terminal
   einfügen:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/hydrahive/hydrahive2-modules/main/mining/rig/install.sh \
     | sudo sh -s -- --server https://<server> --code XXXX-XXXX-XXXX --pin sha256//…
   ```

   - Der **Code** gilt 15 Minuten und nur einmal. Für jeden Rechner einen
     eigenen Befehl erzeugen.
   - Der **Pin** ist der Fingerabdruck des Server-Zertifikats. Damit vertraut
     der Rechner genau diesem Server, auch bei einem selbst ausgestellten
     Zertifikat.
3. Der Rechner erscheint in HydraHive als **„wartet auf Freigabe“**. Auf
   **Freigeben** klicken. Fertig.

Bei 20 Rechnern heißt das 20-mal: Befehl erzeugen, am Rechner einfügen,
freigeben. Pro Rechner dauert das etwa eine Minute.

**Was der Befehl am Rechner macht:**

- legt den Systemnutzer `hh-rig` an (ohne Login, nur Zugriff auf die Grafikkarte)
- kopiert das Programm nach `/opt/hydrahive-rig` (nur Python-Standardbibliothek,
  kein pip, keine Fremdpakete)
- speichert den Zugangsschlüssel in `/etc/hydrahive-rig/config.json`
  (nur für `hh-rig` lesbar)
- startet den Dienst `hydrahive-rig`. Er läuft auch nach einem Neustart weiter.

## Im Betrieb

```bash
systemctl status hydrahive-rig        # läuft der Dienst?
journalctl -u hydrahive-rig -f        # was meldet er?
```

In HydraHive zeigt die Liste je Rechner: Zustand (online, offline,
ausgeschaltet, gesperrt), Grafikkarte, Temperatur, Strom und Last.
Nach 2 Minuten ohne Meldung gilt ein Rechner als offline.

## Entfernen

1. In HydraHive den Rechner **sperren**. Er verliert sofort den Zugang. Danach
   **Entfernen**.
2. Am Rechner:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/hydrahive/hydrahive2-modules/main/mining/rig/uninstall.sh | sudo sh
   ```

## Wenn etwas nicht klappt

| Meldung | Ursache / Lösung |
|---|---|
| `Koppeln fehlgeschlagen … 401` | Code abgelaufen oder schon benutzt → neuen Befehl erzeugen |
| `… 409 rig_name_taken` | Name schon vergeben → anderen Namen wählen oder alten Rechner entfernen |
| `server_pin_mismatch` | Server-Zertifikat wurde getauscht → neuen Befehl erzeugen |
| `python3 >= 3.11 nötig` | System zu alt → Ubuntu 24.04+ / Debian 12+ |
| Grafikkarte „—“ in der Liste | Treiber fehlt: NVIDIA → `nvidia-smi` prüfen, AMD → `amdgpu` geladen? |
| `Server lehnt diesen Rig ab` im Log | Rechner wurde gesperrt → neu koppeln |

Getestet: Ubuntu 26.04 mit NVIDIA RTX 5060 Ti, Debian 12 (ohne Grafikkarte).
AMD bisher nur mit nachgestellten Daten.
