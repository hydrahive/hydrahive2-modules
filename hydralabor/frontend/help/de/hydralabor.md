# Hydra-Labor – sicher an HydraHive mitbauen, ohne den eigenen Server zu gefährden

Im Hydra-Labor arbeitet ein eigener Agent am Code von HydraHive, und zwar in einem abgeschotteten Container.
Deinen Server und dein Heimnetz erreicht er von dort nicht. Du siehst das Ergebnis als Probe im Browser und kannst
Änderungen und Fehler über dein GitHub-Konto einreichen. Das hilft allen, die HydraHive verbessern wollen, ohne Git
oder Programmieren zu können.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Das Labor dürfen nur Admins nutzen.
2. Öffne **Hydra-Labor** in der Navigation (Gruppe **Arbeiten**). Ein Assistent führt dich durch drei Schritte.
3. **1. Voraussetzungen**: Klicke auf **Prüfen**. Jeder Punkt bekommt ein Häkchen oder ein Kreuz mit dem Grund.
4. **2. Modell und Größe**: Wähle bei **Modell für den Labor-Agenten** ein Modell und lege **Prozessorkerne**,
   **Arbeitsspeicher (MB)** und **Speicherplatz (GB)** fest. Voreingestellt sind 2 Kerne, 4096 MB und 20 GB.
5. **3. Labor anlegen**: Klicke auf **Labor anlegen**. Das dauert etwa 2–5 Minuten, du kannst die Seite währenddessen
   verlassen. Ein Balken und eine Liste zeigen den Fortschritt.
6. Steht dort **Dein Labor ist bereit.**, klicke auf **Zum Labor-Chat** und beschreibe, was du bauen oder reparieren
   möchtest.

## Was du damit machen kannst

### Labor anlegen
**Labor anlegen** lässt sich erst klicken, wenn alle Voraussetzungen erfüllt sind, ein Modell gewählt ist und die Größe
passt. Erlaubt sind 1–64 Kerne, 1024–262144 MB Arbeitsspeicher und 10–2000 GB Platz. Ändert sich die Größe, musst du
neu prüfen. Beim Anlegen richtet das Labor unter anderem ein abgeschottetes Netz ein, holt den Code von HydraHive,
richtet eine Testumgebung ein, legt einen Sicherungspunkt „frisch“ an und zuletzt ein Projekt mit dem Labor-Agenten.
Bricht ein Schritt ab, steht dort **Abgebrochen bei:** mit dem Schritt, und der Knopf heißt **Noch einmal versuchen**.

### Zum Labor-Chat
**Zum Labor-Chat** öffnet auf der Projekt-Seite das Projekt „Hydra-Labor“ mit dem Labor-Agenten. Der Agent
arbeitet nur im Labor und lässt vor jedem „fertig“ die Tests laufen.

### Labor steuern
Oben steht **Labor läuft** oder **Labor ist aus**, darunter die Größe und wann die Sperre zuletzt geprüft wurde.
- **Starten** / **Stoppen**: schaltet den Container ein oder aus.
- **Testlauf**: lässt die Tests von HydraHive im Labor laufen (nur wenn das Labor läuft). Das dauert einige Minuten.
  Danach steht dort zum Beispiel **Alle Tests grün** oder wie viele Tests rot und grün sind, mit der Liste der roten.
- **Sperre prüfen**: testet aus dem Labor heraus, ob dein Server, das Heimnetz und Tailscale wirklich gesperrt sind und
  ob die Namensauflösung fürs Internet geht.
- **Zurücksetzen**: bringt das Labor auf den frischen Stand nach dem Anlegen. Alles, was seitdem im Labor geändert wurde,
  ist danach weg. Chats bleiben erhalten. Vorher kommt die Frage **Labor zurücksetzen?**.
- **Labor entfernen**: löscht Labor-Bereich, Labor-Projekt mit Agent und Chats. Zur Bestätigung tippst du `LABOR` ein
  und klickst auf **Endgültig entfernen**. Das lässt sich nicht rückgängig machen.

### Probe ansehen
Hier siehst du dein Labor als eigenes HydraHive im Browser, mit eigener Anmeldung und leeren Daten.
1. **Probe bauen** (dauert etwa eine Minute). Ist die Probe gebaut, heißt der Knopf **Neu bauen**. Damit holst du
   Änderungen aus dem Labor in die Probe.
2. **Probe starten**.
3. Die Seite zeigt **Benutzer** und **Passwort** für die Anmeldung an der Probe. Mit **Kopieren** übernimmst du das
   Passwort.
4. **Probe öffnen** öffnet die Probe in einem neuen Tab. Mit **Probe stoppen** hältst du sie wieder an.

Ist das Labor aus, steht dort **Das Labor ist aus. Bitte zuerst starten.**

### GitHub
Zum Einreichen und Melden verbindest du ein GitHub-Konto. Ohne GitHub geht alles andere trotzdem.
1. Klicke auf **Mit GitHub verbinden**. Die Seite zeigt einen Code.
2. Klicke auf **GitHub öffnen**, gib dort den Code ein (**Code kopieren** hilft) und bestätige.
3. Danach steht dort **Verbunden als** mit deinem GitHub-Namen. Mit **Trennen** löst du die Verbindung. Den Zugang
   kannst du auch in den **GitHub-Einstellungen** entfernen.

