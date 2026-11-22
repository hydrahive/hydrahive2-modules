# Mining – Grafikkarten-Rechner schürfen lassen, was gerade am meisten bringt

Mining verwaltet deine GPU-Rechner im eigenen Netz und lässt jeden auf dem Coin schürfen, der bei Kryptex gerade am meisten einbringt.
Die Seite zeigt die aktuellen Erträge je Coin, den Zustand jedes Rechners und einen Verlauf.
Das hilft allen, die mehrere Rechner mit Grafikkarten betreiben und nicht selbst ständig umschalten wollen.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
   Ansehen und Steuern sind ab Werk nur für Admins frei. Andere Nutzer brauchen unter **Freigaben**
   die Freigabe **Mining ansehen** und zum Bedienen **Mining steuern (Rechner, Einstellungen)**.
2. Öffne **Mining** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Zuhause & Privat**).
3. Trage unten unter **Einstellungen** im Feld **Kryptex-Benutzername (oder Wallet)** deinen Kryptex-Namen ein,
   zum Beispiel `krxAB12CD34`, und klicke auf **Speichern**.
4. Klicke oben bei **Rechner** auf **Rechner koppeln**, gib einen **Name des Rechners** ein (zum Beispiel `rig-01`)
   und klicke auf **Befehl erzeugen**.
5. Kopiere den angezeigten Befehl (Knopf **Kopieren**) und füge ihn auf dem Rechner in ein Terminal ein.
6. Der Rechner erscheint in der Liste als **wartet auf Freigabe**. Klicke dort auf **Freigeben**.
   Danach misst der Rechner seine Karte durch und beginnt zu schürfen.

## Was du damit machen kannst

### Rechner
Die Liste zeigt alle gekoppelten Rechner mit den Spalten **Rechner**, **Zustand**, **Grafikkarte**, **Temp.**, **Strom**,
**Last** und **System**. Unter **System** steht das Betriebssystem und die Version des Rechner-Programms (`v…`).
Die Liste aktualisiert sich alle 15 Sekunden von selbst.

Der **Zustand** ist einer von: **wartet auf Freigabe**, **online**, **offline**, **ausgeschaltet** oder **gesperrt**.
Unter dem Namen steht, was der Rechner gerade tut:
- „Benchmark“ mit Zähler (z. B. „Benchmark 4/35“): Der Rechner misst nacheinander jeden Coin, den seine Karte kann.
- ⛏ mit Coin, Miner und Hashrate: Er schürft gerade. Dazu kommt die Zahl der angenommenen „Shares“.
- Ein grauer Hinweis, warum er steht, zum Beispiel **kein Kryptex-Benutzer eingetragen (Einstellungen)**.

Stecken in einem Rechner Karten von NVIDIA und AMD, stehen dort zwei Zeilen mit **NVIDIA** und **AMD**.
Bei Rechnern mit mehreren Karten klappst du mit „… Karten anzeigen“ die Werte je Karte auf.

Knöpfe je Rechner:
- **Freigeben**: nimmt einen neu gekoppelten Rechner auf.
- **Ausschalten** / **Einschalten**: hält den Rechner an oder lässt ihn wieder schürfen.
- **Neu messen**: verwirft alle Messwerte des Rechners, er misst alle Coins neu. Sinnvoll nach Treiber- oder Kartenwechsel.
  Vorher kommt eine Rückfrage.
- **folgt Energie**: Haken nur sichtbar, wenn die **Energie-Steuerung** eingeschaltet ist (siehe unten).
- **Sperren**: Der Rechner verliert sofort den Zugang und muss neu gekoppelt werden. Vorher kommt eine Rückfrage.
- **Entfernen**: erscheint erst bei einem gesperrten Rechner und löscht ihn aus der Liste.

### Neuen Rechner koppeln
Mit **Rechner koppeln** öffnet sich **Neuen Rechner koppeln**. Der Name darf nur Kleinbuchstaben, Ziffern und Bindestrich
enthalten, höchstens 32 Zeichen. Er erscheint auch bei Kryptex.
Nach **Befehl erzeugen** zeigt HydraHive einen fertigen Befehl für das Terminal des Rechners, darunter den **Code**.
Der Code ist 15 Minuten gültig und nur einmal verwendbar, also für jeden Rechner einen eigenen Befehl erzeugen.
Steht dort **Server-Zertifikat ist im Befehl hinterlegt**, vertraut der Rechner genau diesem Server.
Mit **Fertig** schließt du den Bereich, mit **Abbrechen** brichst du vorher ab.

