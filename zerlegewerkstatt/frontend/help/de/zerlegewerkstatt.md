# Zerlege-Werkstatt – eigene Programme, Apps und Firmware statisch untersuchen

Die Zerlege-Werkstatt untersucht Windows-Programme, Android-Apps, Linux-Programme, Firmware und passive
Netzwerk-Mitschnitte, die dir gehören oder die du ausdrücklich untersuchen darfst. Sie arbeitet nur statisch und
offline: Keine Datei wird gestartet, keine App installiert und kein Live-Verkehr mitgeschnitten. Das hilft dir,
wenn du verstehen willst, wie ein eigenes Gerät oder Programm aufgebaut ist und mit wem es spricht, und jede
Aussage mit einem Beleg nachprüfen möchtest.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Der Server braucht dafür die
   Container-Verwaltung Incus. Die Installation richtet einen eigenen Analyse-Container ein.
2. Anfangs dürfen nur Admins die Werkstatt nutzen. Andere Nutzer gibt ein Admin unter **Freigaben** frei:
   **Zerlege-Werkstatt (Apps, Firmware und Mitschnitte)** für die Seite und
   **Agentenwerkzeuge der Zerlege-Werkstatt** für die Agenten-Werkzeuge.
3. Die Werkstatt arbeitet immer in einem Projekt. Hast du noch keins, lege zuerst unter **Projekte** eines an.
4. Öffne die **Zerlege-Werkstatt** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich
   **Wissen & Recherche**) und wähle oben das **Projekt**.
5. Fülle links **Neuer Fall** aus, bestätige **Ich darf das Material untersuchen.** und klicke **Fall anlegen**.
6. Rechts unter **Artefakte** klickst du **Datei hochladen**. Unter der Datei startest du zuerst
   **Allgemein untersuchen**. Sobald der Auftrag fertig ist, liest du darunter den **Bericht**.

## Was du damit machen kannst

### Anleitung auf der Seite
Oben steht immer der Kasten **So arbeitest du mit der Zerlege-Werkstatt** mit sechs Schritten zum ersten Bericht.
Mit **Ausführliche Anleitung öffnen** klappst du eine lange Anleitung auf: Bausteine, gute Fragestellungen,
welche Datei wofür taugt, welche Analyse wann passt, vier Beispielabläufe, Hilfe bei Fehlern und die Grenzen.
Ein Klick auf die Überschrift klappt sie wieder zu.

### Fälle
Ein Fall bündelt eine konkrete Frage, ihren Zweck und deine Berechtigung. Unter **Fälle** siehst du alle Fälle
des gewählten Projekts mit Ziel und der Zahl der Artefakte und Analysen. Ein Klick öffnet den Fall.

Unter **Neuer Fall** trägst du ein:
- **Titel** – ein kurzer Name, mindestens drei Zeichen.
- **Ziel oder Gerät** – was du untersuchst, möglichst mit Version. Das Feld beschreibt nur, es verbindet sich
  nicht mit dem Gerät.
- **Fragestellung** – eine konkrete Frage, mindestens zehn Zeichen. Mehrere kleine Fragen bringen bessere
  Ergebnisse als „alles herausfinden“.
- **Zweck der Untersuchung** – eine von fünf Möglichkeiten: **Interoperabilität mit dem eigenen Gerät**,
  **Sicherheitsprüfung des eigenen Geräts**, **Fehlersuche an eigener Software**,
  **Sicherung eigener Funktionalität** oder **Sonstige erlaubte Untersuchung**.
- **Ich darf das Material untersuchen.** – ohne diesen Haken bleibt **Fall anlegen** gesperrt und es kann
  keine Analyse starten.
- **Herkunft und Berechtigung** – woher die Datei kommt und warum du sie untersuchen darfst.

### Artefakte aufnehmen
Ein Artefakt ist eine aufgenommene Datei. Angenommen werden:
- Windows-Programme (EXE, DLL),
- Android-Apps (APK),
- Linux- und Unix-Programme (ELF),
- Firmware-Abbilder,
- passive Netzwerk-Mitschnitte (PCAP, PCAPNG).

Die Werkstatt prüft den Inhalt der Datei, nicht nur die Endung. Eine umbenannte Datei wird dadurch nicht zu einem
anderen Typ. Zu jeder Datei zeigt sie Name, Typ, Größe und den SHA-256-Wert, der genau diese Datei kennzeichnet.