Noch kein Konto? Der Link **Konto anlegen** führt zur Anmeldung bei GitHub.

### Änderung einreichen
Ist das Labor bereit und GitHub verbunden, erscheint **Änderung einreichen**. Du wählst bei **Wofür?** zwischen
**HydraHive selbst** und **Module**, gibst einen **Titel (kurz, worum geht es?)** ein und schreibst bei
**Was ändert sich und warum? (2–3 Sätze)** ein paar Sätze. **Prüfen und einreichen** startet diese Schritte:
Änderungen prüfen, Tests laufen lassen, deine Kopie bei GitHub vorbereiten, Änderungen hochladen, Vorschlag anlegen.
Am Ende steht ein Link zum Vorschlag. Das HydraHive-Projekt sieht ihn sich an und übernimmt ihn oder schreibt dir
zurück.

### Fehler melden
**Fehler melden** öffnet ein kurzes Formular: **Wofür?**, **Kurz: Was geht nicht?**, **Was ist passiert?**,
**Was hast du erwartet?** und **Wie kommt man dahin? (Schritte)**. **Melden** legt die Meldung bei GitHub an und zeigt
den Link dazu.

### Meine Einreichungen
Hier stehen deine Änderungen und Fehlermeldungen mit ihrem Stand: **eingereicht**, **übernommen** oder
**abgeschlossen**. **Stand abfragen** holt den neuesten Stand von GitHub.

## Mit Buddy und Agenten

Hydra-Labor gibt Buddy und anderen Agenten keine eigenen Werkzeuge. Gearbeitet wird im Labor-Chat.

Der Labor-Agent wird vom Modul angelegt und verwaltet. Seine Werkzeuge sind fest: Dateien lesen und schreiben, Befehle
ausführen, im Web suchen, in der Hilfe nachlesen, sich Notizen merken und eine Aufgabenliste führen. Alle Befehle und
Dateien laufen im Container, nicht auf dem Server. Eingeschaltet sind nur die Skills „labor-review“, „test“,
„debugging“ und „code-review“. Vor dem Abschluss geht er die Prüfliste „labor-review“ durch.

Was der Agent nicht kann:
- den Server, das Heimnetz oder Tailscale erreichen (das Internet geht),
- Befehle mit Administratorrechten ausführen,
- Webseiten mit Zugangsdaten des Servers abrufen,
- selbst etwas bei GitHub ändern. Eingereicht wird nur über den Knopf **Änderung einreichen**.

## Gut zu wissen

- **Nur Admins:** Seite und Schnittstellen sind nur für Admins. Sonst erscheint „Das dürfen nur Admins.“
- **Voraussetzungen:** Auf dem Server muss die Container-Verwaltung incus ab Version 6.0 laufen. Geprüft werden außerdem
  freier Speicherplatz (gewählte Größe plus 10 GB Puffer), freier Arbeitsspeicher und ob HydraHive aktuell genug ist.
- **Modell:** Hat das Agenten-Template „Hydra-Labor“ (unter LLM → Agenten-Templates) ein Modell, ist nur dieses wählbar,
  sonst alle eingerichteten Chat-Modelle.
- **Sperre wirkt nicht:** Findet **Sperre prüfen** einen Weg zu Server oder Heimnetz, wird das Labor sofort
  ausgeschaltet. Dann steht dort „Achtung: Die Sperre wirkt nicht …“.
- **Probe:** Sie läuft auf Port 8443 und ist nur aus dem Heimnetz und über Tailscale erreichbar. Geöffnet wird sie über
  einen Einmal-Link, der 60 Sekunden gilt. Die Anmeldung gilt danach 8 Stunden. Ist sie abgelaufen, wähle erneut
  **Probe öffnen**.
- **GitHub-Zugang:** Das Labor fragt bei GitHub nur das Recht für öffentliche Projekte an. Gibt GitHub mehr Rechte, wird
  der Zugang aus Sicherheitsgründen nicht gespeichert. Gespeichert wird er verschlüsselt. Es gibt eine Verbindung für das
  ganze Labor. Mit dem Konto, dem HydraHive gehört, ist Einreichen nicht nötig.
- **Einreichen:** Vorher prüft das Labor:
  - höchstens 50 Dateien und 3000 Zeilen auf einmal,
  - nichts, was wie ein Passwort oder Schlüssel aussieht,
  - keine geschützten Bereiche, die nur das HydraHive-Projekt selbst ändert (z. B. automatische Prüfungen,
    Installation, Prüfskripte, Lizenz),
  - alle Tests grün.

  Schlägt etwas fehl, nennt die Meldung die betroffenen Dateien oder Tests.
- **Fehler melden:** Mitgeschickt werden nur die Versionen von HydraHive und dem Labor sowie das Betriebssystem. Keine
  Protokolle, keine Daten. Passwörter im Text werden entfernt.
- **Typische Meldungen:**
  - „Gerade läuft schon ein Vorgang. Bitte kurz warten.“ – es läuft schon ein Testlauf, eine Prüfung o. Ä.
  - „Der letzte Vorgang wurde unterbrochen (z. B. durch einen Neustart). Bitte noch einmal starten.“
  - „Ein Einrichtungsschritt ist gescheitert (oft: kein Internet).“
  - „GitHub bremst gerade. Bitte in einer Stunde noch einmal.“

*Stand: Hydra-Labor 0.4.2, 22.11.2026*
