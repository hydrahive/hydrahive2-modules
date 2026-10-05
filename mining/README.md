# Mining

HydraHive verwaltet GPU-Rechner im Netz und lässt jeden auf dem gerade
ertragreichsten Kryptex-Coin schürfen. Die Seite **Mining** zeigt die
Live-Erträge je Coin und die gekoppelten Rechner.

Stand 0.7.1 (Rechner-Client 0.4.2): Ertragstabelle mit 16 Coins, Rechner
koppeln/freigeben/an/aus/sperren, echtes Schürfen mit Benchmark, automatischem
Umschalten, Watchdog und Energie-Steuerung. Rechner mit AMD- und NVIDIA-Karten
zugleich bekommen je Hersteller einen eigenen Miner. Neu: Clore-Probelauf (rechnet, ob sich
gemietete GPU-Server lohnen würden – mietet nichts).

**Schon im Einsatz?** Nach einem Modul-Update auch die Rechner aktualisieren,
siehe [Client aktualisieren](#client-aktualisieren).

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
  - AMD: Treiber `amdgpu` (bei Ubuntu/Debian Standard) **und ein OpenCL-Treiber**.
    Den bringt Ubuntu/Debian nicht von selbst mit, ohne ihn finden die Miner keine
    Karte. Einfachster Weg, auch für ältere Karten (RX 470/570/580, RX 550, Radeon VII):

    ```bash
    sudo apt install mesa-opencl-icd clinfo
    RUSTICL_ENABLE=radeonsi clinfo -l      # muss jede AMD-Karte zeigen
    ```

    Den Schalter `RUSTICL_ENABLE` setzt der Client beim Starten der Miner selbst.
    Wer ROCm von AMD installiert hat, braucht `mesa-opencl-icd` nicht.
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

## Client aktualisieren

Kommt eine neue Version des Moduls, braucht der Rechner oft auch einen neuen
Client. Am Rechner:

```bash
curl -fsSL https://raw.githubusercontent.com/hydrahive/hydrahive2-modules/main/mining/rig/install.sh \
  | sudo sh -s -- --update
```

- Die Kopplung bleibt. Kein neuer Code, keine neue Freigabe.
- Messwerte und Verlauf bleiben in HydraHive erhalten.
- Am Ende steht die neue Version, z. B. `Fertig: Client 0.4.1. Kopplung unverändert.`
  In HydraHive steht sie in der Rechner-Liste unter dem Betriebssystem (`v0.4.1`).
- Coins, die vorher auf diesem Rechner fehlgeschlagen sind, versucht HydraHive
  nach dem Update automatisch neu.

**Was braucht welche Version?**

| Client | Kann |
|---|---|
| 0.3.x | 9 Coins: CFX, ERG, IRON, NEXA, PRL, QUAI, RVN, XEL, XNA |
| ab 0.4.0 | zusätzlich ALPH, ETC, ETHW, OCTA, QTC, XTM (Cuckaroo29 und SHA3X); AMD + NVIDIA im selben Rechner |
| ab 0.4.1 | bei einem Miner-Abbruch steht der Grund im Journal |
| ab 0.4.2 | AMD: Mesa-OpenCL (`mesa-opencl-icd`) wird genutzt; fehlt OpenCL, zeigt HydraHive das statt zu messen; echte Kartennamen (z. B. „RX 470“ statt „0x67df“) und Lüfter |

Ein alter Client schürft weiter, bekommt aber nur die Coins, die er kennt.

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
   Karte kann, je etwa 3 Minuten. Manche Coins gehen mit mehreren Minern, dann
   wird jeder gemessen. Das sind bei NVIDIA 35 Messungen, bei AMD 22 (Anzeige
   z. B. „Benchmark 4/35“). Beim ersten Mal dauert das 1 bis 2 Stunden. Danach
   rechnet HydraHive mit den echten Werten. In der Ertragstabelle steht bei
   manchen Coins „—“, bis ein Rechner sie gemessen hat.
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
Client aktualisieren“ → [Client aktualisieren](#client-aktualisieren).

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

### Clore-Probelauf (nur rechnen)

Alle 15 Minuten liest HydraHive den öffentlichen Marktplatz von [Clore.ai](https://clore.ai)
und rechnet für jeden freien Server: **Kryptex-Ertrag pro Tag gegen Miete pro Tag**. Es wird
**nichts gemietet**, es braucht keinen Clore-Zugang und kein Geld.

- **Treffer** = mindestens 12 % Plus, nachdem der Ertrag vorsichtig gekürzt wurde
  (−15 % bei Herstellerwerten, −8 % bei eigenen Messungen, PROP-Coins mindestens −10 %),
  und der Server ist bei Clore zu mindestens 90 % zuverlässig.
- Miete inklusive Mietergebühr von Clore (+5 % normal, +1,25 % Spot). Spot ist nur das
  Mindestgebot – ob man es bekommt, ist offen.
- Hashraten: eigene Messwerte aus `backend/clore_benchmarks.json` (✓ in der Liste),
  sonst Herstellerangaben von Kryptex. Für Karten ohne Werte gibt es keine Rechnung.
- Die Box **Clore-Probelauf** auf der Mining-Seite zeigt den letzten Lauf, die besten Treffer
  der letzten 24 h und je Tag, wie oft es Treffer gab. Ergebnisse bleiben 14 Tage gespeichert.
- Ausschalten: *Einstellungen* → Haken „Clore-Probelauf“.

Ausführlich: `docs/clore-dryrun.md`.

## Mit Buddy

Buddy kennt das Mining (Skill `mining-workflow`, wird beim Laden des Moduls
installiert) und hat Werkzeuge dafür:

| Werkzeug | Was | Freigabe |
|---|---|---|
| `mining_status` | Überblick: welche Rechner online, was sie tun, letzter Fehler | Mining ansehen |
| `mining_earnings` | Ertrag €/Tag jetzt und im Schnitt (24 h / 7 Tage) | Mining ansehen |
| `mining_rig_history` | Verlauf eines Rechners, Coin-Wechsel | Mining ansehen |
| `mining_benchmarks` | Messungen eines Rechners, nach Ertrag sortiert | Mining ansehen |
| `mining_clore_dryrun` | Clore-Probelauf: würde sich Mieten lohnen? | Mining ansehen |
| `mining_rig_control` | Rechner ein/aus, neu messen, Energie folgen | Mining steuern |
| `mining_settings` | Einstellungen anzeigen/ändern | Mining steuern (ändern) |

Beispiele: „Würde sich Clore lohnen?“, „Wie läuft das Mining?“, „Was hab ich diese Woche verdient?“, „Warum ist
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
| „AMD: OpenCL-Treiber fehlt“ | `sudo apt install mesa-opencl-icd`, dann `sudo systemctl restart hydrahive-rig` |
| `OpenCL not found` / `Number of OpenCL supported GPUs: 0` im Log | wie oben: OpenCL-Treiber für AMD fehlt. Mit Client 0.4.2 misst der Rechner dann gar nicht erst |
| `Server lehnt diesen Rig ab` im Log | Rechner wurde gesperrt → neu koppeln |
| „kein Kryptex-Benutzer eingetragen“ | Einstellungen → Kryptex-Benutzername |
| Neue Coins werden nie gemessen | Alter Client → [Client aktualisieren](#client-aktualisieren) |
| `job_rejected:unknown_coin` im Log | Alter Client an neuem Modul → [Client aktualisieren](#client-aktualisieren). Danach versucht HydraHive diese Coins neu |
| `watchdog:exited` im Log | Miner bricht ab. Ab Client 0.4.1 stehen direkt darunter seine letzten Zeilen: `sudo journalctl -u hydrahive-rig -n 40 --no-pager`. SRBMiner schreibt zusätzlich nach `/var/lib/hydrahive-rig/srbminer.log` |
| `sha256_mismatch` im Log | Download beschädigt oder verändert → Rechner lädt beim nächsten Versuch neu |
| Coin wird übersprungen (`failed`) | Miner lief auf dieser Karte nicht (z. B. zu wenig Speicher) → „Neu messen“ nach Treiber-Update |
| „pausiert: Energie-Quelle antwortet nicht“ | Adresse/Feld der Quelle prüfen; nur Adressen im eigenen Netz |
| „AMD + NVIDIA im Rechner: bitte Client aktualisieren“ | [Client aktualisieren](#client-aktualisieren) |

Getestet: Ubuntu 26.04 mit NVIDIA RTX 5060 Ti, Debian 12 (ohne Grafikkarte, auch
das Update von Client 0.3.1 auf 0.4.1). AMD: Mesa-OpenCL erkennt auf Ubuntu 26.04
RX 470, Radeon VII und RX 550 (Kugelfang); Schürfen damit noch ungeprüft. Rechner
mit AMD + NVIDIA bisher nur mit nachgestellten Daten.
