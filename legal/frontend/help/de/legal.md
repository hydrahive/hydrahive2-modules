# Recht – eigene Rechtsfälle ordnen, Gesetze nachlesen, Fristen rechnen

**Keine Rechtsberatung. Bei Fristen, Klagen und Unsicherheit: Anwalt oder Beratungsstelle.**

Recht hilft dir, einen eigenen Fall zu verstehen und vorzubereiten. Du liest Bundesgesetze im amtlichen Wortlaut,
legst je Fall eine Fallakte mit Beteiligten, Fristen, Schriftverkehr und Notizen an und lässt dir von einem
Rechts-Agenten zuarbeiten. Der Agent macht nur Vorschläge, verschickt nichts und ersetzt keine Anwältin und keinen
Anwalt.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Recht ist zunächst nur für Admins offen. Andere Nutzer gibt ein Admin unter **Freigaben** frei:
   **Recht nutzen (Gesetze suchen, eigene Fälle sehen)** und – wer selbst Fälle anlegen soll – zusätzlich
   **Recht: Fälle anlegen (je Fall ein Projekt mit Rechts-Agent)**.
3. Öffne **Recht** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Wissen & Recherche**).
   Recht liegt im **Vault**: Beim ersten Öffnen legst du eine Vault-PIN fest, danach gibst du sie zum Entsperren ein.
4. Im Reiter **Fälle** klickst du auf **Neuer Fall**, trägst mindestens die Pflichtfelder **Titel** und
   **Bundesland** ein und klickst **Fall anlegen**. Die Fallakte öffnet sich sofort.
5. Im Reiter **Gesetze** gibst du Fachbegriffe oder eine Norm wie „§ 536c BGB“ ein und klickst **Suchen**.

## Was du damit machen kannst

### Gesetze
- Gesucht wird in den lokal gespeicherten Bundesgesetzen. Die Kernliste umfasst 54 Gesetze in den Rubriken
  „Zivil- und Verfahrensrecht“, „Wohnen und Immobilien“, „Familie“, „Sozialrecht“, „Verwaltung“, „Strafrecht und
  Bußgeld“, „Arbeit, Steuer, Daten“ und „Grundlagen“. Vor der ersten Suche siehst du, wie viele davon geladen sind.
- Wörter aus dem Gesetz treffen besser als Alltagssprache – „Mangel Mietsache Anzeige“ statt „Wohnung zu heiß“.
  Eine genaue Normbezeichnung öffnet die Norm direkt. Findet die Suche nichts, steht dort „Keine Treffer. Andere
  Fachbegriffe versuchen.“
- Ein Klick auf einen Treffer zeigt rechts den Wortlaut mit Absätzen und Aufzählungen, den Stand des Gesetzes und
  das Abrufdatum. **Zitat kopieren** legt die Normbezeichnung in die Zwischenablage, **Amtliche Fassung** öffnet die
  Norm auf gesetze-im-internet.de.
- Unten steht, wann zuletzt abgeglichen wurde. Die Gesetze werden kurz nach dem Start geladen und danach etwa einmal
  am Tag mit gesetze-im-internet.de abgeglichen. Admins können mit **Jetzt abgleichen** sofort abgleichen.

### Fälle
- Jeder Fall ist ein eigenes Projekt mit einem eigenen Rechts-Agenten. Die Liste zeigt **Fall**, **Status**,
  **Nächste Frist** und **Geändert**; mit **Öffnen** kommst du in die Fallakte. Du siehst deine Fälle und die, in
  deren Projekt du Mitglied bist; Admins sehen alle Fälle. Hast du noch keinen, steht dort „Noch keine Fälle.“
- Die Ampel vor einer Frist ist rot, wenn die Frist vorbei ist oder in höchstens 3 Tagen endet, gelb bei höchstens
  14 Tagen und grün, wenn sie später endet.
- **Neuer Fall**: Pflicht sind **Titel** und **Bundesland** (das Bundesland entscheidet über die Feiertage bei Fristen).
  Freiwillig sind **Rechtsgebiet**, **Was ist passiert? (kurz)**, **Sachverhalt im Detail**,
  **Was willst du erreichen?** und **Aktenzeichen der Gegenseite**. Darunter steht, welches Modell der
  Rechts-Agent nutzt. Es kommt aus einem Agenten-Template, das ein Admin unter LLM → Agenten-Templates ändert. Auf
  einem Server ohne Agenten-Templates wählst du das Modell hier selbst.

