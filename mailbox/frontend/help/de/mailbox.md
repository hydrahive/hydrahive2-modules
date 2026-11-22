# Mailbox – alle Mailkonten an einem Ort, mit vollständigem Archiv

Mailbox ist das Webmail von HydraHive. Du liest und schreibst Mails aus mehreren Konten an einer Stelle. Jede Mail
wird zusätzlich im lokalen Archiv abgelegt. Wird sie später auf dem Mailserver gelöscht, bleibt die Kopie erhalten
und ist weiter durchsuchbar. Auf Wunsch dürfen Agenten in freigegebenen Konten suchen, lesen und Entwürfe anlegen.

## So startest du

1. Ein Admin installiert das Modul unter **Module**. Danach dürfen es zuerst nur Admins nutzen. Das Recht
   „Mailbox nutzen (eigene Mailkonten, Webmail, Archiv)“ kann ein Admin unter **Freigaben** an andere vergeben.
2. Öffne **Mailbox** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Kommunikation**).
3. Klicke auf **Erstes Konto hinzufügen** und trage unter **Mailadresse** deine Adresse ein. Bei bekannten
   Anbietern füllt Mailbox die Serverdaten selbst aus und zeigt bei Bedarf einen Hinweis, zum Beispiel dass Gmail
   ein App-Passwort braucht.
4. Wähle die Anmeldung:
   - **Passwort**: Passwort eintragen und **Speichern**. Mailbox prüft dabei die Anmeldung.
   - **Microsoft (Outlook, Hotmail, Microsoft 365)**: Klicke auf **Mit Microsoft anmelden**. Mailbox zeigt eine
     Seite und einen Code. Öffne die Seite, melde dich an und gib den Code ein, das geht auch am Handy. Danach
     legt Mailbox das Konto selbst an.
5. Danach holt Mailbox alle Ordner und alle Jahre ins Archiv. Bei großen Postfächern kann das Stunden dauern. Den
   Fortschritt siehst du links unter dem Kontonamen.

## Was du damit machen kannst

### Konto hinzufügen
- Weitere Konten fügst du links unten mit **Konto hinzufügen** hinzu.
- Unter **Server-Einstellungen** prüfst oder änderst du **Name des Kontos**, **Benutzername**, **IMAP-Server**
  und **SMTP-Server** samt **Port**. Bei unbekannten Anbietern klappt dieser Teil von selbst auf.
- Microsoft-Konten brauchen einmal eine eigene App bei Microsoft. Fehlt sie, steht im Dialog, dass die
  Microsoft-Anmeldung noch nicht eingerichtet ist. Ein Admin richtet sie über das Schlüssel-Symbol oben ein
  (**Microsoft-Anmeldung einrichten**). Der Dialog führt durch die Schritte bei Microsoft Entra. Dann trägt der
  Admin die **Anwendungs-ID (Client)** und das **Verzeichnis** ein und klickt auf **Speichern und prüfen**. Das
  gilt danach für alle Nutzer.

### Die Ordnerleiste
- **Alle Posteingänge** zeigt die Posteingänge aller Konten zusammen.
- Unter jedem Konto stehen seine Ordner. Ein Klick auf den Kontonamen klappt sie auf oder zu. Mailbox merkt sich
  das in diesem Browser.
- Der farbige Punkt zeigt den Zustand: **verbunden**, **noch nicht abgeglichen**, **Anmeldung fehlgeschlagen**
  oder **Fehler beim Abgleich**.
- Der Kreispfeil (**Jetzt abrufen**) gleicht das Konto sofort ab. Das Zahnrad öffnet die Kontoeinstellungen.
- **Entwürfe** enthält deine gespeicherten Entwürfe.
- **Nur im Archiv** zeigt Mails, die es auf dem Server nicht mehr gibt.

### Mails lesen
- Klicke in der mittleren Liste auf eine Mail, sie öffnet sich rechts.
- Externe Bilder lädt Mailbox zum Schutz vor Verfolgung zunächst nicht. Mit **Bilder laden** zeigst du sie für
  diese Mail. Mit **Nur Text** und **HTML-Ansicht** wechselst du die Darstellung.
- Anhänge stehen unter dem Kopf der Mail. Über **.eml** lädst du die ganze Mail als Datei herunter.
- Liegt eine Mail nur noch im Archiv, steht dort **Auf dem Server gelöscht – nur noch im Archiv.** Antworten geht
  trotzdem.