### Verlauf
Sobald mindestens ein Rechner freigegeben ist, erscheint unter der Liste der **Verlauf** aller Rechner, jede Linie in eigener Farbe.
Oben wählst du, was gezeigt wird: **Ertrag €/Tag**, **Leistung %** (Anteil der eigenen Benchmark-Messung), **Watt** oder
**Temperatur**, und den Zeitraum **24 h** oder **7 Tage**. Neben der Überschrift steht der aktuelle Gesamtertrag pro Tag.
Am Anfang steht dort **Noch zu wenig Daten — der Verlauf füllt sich mit jeder Minute.**

### Erträge je Coin
Die Tabelle zeigt für eine gewählte **Grafikkarte**, was jeder Coin bei Kryptex gerade bringt:
**Coin**, **Algorithmus**, **Hashrate**, **Gebühr**, **pro Tag** und **pro Monat** (Tageswert mal 30).
Der Coin mit dem höchsten Ertrag ist grün markiert und trägt **bester**.
Beträge stehen in Euro, solange ein Wechselkurs vorliegt, sonst in US-Dollar.
- Ein `*` hinter dem Betrag heißt: selbst gerechnet, weil Kryptex hier keinen Wert liefert.
- Bei Gebühren mit „PROP“ schwankt die Auszahlung mit dem Glück des Pools.
- Die Hashraten sind Kryptex-Angaben für die Karte ohne Übertakten. Jeder Rechner misst später seine echten Werte.

HydraHive holt die Werte alle 5 Minuten. Daneben steht „Stand: vor … min“. Ist der Stand älter als 15 Minuten, steht dort
„Veraltet: …“, dann ist Kryptex gerade nicht erreichbar. Mit **Jetzt abrufen** oben rechts holst du die Werte sofort.

### Clore-Probelauf
Die Box **Clore-Probelauf** rechnet, ob sich das Mieten von GPU-Servern beim Marktplatz Clore.ai lohnen würde.
Es wird nichts gemietet. Ist der Probelauf eingeschaltet, vergleicht HydraHive alle 15 Minuten die Miete mit dem
Kryptex-Ertrag. Ein Treffer heißt: mindestens 12 % Plus nach einem Sicherheitsabschlag und mindestens 90 % Zuverlässigkeit
des Servers. Die Box zeigt das Ergebnis des letzten Laufs, die besten Treffer der letzten 24 Stunden
(**Karten**, Coin, **Ertrag/Tag**, **Miete/Tag**, ROI, Server) und je Tag, wie viele Läufe Treffer hatten.
Ein ✓ bei den Karten bedeutet: eigener Messwert. „Spot“ ist nur das Mindestgebot, ob man es bekommt, ist offen.
Ab Werk ist der Probelauf aus. Einschalten unter **Einstellungen** mit dem Haken
**Clore-Probelauf: Marktplatz alle 15 min lesen und rechnen (mietet nichts)**.

### Einstellungen
- **Kryptex-Benutzername (oder Wallet)**: wohin geschürft wird. Nur den Namen eintragen, ohne „.Worker“ dahinter.
  Den Worker-Namen setzt jeder Rechner selbst. Steht hinter dem krx-Namen ein Punkt mit Zusatz, erscheint ein Warnhinweis.
- **Server-Region**: welcher Kryptex-Server genutzt wird (ab Werk **Europa**).
- **Wechseln ab mehr Ertrag (%)**: Ein anderer Coin wird erst genommen, wenn er so viel mehr bringt (ab Werk 5 %).
- **Frühestens wechseln nach (Minuten)**: Mindestlaufzeit eines Coins vor einem Wechsel (ab Werk 15).
- **Abschlag für PROP-Coins (%)**: rechnet Coins mit schwankender Auszahlung vorsichtiger (ab Werk 0, höchstens 50).
- Haken für den **Clore-Probelauf** (siehe oben).

Änderungen gelten erst nach **Speichern**. Ohne Freigabe **Mining steuern (Rechner, Einstellungen)** siehst du die
Einstellungen nur, kannst sie aber nicht ändern.

### Energie-Steuerung
Für eine Photovoltaik-Anlage: Rechner mit Haken **folgt Energie** laufen nur, solange genug Leistung frei ist.
Unter **Quelle** wählst du:
- **aus — alle Rechner laufen immer** (ab Werk),
- **fester Wert** mit **Verfügbare Leistung (W)**,
- **abfragen (HTTP, nur im eigenen Netz)**: eine Adresse in deinem Heimnetz, die JSON liefert.
  Dazu **Adresse der Quelle**, **Feld in der Antwort (z. B. data.surplus_w)**,
  **Faktor (1000 wenn die Quelle kW liefert)** und **Quelle gilt als ausgefallen nach (Minuten)**.

Außerdem **Reserve (W)**, die immer abgezogen wird, und **Mindestzeit zwischen Ein/Aus (Minuten)**, damit Wolken nicht
ständig schalten (ab Werk 100 W und 10 Minuten). Zuerst laufen die Rechner mit mehr Ertrag pro Watt.
Oben rechts in der Box steht hinter **verfügbar:** die freie Leistung in Watt. Kommen keine Daten, steht dort
**keine Daten — Rechner mit „folgt Energie“ pausieren**.

