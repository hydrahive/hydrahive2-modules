# Netzwerk – Internet und Heimnetz im Blick, mit belegbaren Daten

Das Modul Netzwerk zeigt dir, wie es deinem Internet und deinem Heimnetz geht. Es misst jede Minute selbst und
liest eine UniFi Dream Machine und eine FRITZ!Box aus. Wenn etwas nicht läuft, hast du Zahlen, die das belegen,
zum Beispiel für die Störungsmeldung beim Anbieter.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Unter **Credentials** legt der Admin den API-Schlüssel der Dream Machine an. Als Typ passt **Bearer Token**,
   **Custom Header** oder **Query Parameter**.
3. **Netzwerk** öffnen (Gruppe **Arbeiten**) und den Reiter **Einrichtung** wählen. Unter **Dream Machine** bei
   **Adresse** die Adresse der Dream Machine eintragen. Sie beginnt mit `https://`. Bei
   **API-Schlüssel aus dem Safe** den eben angelegten Schlüssel wählen und **Speichern** klicken.
4. Unter **Zertifikat der Dream Machine** auf **Fingerabdruck abrufen** klicken. Vergleiche ihn mit dem
   Fingerabdruck in der Dream Machine (Einstellungen → System). Stimmt er, klickst du **Stimmt – bestätigen**.
   Danach prüfst du mit **Verbindung testen**, ob alles klappt.
5. Wer mag, trägt noch unter **FRITZ!Box (Kabelmodem)** die Adresse der FRITZ!Box und unter **Gebuchter Tarif**
   den Tarif ein. Ab jetzt sammelt das Modul rund um die Uhr. Die erste eigene Messung kommt etwa eine Minute nach dem Start.

## Was du damit machen kannst

Oben stehen die Reiter **Übersicht**, **Geräte**, **Clients**, **Netz**, **Verkehr** und **Störungen**. Wer das
Modul einrichten darf, sieht zusätzlich **Einrichtung**.

### Übersicht
- Ganz oben steht, wie du gerade im Internet bist: „über Kabel“, „über Mobilfunk-Ersatz“, „kein Internet“ oder
  „Weg unbekannt“.
- Drei Ampeln zeigen **Zuhause**, **FRITZ!Box** und **Internet**: „läuft“, „hakt“, „aus“ oder
  „keine Messung“. „Hakt“ heißt: Es gehen Pakete verloren oder die Antwort dauert zu lange (zu Hause und zur
  FRITZ!Box über 20 ms, ins Internet über 60 ms).
- **Letzte 24 Stunden** zeigt den Verlauf von Antwortzeit und Verlust.
- **Letzter Geschwindigkeitstest der Dream Machine** zeigt **Herunter** und **Hoch** in Mbit/s. Hast du einen
  Tarif eingetragen, steht dabei, wie viel Prozent vom Tarif ankommen. Liegt der Upload unter der Hälfte, ist er
  rot markiert.
- Der Kasten **Dream Machine** nennt den Anbieter, die Zahl der Geräte und Clients und wann zuletzt abgerufen
  wurde. Schlug der letzte Abruf fehl, steht dort der Grund.
- Die Übersicht lädt sich jede Minute neu.

### Geräte
Hier stehen Router, Switches und Access Points der Dream Machine, jeweils mit Zustand (zum Beispiel online,
offline, „Update läuft“), Modell und Adresse. Dazu kommen Firmware, ein Hinweis bei verfügbarem Update,
Laufzeit, Zahl der Clients, CPU, Speicher und Temperaturen. Unter **Anschlüsse** siehst du jeden Port mit
Geschwindigkeit, Verkehr, PoE-Leistung und Fehlern. Unter **Funk** siehst du je Frequenzband Kanal,
Sendeleistung, Clients, Auslastung und Zufriedenheit.

### Clients
Hier stehen alle Geräte, die die Dream Machine im Netz kennt, mit Name, Hersteller, Adresse und woran sie hängen
(Kabel mit Port oder WLAN mit Band und Access Point). Bei WLAN-Geräten siehst du das Signal als „gut“, „ok“,
„schwach“ oder „schlecht“. Gäste und Geräte mit fester Adresse sind markiert. Offline-Geräte zeigen, wann sie
zuletzt gesehen wurden.
- Im Suchfeld suchst du nach Name, Hersteller oder IP.
- Filtern kannst du nach **Online**, **Offline** oder **Alle** und nach **Alle**, **WLAN** oder **Kabel**.
  Beim Öffnen sind nur die Online-Geräte zu sehen.

### Netz
- **Aufbau** zeigt das Netz als Baum: welches Gerät an welchem hängt. Die Clients eines Geräts sind zuerst
  eingeklappt, mit „anzeigen“ klappst du sie auf.
- **Netze** listet die Netze mit Art (Internet oder Heimnetz), VLAN, Adressbereich und DHCP.
- **WLANs** zeigt jedes WLAN mit an/aus, Verschlüsselung, Frequenzbändern und ob es ein Gästenetz oder versteckt
  ist.
- **Portfreigaben** listet die Freigaben der Dream Machine. Darunter steht, wie viele Firewall-Regeln und Routen
  es gibt.

### Verkehr
- **Clients mit dem meisten Verkehr (seit Verbindung)** zeigt die 20 Online-Geräte mit dem meisten Verkehr,
  jeweils mit Download und Upload.
- **Verkehr je Gerät und Anschluss** zeigt den Verkehr jedes Netzgeräts und seiner belegten Ports.

