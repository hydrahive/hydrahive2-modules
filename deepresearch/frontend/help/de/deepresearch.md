# Deep Research – gründliche Web-Recherche mit zitiertem Bericht

Deep Research beantwortet eine Frage nicht in einem Satz, sondern recherchiert sie im Web in mehreren Runden. Am
Ende steht ein ausführlicher, bebilderter Bericht auf Deutsch, der seine Quellen direkt am jeweiligen Fakt nennt.
Das hilft bei Überblicken, Vergleichen, Kaufberatungen, Anleitungen und Faktenchecks.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Danach können es alle angemeldeten
   Nutzer verwenden.
2. Öffne **Deep Research** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich
   **Wissen & Recherche**).
3. Schreib links in das Feld „Worüber soll recherchiert werden?“ deine Frage. Sie braucht mindestens 3 Zeichen.
4. Klicke auf **Recherche starten** oder drücke Strg+Enter (am Mac Cmd+Enter).
5. Rechts läuft der Fortschritt mit. Ist der Lauf fertig, erscheint dort der Bericht.

## Was du damit machen kannst

### Frage und Einstellungen
Unter dem Eingabefeld stellst du vor dem Start drei Dinge ein:
- Modell: **Standard-Modell** oder ein bestimmtes KI-Modell aus der Liste. Kostenlose Modelle sind mit
  „gratis“ markiert.
- **Tiefe**: **Schnell · 3**, **Standard · 6** oder **Tief · 8**. Die Zahl ist die höchste Zahl an Suchrunden.
  Ab der zweiten Runde prüft die KI nach jeder Runde, ob das Material reicht, und hört dann früher auf.
- **Kategorie**: **Auto-Kategorie** lässt die KI selbst einordnen. Oder du gibst die Form des Berichts vor:
  **Produkt** (Optionen, Pro und Contra, Empfehlung), **Vergleich** (Tabelle mit Kriterien, dann Fazit),
  **How-to** (Schritt-für-Schritt-Anleitung mit Voraussetzungen), **Faktencheck** (Behauptung, Belege,
  Einordnung) oder **Allgemein** (gegliederter Übersichtsartikel).

### Der Fortschritt
Während des Laufs siehst du oben deine Frage, darunter, was gerade passiert, und die vergangene Zeit:
„Plane Recherche-Strategie …“, „Suche · … Queries“, „Liest: …“ mit dem Titel der Seite, „Analysiere · … Funde“
und zuletzt „Schreibe Bericht …“. Eine Grafik und ein Balken zeigen den Fortgang. Darunter stehen die Zahlen für
Runde, Quellen und Funde. Die Seite aktualisiert sich von selbst. Du kannst sie verlassen und später
wiederkommen, der Lauf geht auf dem Server weiter.

Es läuft immer nur eine Recherche gleichzeitig, auch über alle Nutzer hinweg. Startest du eine zweite, steht dort
„In Warteschlange …“, bis sie an der Reihe ist.

### Deine Recherchen
Links unter dem Knopf stehen deine bisherigen Läufe, die neuesten oben. Ein Zeichen vor jeder Frage zeigt den
Stand: ⏳ wartet, ⋯ läuft, ✓ fertig, ✕ fehlgeschlagen.
- Mit **Alle**, **Läuft** und **Fertig** filterst du die Liste. **Fertig** zeigt auch fehlgeschlagene Läufe.
- Ein Klick auf eine Frage öffnet den Lauf.
- Fährst du mit der Maus über einen Eintrag, erscheint rechts ein ✕ (**Löschen**). Ein Klick entfernt den Lauf
  sofort, ohne Rückfrage.
- Löschen hält einen laufenden Lauf nicht an. Er verschwindet aus der Liste, rechnet im Hintergrund aber zu Ende
  und hält so lange die Warteschlange besetzt.

Du siehst nur deine eigenen Recherchen. Die Liste zeigt die letzten 50.

### Der Bericht
Ein fertiger Lauf zeigt rechts den Bericht. Er beginnt mit einer Zusammenfassung und endet mit einem Fazit.
Dazwischen gibt es Abschnitte je Teilaspekt, wo es passt auch Tabellen. Die Quellen stehen als Links direkt im
Text. Oben im Bericht stehen Dauer, Runden, Suchanfragen, Zahl der Quellen und das verwendete Modell. Am Rand
führt ein Inhaltsverzeichnis durch die Abschnitte. Die Bilder stammen aus den gefundenen Quellen. Am Ende listet
**Quellen** alle verwendeten Seiten auf.

Über dem Bericht stehen drei Knöpfe:
- **Als PDF** öffnet den Bericht in einem neuen Fenster und ruft den Druckdialog auf. Dort wählst du „Als PDF
  speichern“.