### Fallakte
Oben stehen Titel, Rechtsgebiet und Bundesland. Mit Schreibrecht änderst du dort den Status (**offen**, **wartet**,
**erledigt**) und öffnest den Chat mit **Mit dem Rechts-Agenten sprechen**. **Alle Fälle** führt zurück zur Liste.
Die Akte hat diese Reiter:

- **Übersicht**: Kurzfassung, Sachverhalt, Ziel und Aktenzeichen.
- **Beteiligte**: Personen und Stellen mit **Rolle** (zum Beispiel Gegenseite, Anwalt/Anwältin, Behörde, Gericht,
  Zeuge/Zeugin, Ich / wir), **Name** (Pflicht), **Anschrift** und **Kontakt**; mit **Hinzufügen** speichern. Der
  Beteiligte „Ich / wir“ wird in Briefen zum Absender.
- **Fristen**: Unter **Frist rechnen** gibst du an, **Wofür** die Frist gilt, den **Ereignistag (Zugang)**, die
  **Art** (Tage, Wochen, Monate, Jahre oder bestimmter Tag), die **Anzahl** und den **Beginn**. **Rechnen** zeigt das
  Fristende mit Wochentag und dem Rechenweg nach §§ 187, 188 und 193 BGB samt Feiertagen des Bundeslands. Erst
  **In die Akte übernehmen** speichert die Frist. Gespeicherte Fristen markierst du als erledigt oder löschst sie;
  ein Klick auf das Datum zeigt den Rechenweg erneut.
- **Schriftverkehr**: alle Schreiben in einer Liste, eingehend und ausgehend.
  - **Neuer Brief** öffnet die Brief-Werkstatt: **Vorlage** und **Empfänger** wählen, **Gerüst einsetzen** füllt
    den Brief aus der Akte. Es gibt sechs Vorlagen: Mangelanzeige mit Fristsetzung (Miete), Mahnung / Fristsetzung
    zur Zahlung oder Leistung, Widerspruch gegen einen Bescheid, Kündigung (Vertrag), Bitte um Akteneinsicht und
    Anschreiben an den eigenen Anwalt. Danach bearbeitest du Absender, Empfänger, Datum, **Zustellweg**, Zeichen,
    Betreff, Text und Anlagen.
  - Die **Prüfliste** daneben prüft ohne KI, ob Absender und Empfänger mit Anschrift, Datum, Betreff, Aktenzeichen,
    eine Frist als Datum in der Zukunft, belegte Normen, Zustellweg und Anlagen vorhanden sind. Sie blockiert
    nichts, sie zeigt nur, was fehlt. Genannte Normen werden gegen die gespeicherten Gesetze geprüft.
  - **Als Entwurf speichern** legt den Brief ab. Die **Druckansicht** zeigt ihn im Format DIN 5008 Form B; gelb
    markierte Platzhalter in eckigen Klammern füllst du vor dem Druck. **Drucken / als PDF speichern** öffnet den
    Druckdialog des Browsers.
  - Hast du den Brief selbst verschickt, trägst du über **versendet …** Datum, Versandweg und einen Nachweis (zum
    Beispiel eine Sendungsnummer) ein und klickst **Eintragen**. Danach ist der Brief gesperrt und lässt sich nicht
    mehr ändern oder löschen.
  - **Eingang erfassen**: eingegangene Schreiben mit Datum, Absender, Betreff und Inhalt abtippen oder kurz
    zusammenfassen. Hochladen gibt es nicht.
- **Notizen**: Recherche-Ergebnisse des Agenten und eigene Notizen mit **Notiz speichern**. Genannte Normen erhalten
  ein ✓, wenn sie in den gespeicherten Gesetzen vorkommen, sonst ein ? („nicht im Korpus – prüfen!“).