Zwei Wege führen in den Fall:
- **Datei hochladen** – bis zu fünf Dateien auf einmal.
- **Eingang prüfen** zeigt einen Eingangsordner in der Projektfreigabe und was darin liegt. Dort legst du große
  Dateien ab und holst sie mit **Eingang übernehmen** in den Fall. Übernommen werden nur normale Dateien direkt im
  Ordner, keine Unterordner und keine Verknüpfungen. Die Originale bleiben unverändert. Ändert sich eine Datei
  während der Übernahme, wird sie verworfen. Danach meldet die Seite, wie viele Dateien übernommen wurden, zum
  Beispiel „2 von 3 Dateien übernommen.“. Gründe für ausgelassene Dateien zeigt sie dabei nicht.

### Analysen starten
Unter jedem Artefakt erscheinen nur die Analysen, die zu seinem Typ passen. Sie sind in Gruppen geordnet:
**Überblick**, **Aufbau**, **Code und Abhängigkeiten**, **Netzwerk** und **Signaturen**.

- **Allgemein untersuchen** – für jede Datei, meist der erste Schritt.
- **Android-Paket untersuchen** und **APK-Signaturen prüfen** – bei Android-Apps.
- **Programm-Identität prüfen**, **.NET-Mitglieder und Zeichenketten prüfen**, **Windows-Imports prüfen**,
  **Windows-Ressourcen prüfen**, **TLS-Callbacks und Load-Config prüfen** und **Authenticode-Tabelle prüfen** –
  bei Windows-Programmen.
- **ELF-Notes und Build-ID prüfen** und **Kernelmodul-Metadaten prüfen** – bei Linux-Programmen.
- **Exporte prüfen**, **Go-Buildinfos prüfen** und **Rust-Abhängigkeiten prüfen** – bei Windows- und
  Linux-Programmen.
- **Firmware-Regionen prüfen** – bei Firmware. Zeigt mögliche Bereiche mit Position und Beschreibung, aber keine
  bestätigten Partitionen und keine herausgelösten Dateien.
- **Endpunkte, DNS und TLS prüfen** – bei Mitschnitten. Zeigt nur, was im aufgezeichneten Zeitraum zu sehen war.
- **Entropie und Packungsindikatoren prüfen** – für jede Datei, wenn du gepackte oder verschlüsselte Bereiche
  vermutest. Hohe Entropie ist ein Hinweis, kein Beweis.
- **Tiefenanalyse (Ghidra)** – langsamere Codeanalyse bei Windows-Programmen, Linux-Programmen und Firmware.

Wartende und laufende Aufträge stehen oben im Bericht mit **Wartet** oder **Läuft**, der Analyse und dem
Fortschritt in Prozent. Solange etwas wartet oder läuft, aktualisiert sich die Seite alle paar Sekunden von selbst.
Ist ein Auftrag fertig, verschwindet er aus dieser Liste und seine Befunde stehen im Bericht. Ein fehlgeschlagener
Auftrag erscheint als „Analyse fehlgeschlagen.“ mit seinem Fehlercode.

### Bericht lesen
Der **Bericht** hat fünf aufklappbare Abschnitte. Sie sagen, wie sicher eine Aussage ist:
- **Beobachtet** – direkt aus der Datei oder dem Mitschnitt gemessen.
- **Abgeleitet** – eine feste Regel verbindet mehrere Beobachtungen.
- **Vermutet** – eine plausible Annahme, kein Beweis.
- **Unbekannt** – was sich aus dem Material nicht beantworten lässt.
- **Nächste erlaubte Prüfung** – ein sicherer Folgeschritt.

Darunter steht das **Belegverzeichnis**: je Beleg eine Kennung, die Analyse, der Arbeitsschritt, die Sicherheit
der Aussage und das verwendete Werkzeug mit Version. Fehlgeschlagene Aufträge erscheinen mit ihrem Fehlercode.

## Mit Buddy und Agenten

Die Werkstatt bringt drei Werkzeuge mit. Sie sind nicht automatisch an: Du gibst sie einem Agenten bewusst in
seinen Einstellungen im Reiter **Tools & MCP**. Ein Agent kann sie nur nutzen, wenn sein Besitzer die Freigabe
**Agentenwerkzeuge der Zerlege-Werkstatt** hat. Die Werkzeuge arbeiten immer im Projekt, in dem der Agent gerade
läuft, und nur, wenn der Besitzer dieses Projekt sehen darf.

- `reverse_cases`: listet die Fälle des Projekts (bis zu 50) mit Titel, Ziel, Zweck und Zustand.
- `reverse_inspect`: startet eine Analyse an einer Datei, die schon im Fall liegt. Der Agent wählt nur die Art
  der Analyse. Sie muss zum Dateityp passen. Dafür braucht der Besitzer Schreibrechte im Projekt.