### Suchen
- Das Suchfeld oben durchsucht alle Mails im Archiv, über alle Konten und Jahre.
- Filter schreibst du direkt ins Feld: `von:`, `an:`, `betreff:`, `hat:anhang`, `vor:` und `nach:` mit Datum
  (JJJJ-MM-TT), `konto:`, `ordner:` und genaue Wörter in Anführungszeichen. Beim Tippen schlägt das Feld die
  Filter vor.
- Steht neben dem Feld **Suche nur in Betreff/Kopf**, fehlt auf dem Server die Volltextsuche. Dann wird der
  Mailtext nicht durchsucht.

### Mails bearbeiten
- Über der geöffneten Mail: **Als gelesen markieren** bzw. **Als ungelesen markieren**, **Markieren** bzw.
  **Markierung entfernen**, **Verschieben nach …** und **Löschen**.
- Mehrere Mails hakst du in der Liste an, oben gibt es **Alle auswählen**. Dann erscheint eine Leiste mit
  **Als gelesen markieren**, **Markieren**, **Archivieren**, **Spam** und **Löschen**. Mails, die nur im Archiv
  liegen, werden dabei übersprungen.
- **Löschen** fragt nach und verschiebt die Mail in den Papierkorb des Mailservers. Im Papierkorb heißt der Knopf
  **Endgültig vom Server löschen**. Die Kopie im Archiv bleibt in beiden Fällen, die Mail steht danach unter
  **Nur im Archiv**.

### Schreiben, antworten, Entwürfe
- **Neue Mail** öffnet das Schreibfenster. Unter **Von** wählst du das Konto. Dazu gibt es **An**, **Cc/Bcc**,
  **Betreff**, **Text** und **Anhang**.
- Bei einer geöffneten Mail: **Antworten**, **Allen antworten** und **Weiterleiten**. Beim Weiterleiten einer Mail
  mit Anhängen kannst du **Anhänge des Originals mitsenden** anhaken.
- Anhänge dürfen zusammen höchstens 25 MB groß sein.
- Während du schreibst, speichert Mailbox den Entwurf nach ein paar Sekunden selbst. Du kannst auch
  **Entwurf speichern** oder **Verwerfen**. Steht dort **Entwurf nur lokal gespeichert**, liegt er nur in
  HydraHive und nicht im Entwürfe-Ordner des Servers. Eigene Anhänge werden im Entwurf nicht gespeichert.
- Nach **Senden** zeigt Mailbox, ob die Kopie im Gesendet-Ordner liegt, ob der Anbieter sie selbst ablegt oder ob
  sie nur im Archiv steht. Abgelehnte Empfänger werden einzeln genannt.

### Kontoeinstellungen
- Das Zahnrad am Konto öffnet die **Kontoeinstellungen**: **Absendername** und **Signatur**. Die Signatur setzt
  Mailbox beim Senden unter jede Mail (nach „-- “). Mit **Speichern** übernehmen.
- Bei Microsoft-Konten steht hier **Microsoft-Anmeldung**. Ist die Anmeldung abgelaufen, meldest du dich hier neu
  an. Das Archiv bleibt erhalten.
- Darunter stehen die **Freigaben für Agenten** (siehe unten).
- **Konto entfernen** entfernt nur den Zugang. Die archivierten Mails bleiben im Archiv und in der Suche.

### Benachrichtigungen und Tastenkürzel
- Die Glocke oben (**Benachrichtigen bei neuer Mail**) schaltet Browser-Meldungen ein. Der Browser fragt einmal
  nach Erlaubnis. Die Meldung nennt nur die Zahl neuer Mails, keinen Absender und keinen Betreff.
- Tasten: `j`/`k` blättern, `r` antworten, `a` allen antworten, `f` weiterleiten, `e` archivieren, `#` löschen,
  `/` suchen, `c` neue Mail. Solange das Schreibfenster offen ist oder du in einem Feld tippst, sind sie aus.

## Mit Buddy und Agenten

Agenten sehen ein Mailkonto nur, wenn du es freigibst. Ohne Freigabe finden die Mailbox-Werkzeuge nichts.

### Konto freigeben
1. Öffne mit dem Zahnrad die Kontoeinstellungen.
2. Wähle unter **Freigaben für Agenten** bei **Projekt wählen …** ein Projekt oder **Mein Buddy (ohne Projekt)**.
3. Wähle die **Stufe** und klicke auf **Freigeben**:
   - **lesen**: suchen, Mails lesen und Anhänge in den Arbeitsordner holen.
   - **Entwurf**: zusätzlich Entwürfe anlegen, Mails verschieben und markieren.
4. Die Stufe stellst du später in der Liste um. Der Mülleimer (**Freigabe entfernen**) nimmt sie zurück. Wird das
   Konto entfernt, verschwinden auch seine Freigaben.