- **Vorschläge**: Was der Rechts-Agent ablegen möchte – Beteiligte, Fristen, Tatsachen und Briefe. Erst mit
  **Übernehmen** steht es in der Akte, mit **Verwerfen** nicht. Eine übernommene Tatsache wird an den Sachverhalt
  angehängt, ein übernommener Brief landet als Entwurf im Schriftverkehr. Die Zahl offener Vorschläge steht am Reiter.

## Mit Buddy und Agenten

Jeder Fall hat einen eigenen Rechts-Agenten. Du sprichst mit ihm über **Mit dem Rechts-Agenten sprechen** in der
Fallakte; der Chat öffnet sich daneben und wird beim nächsten Mal fortgesetzt. Dein Buddy bekommt die
Recht-Werkzeuge nicht automatisch.

Der Rechts-Agent kann:
- die Fallakte lesen (`legal_case`),
- Normen suchen und im Wortlaut holen (`legal_search`, `legal_norm`), auch in einer früheren Fassung, sofern sie
  gespeichert ist,
- Fristen mit Rechenweg rechnen (`legal_deadline`),
- Beteiligte, Fristen, Tatsachen und Briefe als Vorschlag ablegen (`legal_propose_party`, `legal_propose_deadline`,
  `legal_propose_fact`, `legal_propose_letter`),
- Recherche-Ergebnisse als Notiz festhalten (`legal_note`),
- Briefe aus einer Vorlage aufsetzen und prüfen (`legal_letter_draft`, `legal_check_letter`),
- im Web suchen und sein Gedächtnis nutzen.

Fragen kannst du zum Beispiel: „Welche Norm gilt, wenn ich einen Mangel in der Mietwohnung melden muss?“,
„Rechne mir die Frist für den Widerspruch, der Bescheid kam am Montag an“ oder „Schreib mir eine Mangelanzeige an
die Gegenseite“.

Was nicht geht:
- Der Agent ändert die Akte nie selbst. Alles außer Notizen kommt als Vorschlag, den du übernimmst oder verwirfst.
- Er verschickt nichts – keine Briefe, keine Mails. Er hat keine Werkzeuge, die nach außen wirken, und keinen
  Zugriff auf Dateien.
- Der Fristenrechner beachtet keine Sonderregeln (zum Beispiel ZPO oder Zustellung).
- Mit nur Leserecht im Fall kann der Agent keine Vorschläge oder Notizen ablegen.

## Gut zu wissen

- **Keine Rechtsberatung.** Recht zeigt Wortlaut, rechnet und ordnet. Bei Klagen, Strafsachen, hohen Beträgen oder
  laufenden gerichtlichen Fristen gehört der Fall zu einer Anwältin, einem Anwalt oder einer Beratungsstelle.
- Fristen ohne Gewähr: Jede Berechnung endet mit dem Hinweis, Fristbeginn (Zugang!), Sonderregeln und Feiertage am
  Erklärungsort selbst zu prüfen und im Zweifel früher zu handeln. Gibt es einen Feiertag nur in einzelnen
  Gemeinden, weist der Rechner darauf hin.
- Vault: Recht ist nur mit entsperrtem Vault erreichbar. Nach 15 Minuten ohne Nutzung sperrt der Vault wieder.
- Gespräche, in denen der Rechts-Agent die Fallakte liest oder etwas in ihr ablegt, gelten als privat. Agenten,
  die nur normale Inhalte sehen dürfen, finden sie im Gedächtnis nicht.
- Zugriff: Wer einen Fall sieht, regelt die Mitgliedschaft im Projekt. Mit nur Leserecht lassen sich Akte und Chat
  nicht ändern („Nur Leserechte in diesem Fall.“).
- Wird das Projekt eines Falls gelöscht, verschwindet auch der Fall. Nach 30 Tagen wird die Fallakte auf dem Server
  gesichert und danach gelöscht.
- Typische Meldungen:
  - „Dafür fehlt die Freigabe „Recht: Fälle anlegen“.“ – ein Admin muss die Freigabe erteilen.
  - „Fall nicht gefunden oder kein Zugriff.“ – du bist nicht Mitglied im Projekt des Falls.
  - „Diese Frist lässt sich so nicht rechnen (Art/Anzahl prüfen).“
  - „Über diesen Vorschlag wurde schon entschieden.“

*Stand: Recht 0.5.1, 22.11.2026*