- `reverse_report`: liest den Bericht eines Falls mit Zustand und Fehlercode der Aufträge. Die Ausgabe ist
  begrenzt und als nicht vertrauenswürdiges Material gekennzeichnet.

Was du fragen kannst:
- „Welche Fälle gibt es in der Zerlege-Werkstatt?“
- „Starte beim Router-Fall die Firmware-Regionen-Prüfung und sag mir, wenn sie fertig ist.“
- „Fass mir den Bericht zusammen: Was ist beobachtet, was nur vermutet?“

Was nicht geht: Der Agent kann keine Fälle anlegen, keine Dateien hochladen oder aus dem Eingang übernehmen und
keine Dateipfade, Befehle oder Adressen angeben. Texte aus dem untersuchten Material sind nur Daten. Der Agent
soll darin enthaltene Anweisungen nicht befolgen.

## Gut zu wissen

- Nur erlaubtes Material: Untersuche nur Eigenes oder ausdrücklich Erlaubtes. Trage keine Passwörter, Tokens
  oder privaten Schlüssel in Titel, Frage oder Berechtigungsnotiz ein.
- Statisch heißt: Die Werkstatt führt nichts aus, verbindet sich nicht mit dem Gerät und schneidet keinen
  Verkehr live mit. Ein Fund zeigt, was in der Datei steckt, nicht was zur Laufzeit wirklich passiert. Ein Import
  oder eine Android-Berechtigung belegt eine Fähigkeit, nicht ihre Nutzung. Ein leerer Fund ist kein Gegenbeweis.
- Sicherheit: Die Analysen laufen in einem eigenen, unprivilegierten Container ohne Zugriff auf Geräte des
  Servers. Er hat nur bei der Installation Netz. Vor jeder Analyse wird es abgeschaltet. Es gibt nur fest
  vorgegebene Analysen, keine freien Befehle.
- Grenzen: höchstens 512 MiB je Datei und 2 GiB je Fall. Beim Hochladen höchstens fünf Dateien auf einmal.
  Liegen mehr als 50 Dateien im Eingangsordner, wird nichts übernommen. Ein Lauf hat ein festes Zeitlimit.
- Firmware: Als Firmware erkennt die Werkstatt derzeit nur Abbilder, die mit einem bestimmten Kennbyte
  beginnen. Andere Firmware-Dateien lehnt sie mit „Der Dateityp wird nicht unterstützt.“ ab.
- Reihenfolge: Es läuft immer nur eine Analyse zur selben Zeit, weitere warten. Dieselbe Analyse an derselben
  Datei startet nicht doppelt, solange sie noch wartet oder läuft. Wird der Server neu gestartet, während eine
  Analyse läuft, gilt sie als unterbrochen und wird nicht von selbst wiederholt. Starte sie dann einfach neu.
- Rechte: Fälle, Dateien und Analysen gehören zum Projekt. Ansehen geht mit Leserechten, Anlegen, Hochladen
  und Analysieren nur mit Schreibrechten. Projekte ohne Zugriff bleiben unsichtbar. Der Eingangsordner liegt in der
  Projektfreigabe, die sich alle Beteiligten des Projekts teilen.
- Typische Meldungen beim Hochladen:
  - „Der Dateityp wird nicht unterstützt.“ – keine passende Originaldatei. Umbenennen hilft nicht.
  - „Die Datei ist leer.“ oder „Der Fall ist voll.“ – leere Datei bzw. die 2 GiB des Falls sind erreicht.
  - „Diese Datei liegt schon im Fall.“ – eine Datei mit demselben SHA-256 ist schon da.
  - „Das Archiv ist zu groß oder zu stark komprimiert.“ – die APK ist zu groß, enthält zu viele Einträge oder ist
    auffällig stark gepackt.
- Meldungen als Fehlercode: Manche Fehler zeigt die Seite nur als technischen Code, zum Beispiel
  `reverse_artifact_too_many` (mehr als fünf Dateien auf einmal), `reverse_artifact_too_large` (Datei größer als
  512 MiB) oder `reverse_job_already_running` (diese Analyse läuft an dieser Datei schon).
- Laden schlägt fehl: Bei „Fälle konnten nicht geladen werden.“, „Der Fall konnte nicht geladen werden.“ oder
  „Der Bericht konnte nicht geladen werden.“ lädst du mit **Erneut versuchen** neu.

*Stand: Zerlege-Werkstatt 0.4.2, 22.11.2026*
