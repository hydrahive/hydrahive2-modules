# Mining

HydraHive verwaltet GPU-Rechner im Netz und lässt jeden auf dem gerade
ertragreichsten Kryptex-Coin schürfen. Die Seite **Mining** zeigt die
Live-Erträge je Coin und die gekoppelten Rechner.

Stand 0.6.1: Ertragstabelle, Rechner koppeln/freigeben/an/aus/sperren, echtes
Schürfen mit Benchmark, automatischem Umschalten, Watchdog und Energie-Steuerung.

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

### Was der Rechner tut

1. **Benchmark**: Nach der Freigabe misst jeder Rechner alle Coins, die seine
   Karte kann, je etwa 3 Minuten (Anzeige „Benchmark 4/17“). Das dauert beim
   ersten Mal knapp eine Stunde. Danach rechnet HydraHive mit den echten Werten.
2. **Schürfen**: HydraHive wählt je Rechner den Coin mit dem höchsten Ertrag
   und schickt ihn an den Miner (rigel, lolMiner, SRBMiner — lädt der Rechner
   selbst von GitHub und prüft die Prüfsumme).
3. **Umschalten**: Lohnt ein anderer Coin um mehr als die *Schwelle* (Standard
   5 %) und läuft der aktuelle schon länger als die *Mindestlaufzeit*, wird
   gewechselt.
4. **Watchdog**: Stürzt der Miner ab oder liefert er 3 Minuten keine Hashrate,
   startet der Rechner ihn neu. Nach 3 Versuchen gibt er auf und meldet den
   Fehler; HydraHive nimmt dann einen anderen Coin.

### Rechner mit AMD- und NVIDIA-Karten

Stecken Karten beider Hersteller in einem Rechner (Client ab 0.4.0), läuft je
Hersteller ein eigener Miner: eigene Messung, eigener Coin. Die Liste zeigt
dann zwei Zeilen mit „NVIDIA“ und „AMD“. Bei Kryptex erscheinen sie als
`<rechner>-nvidia` und `<rechner>-amd`. Rechner mit nur einem Hersteller
bleiben wie bisher (Name ohne Zusatz, Messwerte bleiben erhalten).

Ein alter Client (0.3.x) in so einem Rechner bleibt aus und meldet „bitte
Client aktualisieren“.

**Neu messen** (Knopf in der Liste): nach Treiber- oder Kartenwechsel.

### Verlauf

Unter der Rechner-Liste zeigt eine Box den Verlauf aller Rechner, jede Linie in
eigener Farbe: **Ertrag €/Tag** (Standard), **Leistung %** der eigenen
Benchmark-Messung, **Watt** und **Temperatur** je Karte. Zeitraum 24 h oder
7 Tage. HydraHive speichert dafür höchstens einen Wert pro Rechner und Minute und
löscht ihn nach 7 Tagen.

### Energie-Steuerung (für PV)

Unter *Energie-Steuerung* eine Quelle wählen:

- **aus**: alle Rechner laufen immer (Standard).
- **fester Wert**: z. B. 2000 W für alle Rechner zusammen.
- **abfragen**: eine Adresse im eigenen Netz, die JSON liefert, z. B.
  `http://192.168.178.50/api/surplus` mit Feld `data.surplus_w`. Öffentliche
  Adressen sind gesperrt.

Nur Rechner mit Haken **folgt Energie** werden gesteuert. HydraHive schaltet
sie zu, solange die Leistung reicht (Reserve abgezogen). Zuerst die mit mehr
Ertrag pro Watt. Zwischen Ein und Aus liegt eine Mindestzeit (Standard 10 min),
damit Wolken nicht ständig schalten. Antwortet die Quelle nicht mehr, pausieren
diese Rechner.

## Mit Buddy

Buddy kennt das Mining (Skill `mining-workflow`, wird beim Laden des Moduls
installiert) und hat Werkzeuge dafür:

| Werkzeug | Was | Freigabe |
|---|---|---|
| `mining_status` | Überblick: welche Rechner online, was sie tun, letzter Fehler | Mining ansehen |
| `mining_earnings` | Ertrag €/Tag jetzt und im Schnitt (24 h / 7 Tage) | Mining ansehen |
| `mining_rig_history` | Verlauf eines Rechners, Coin-Wechsel | Mining ansehen |
| `mining_benchmarks` | Messungen eines Rechners, nach Ertrag sortiert | Mining ansehen |
| `mining_rig_control` | Rechner ein/aus, neu messen, Energie folgen | Mining steuern |
| `mining_settings` | Einstellungen anzeigen/ändern | Mining steuern (ändern) |

Beispiele: „Wie läuft das Mining?“, „Was hab ich diese Woche verdient?“, „Warum ist
rig-03 so schwach?“, „Schalte rig-02 aus“.

**Nicht per Chat** (nur Oberfläche): Rechner koppeln, freigeben, sperren, löschen und
den Kryptex-Benutzer ändern.

Master-Agenten (auch Buddy) bekommen die Werkzeuge beim nächsten Neustart von HydraHive
automatisch nachgetragen. Wer keine Freigabe „Mining steuern“ hat, sieht die beiden
Steuer-Werkzeuge nicht — sie prüfen das zusätzlich selbst.

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
| „kein Kryptex-Benutzer eingetragen“ | Einstellungen → Kryptex-Benutzername |
| Coin wird übersprungen, Rechner hat alten Client | Alte Clients bekommen nur Coins, die sie kennen. Client aktualisieren: `curl -fsSL https://raw.githubusercontent.com/hydrahive/hydrahive2-modules/main/mining/rig/install.sh \| sudo sh -s -- --update`. Danach werden fehlgeschlagene Coins automatisch neu versucht. |
| `watchdog:exited` im Log | Miner bricht ab. Darunter stehen im Journal die letzten Zeilen des Miners (`journalctl -u hydrahive-rig`); SRBMiner schreibt zusätzlich nach `/var/lib/hydrahive-rig/srbminer.log` |
| `sha256_mismatch` im Log | Download beschädigt oder verändert → Rechner lädt beim nächsten Versuch neu |
| Coin wird übersprungen (`failed`) | Miner lief auf dieser Karte nicht (z. B. zu wenig Speicher) → „Neu messen“ nach Treiber-Update |
| „pausiert: Energie-Quelle antwortet nicht“ | Adresse/Feld der Quelle prüfen; nur Adressen im eigenen Netz |
| „AMD + NVIDIA im Rechner: bitte Client aktualisieren“ | Client neu installieren (Befehl unter „Rechner koppeln“) |

Getestet: Ubuntu 26.04 mit NVIDIA RTX 5060 Ti, Debian 12 (ohne Grafikkarte).
AMD bisher nur mit nachgestellten Daten.