Auf den Reitern **Geräte**, **Clients**, **Netz** und **Verkehr** holt **Neu laden** frische Daten von der Dream
Machine.

### Störungen
Bei **Zeitraum** wählst du 7, 30 oder 90 Tage. Voreingestellt sind 30 Tage.
- **Ausfallzeit je Tag (laut Dream Machine)** und **Ohne Kabel je Tag (eigene Messung)** zeigen je Tag, wie
  lange es gehakt hat. Tage mit einer Stunde oder mehr sind rot markiert.
- **Geschwindigkeitstests** listet alle Tests im Zeitraum mit Download und Upload. Liegt der Upload unter der
  Hälfte des Tarifs, ist er rot markiert.
- **Alle Störungen** listet jede Störung mit Art, Beginn, Ende, Dauer und Quelle. Arten sind „Internet weg“,
  „Kurzer Aussetzer“ (laut Dream Machine) sowie „Kein Internet“ und „Kabel weg“ (eigene Messung). Kurze
  Aussetzer unter 10 Sekunden blendet die Liste aus.

### Einrichtung (nur mit dem Recht „Netzwerk einrichten“)
- **Dream Machine**: **Adresse** und **API-Schlüssel aus dem Safe**.
- **FRITZ!Box (Kabelmodem)**: **Adresse** der FRITZ!Box. Dazu gibt es ein Feld für einen Benutzer aus dem Safe.
  Den nutzt das Modul im Moment aber noch für keine Messung. Die FRITZ!Box wird ohne Anmeldung gelesen.
- **Gebuchter Tarif**: **Herunter (Mbit/s)**, **Hoch (Mbit/s)** und **Monatspreis (€)**.
- **Speichern** geht erst, wenn eine Adresse mit `https://` und ein Schlüssel gewählt sind.
- **Zertifikat der Dream Machine**: **Fingerabdruck abrufen**, vergleichen, **Stimmt – bestätigen**. Danach
  spricht das Modul nur noch mit genau diesem Gerät. Mit **Verbindung testen** siehst du, ob es klappt und welche
  Version die Dream Machine hat.
- Nach dem Bestätigen gibt es **Jetzt abrufen**. Das holt sofort neue Ereignisse und Geschwindigkeitstests.
- **Sicherung übernehmen** liest eine früher gesicherte Datei der Dream Machine (.json oder .json.gz) als
  Vorgeschichte ein.

## Gut zu wissen

- Nur lesen: Das Modul ändert an der Dream Machine und an der FRITZ!Box nichts.
- Messung: Die eigene Messung läuft jede Minute. Sie misst zwei öffentliche Server im Internet und, wenn sie als
  IP-Adresse eingetragen sind, auch die Dream Machine und die FRITZ!Box. Die Dream Machine wird alle 5 Minuten abgefragt, Ereignisse, Geschwindigkeitstests und
  Verlauf zusätzlich jede Stunde.
- Kabel oder Mobilfunk: Hat die FRITZ!Box einen Mobilfunk-Ersatz, erkennt das Modul, über welchen Weg du gerade
  im Internet bist. Dafür muss die Adresse der FRITZ!Box eingetragen sein. In der FRITZ!Box muss
  „Statusinformationen über UPnP übertragen“ eingeschaltet sein. Ohne FRITZ!Box steht dort „Weg unbekannt“.
- Passwörter: WLAN-Passwörter und andere Schlüssel aus den Antworten der Dream Machine werden sofort verworfen.
  Sie erscheinen nirgends. Zugänge kommen nur als Name aus dem Safe, ein Passwortfeld gibt es im Modul nicht.
- Nur das Heimnetz: Als Adresse sind nur Geräte im eigenen Heimnetz erlaubt, also private Adressen oder Namen wie
  `….local`, `….lan` oder `….box`. Sonst kommt „Nur Geräte im eigenen Heimnetz sind erlaubt.“
- Dream Machine nicht erreichbar: Dann zeigen die Reiter den letzten Stand mit dem Hinweis „Die Dream Machine
  antwortet gerade nicht – angezeigt wird der Stand von …“.
- Rechte: Es gibt zwei Rechte, „Netzwerk ansehen“ und „Netzwerk einrichten (Zugänge, Tarif,
  Störungsmeldungen)“. Nach der Installation haben beide nur Admins. Andere Nutzer gibt ein Admin unter
  **Freigaben** frei.
- Kein Buddy: Das Modul hat keine Werkzeuge für Buddy oder Agenten. Bedient wird es nur über die Seite.
- Grenzen: Tarifwerte gehen von 0 bis 100.000. Eine Sicherung darf höchstens 50 MB groß sein.
- Typische Meldungen:
  - „Bitte zuerst den Fingerabdruck der Dream Machine bestätigen.“: Unter **Einrichtung** den Fingerabdruck
    abrufen und bestätigen.
  - „Die Dream Machine weist sich anders aus als bestätigt – bitte den Fingerabdruck neu prüfen.“: Das Zertifikat
    hat sich geändert, etwa nach einem Update oder Tausch. Fingerabdruck neu abrufen und vergleichen.
  - „Das Gerät lehnt den Zugang ab – Schlüssel prüfen.“: Der API-Schlüssel im Safe stimmt nicht.
  - „Das Gerät antwortet nicht.“: Adresse prüfen oder ob das Gerät läuft.
  - „Diese Datei ist keine Sicherung der Dream Machine.“: Die gewählte Datei passt nicht oder ist zu groß.

*Stand: Netzwerk 0.2.1, 22.11.2026*