- **HTML laden** speichert den Bericht als einzelne Datei, die du auch ohne HydraHive öffnen kannst.
- **Im neuen Tab öffnen ↗** zeigt den Bericht groß in einem eigenen Tab.

Im Bericht selbst steht oben rechts noch ein Knopf „⤓ Export ▾“. Innerhalb von HydraHive reagiert er nicht. Nimm
dafür die drei Knöpfe darüber.

## Mit Buddy und Agenten

Das Modul bringt ein Werkzeug mit: **research_report**. Es macht dasselbe wie der Knopf **Recherche starten**:
planen, in mehreren Runden suchen, Seiten auswerten und einen zitierten Bericht schreiben.
- Buddy und die anderen Haupt-Agenten bekommen das Werkzeug nach der Installation automatisch, spätestens nach
  dem nächsten Neustart von HydraHive. Andere Agenten nur, wenn es ihnen zugeteilt wird.
- Du kannst zum Beispiel sagen: „Recherchiere, welche Wärmepumpen für ein Reihenhaus infrage kommen“ oder
  „Mach mir einen Bericht über …“. Für eine einzelne schnelle Info nimmt der Agent besser die normale Websuche.
- Der Agent wartet, bis der Bericht fertig ist, und bekommt dann den ganzen Text, die Quellen und die Zahlen
  zurück. So kann er direkt mit dem Ergebnis weiterarbeiten.
- Der Lauf wird unter deinem Konto gespeichert. Du findest ihn danach auch auf der Seite Deep Research.

Was nicht geht:
- Tiefe und Kategorie kann der Agent nicht wählen. Er recherchiert immer mit bis zu 6 Runden und Auto-Kategorie.
  Nur das Modell kann er vorgeben.
- Frühere Recherchen auflisten, öffnen oder löschen kann der Agent nicht.
- Läuft gerade eine andere Recherche, muss auch der Agent warten.

## Gut zu wissen

- Dauer: Ein Lauf braucht meist einige Minuten. Nach 15 Minuten beginnt keine neue Suchrunde mehr. Die
  laufende Runde und der Bericht werden aber noch fertig.
- Suche: Deep Research sucht über die SearXNG-Suche, die ein Admin unter **Globale Einstellungen** im Reiter
  „Websuche“ als „SearXNG-URL“ einträgt. Fehlt sie oder ist sie nicht erreichbar, findet der Lauf nichts. Der
  Bericht sagt dann „Keine verwertbaren Quellen gefunden.“ und nennt, falls Seiten gelesen wurden, warum sie nicht
  passten. Die Ersatzsuche Tavily der normalen Websuche nutzt Deep Research nicht.
- Modell: Bei **Standard-Modell** nimmt Deep Research die Modelle, die ein Admin auf der LLM-Seite im Reiter
  **Agenten-Templates** beim Template „Recherche“ hinterlegt hat. Fällt ein Modell aus, springt das nächste der
  Kette ein. Wählst du selbst ein Modell, gilt nur dieses.
- Kosten: Ein Lauf ruft das KI-Modell oft auf: für den Plan, für jede gelesene Seite, für jede Runde und für
  den ausführlichen Bericht. Bei bezahlten Modellen kostet das entsprechend. Bei Modellen mit „gratis“ in der
  Liste fallen keine Modellkosten an.
- Datenschutz: Deine Frage und die daraus gebildeten Suchbegriffe gehen an die Suche. Der Server ruft die
  gefundenen Seiten selbst ab. Frage und Seiteninhalte gehen an das gewählte KI-Modell, bei einem Cloud-Modell
  also an dessen Anbieter. Deine Läufe sieht nur dein Konto.
- Quellen prüfen: Der Bericht soll nur sagen, was die Quellen hergeben, und Lücken offen benennen. Bei
  wichtigen Themen trotzdem die verlinkten Quellen kurz gegenlesen.
- Fehlermeldungen:
  - „Das ausgewählte KI-Modell ist nicht korrekt konfiguriert.“ – Das gewählte Modell ist nicht richtig
    eingerichtet. Ein anderes Modell wählen oder einen Admin fragen.
  - „Die Recherche ist fehlgeschlagen – bitte erneut versuchen.“ – Unterwegs ist etwas schiefgegangen. Einfach
    neu starten.
  - „Durch Neustart abgebrochen – bitte neu starten“ – HydraHive oder das Modul wurde neu gestartet, während der
    Lauf wartete oder lief. Die Frage neu stellen.
  - „Bericht konnte nicht geladen werden: …“ – Der Bericht ließ sich nicht abrufen. Seite neu laden.

*Stand: Deep Research 1.2.1, 22.11.2026*