## Mit Buddy und Agenten

Buddy und Agenten haben diese Werkzeuge. Beim Laden des Moduls wird außerdem der Skill `mining-workflow` bereitgestellt.

| Werkzeug | Was es tut |
|---|---|
| `mining_status` | Überblick über alle Rechner: online, offline oder aus, was sie gerade tun, Karte, Watt, Temperatur, letzter Fehler |
| `mining_earnings` | geschätzter Ertrag in €/Tag, jetzt und im Schnitt über bis zu 7 Tage, je Rechner und gesamt |
| `mining_rig_history` | Verlauf eines Rechners: Ertrag, Leistung, Watt, Temperatur, Coin-Wechsel |
| `mining_benchmarks` | Messwerte eines Rechners je Coin und Miner, nach Ertrag sortiert, dazu fehlgeschlagene und offene Messungen |
| `mining_clore_dryrun` | Ergebnisse des Clore-Probelaufs |
| `mining_rig_control` | Rechner ein- oder ausschalten, neu messen lassen, der Energie-Steuerung folgen lassen oder nicht |
| `mining_settings` | Einstellungen anzeigen oder ändern |

Du kannst zum Beispiel fragen: „Wie läuft das Mining?“, „Was hat das Mining in den letzten 7 Tagen gebracht?“,
„Welche Coins hat rig-01 gemessen?“, „Würde sich Clore lohnen?“ oder „Schalte rig-01 aus.“

Was nicht geht:
- Koppeln, Freigeben, Sperren und Entfernen von Rechnern gehen nur in der Oberfläche.
- Den Kryptex-Benutzernamen ändert nur die Oberfläche. Auch die Adresse und das Feld der Energie-Quelle sowie den
  Clore-Probelauf stellst du nur in der Oberfläche ein.
- Steuern und Einstellungen ändern geht nur mit der Freigabe **Mining steuern (Rechner, Einstellungen)**.
  Ohne sie lehnt das Werkzeug ab.

## Gut zu wissen

- Freigaben: Die Rechnerliste, **Jetzt abrufen** und die **Energie-Steuerung** siehst du nur mit der Freigabe
  **Mining steuern (Rechner, Einstellungen)**. Ohne sie siehst du die Ertragstabelle, den Clore-Probelauf und die
  Einstellungen (nur lesend).
- Am Rechner wird kein Port geöffnet. Der Rechner meldet sich alle 30 Sekunden von selbst beim Server.
  Nach 2 Minuten ohne Meldung gilt er als **offline**.
- Der Kopplungsbefehl ist für Linux-Rechner mit systemd gedacht und wird mit `sudo` ausgeführt. Er funktioniert nur einmal und
  15 Minuten lang. Abgelaufen? Einfach einen neuen erzeugen.
- Rechner-Programm aktualisieren: Die Version steht in der Spalte **System**. Wie man es am Rechner aktualisiert,
  beschreibt die Admin-Anleitung (README) des Moduls. Ein Rechner mit NVIDIA- und AMD-Karten und zu altem Programm meldet
  **AMD + NVIDIA im Rechner: bitte Client aktualisieren**.
- Watchdog: Stürzt der Miner ab oder liefert er 3 Minuten keine Hashrate, startet der Rechner ihn neu.
  Nach 3 Fehlversuchen in Folge gibt er auf und meldet den Fehler an HydraHive.
- Daten: Der Verlauf hält höchstens einen Wert pro Rechner und Minute und wird nach 7 Tagen gelöscht.
  Ergebnisse des Clore-Probelaufs bleiben 14 Tage.
- Energie-Quelle: Nur Adressen im eigenen Netz sind erlaubt, öffentliche Adressen werden abgelehnt.
- Typische Hinweise in der Rechnerliste:
  - **kein Kryptex-Benutzer eingetragen (Einstellungen)**: Benutzername unter **Einstellungen** eintragen.
  - **keine unterstützte Grafikkarte erkannt**: Treiber am Rechner prüfen.
  - **AMD: OpenCL-Treiber fehlt (sudo apt install mesa-opencl-icd)**: den genannten Befehl am Rechner ausführen.
  - **kein lohnender Coin für diese Karte**: Für diese Karte gibt es gerade keinen Coin mit Ertrag.
  - **pausiert: nicht genug Energie** bzw. **pausiert: Energie-Quelle antwortet nicht**: siehe **Energie-Steuerung**.
  - **Sensoren schlafen**: Die AMD-Karte ruht und meldet keine Temperatur und Watt. Beim Schürfen kommen die Werte.
  - **keine Sensoren**: Der Treiber liefert keine Messwerte.

*Stand: Mining 0.8.3, 22.11.2026*