Beim Freigeben bekommt der Projekt-Agent des Projekts die passenden Werkzeuge von selbst, bei **Entwurf** auch die
Entwurfs-Werkzeuge. Nimmst du die letzte Freigabe des Projekts zurück, werden sie wieder entfernt. Seine anderen
Werkzeuge bleiben unverändert. Spezialisten bekommen die Werkzeuge nicht von selbst.

### Wer darf was?
- Freigeben kann nur der Besitzer des Kontos, und nur in Projekte, in denen er Mitglied ist.
- Ein Agent sieht das Konto nur, wenn er für ein Mitglied dieses Projekts arbeitet.
- **Mein Buddy (ohne Projekt)** gilt nur für deinen eigenen Buddy außerhalb von Projekten.

### Die Werkzeuge

| Werkzeug | Stufe | Wofür |
|---|---|---|
| `mailbox_accounts` | lesen | freigegebene Konten und ihre Ordner |
| `mailbox_search` | lesen | suchen mit denselben Filtern wie im Suchfeld, höchstens 50 Treffer auf einmal |
| `mailbox_read` | lesen | eine Mail als Text lesen, lange Texte in Abschnitten, mit Liste der Anhänge |
| `mailbox_attachment` | lesen | einen Anhang im Arbeitsordner unter `mailbox-anhaenge/` speichern, bis 25 MB, ohne zu überschreiben |
| `mailbox_draft` | Entwurf | Entwurf anlegen oder einen eigenen ändern, auch als Antwort oder Weiterleitung |
| `mailbox_move` | Entwurf | Mails in einen anderen Ordner desselben Kontos verschieben |
| `mailbox_flag` | Entwurf | gelesen/ungelesen setzen, markieren oder Markierung entfernen |

Du kannst zum Beispiel fragen: „Such mir die letzte Rechnung mit Anhang heraus und leg das PDF ab“ oder „Schreib
einen Antwortentwurf auf die Mail von gestern“.

### Was nicht geht
- Agenten senden nie und löschen nie. Einen Entwurf prüfst und sendest du selbst.
- Ein Agent ändert nur Entwürfe, die ein Agent im selben Projekt angelegt hat. Deine eigenen Entwürfe fasst er
  nicht an.
- Entwürfe eines Agenten stehen bei dir unter **Entwürfe** mit dem Kennzeichen **Agent**. Prüfe Empfänger und
  Text, bevor du sendest.
- Mailtext ist fremder Text. Der Agent bekommt ihn ausdrücklich als Fremdinhalt markiert und soll Anweisungen
  darin nie befolgen.
- Jeder Zugriff wird protokolliert: wann, wer, welches Werkzeug, Ergebnis, ohne Mailinhalt. Die letzten Einträge
  siehst du in den Kontoeinstellungen unter **Letzte Agenten-Zugriffe**.
- Die allgemeinen Werkzeuge `read_mail` und `send_mail` gehören nicht zur Mailbox und nutzen diese Konten nicht.

## Gut zu wissen

- Archiv: Mailbox löscht im Archiv nie etwas. Löschen, Verschieben und Markieren ändern nur den Mailserver.
- Neue Mails: Mailbox hält die Verbindung offen und holt neue Mails meist sofort. Zusätzlich gleicht sie alle
  5 Minuten ab.
- Versandgrenze: Je Konto und Stunde ist die Zahl der Sendungen begrenzt. Ist sie erreicht, steht dort
  **Versandgrenze je Stunde erreicht – bitte später erneut senden**.
- Datenschutz: Gespräche, in denen ein Agent Mailbox-Werkzeuge benutzt, zählen im Langzeitgedächtnis zur
  Stufe „privat“.
- Typische Meldungen beim Senden:
  - **Anmeldung beim Postausgangsserver abgelehnt**: Passwort bzw. App-Passwort prüfen.
  - **Postausgangsserver nicht erreichbar** oder **Verschlüsselung/Zertifikat abgelehnt**: SMTP-Server und Port
    unter **Server-Einstellungen** prüfen.
  - **Text zu lang (höchstens etwa 1 MB) – bitte als Anhang senden**.
- Konto bleibt leer: Der erste Abgleich läuft vielleicht noch. Schau auf den Fortschritt unter dem Kontonamen
  oder klicke auf **Jetzt abrufen**.
- Agent findet keine Mails: Prüfe, ob das Konto für genau dieses Projekt freigegeben ist. Für Verschieben,
  Markieren und Entwürfe braucht es die Stufe **Entwurf**.

*Stand: Mailbox 0.7.4, 22.11.2026*
