# Aufgaben – Aufgaben, die über alle Chats hinweg erhalten bleiben

Aufgaben ist eine einfache Aufgabenliste. Anders als ein Gedanke im Chat bleibt eine Aufgabe erhalten, auch wenn
du einen neuen Chat beginnst. Du kannst Aufgaben selbst anlegen und abhaken. Dein Agent kann das ebenfalls, zum
Beispiel wenn du im Gespräch sagst „das machen wir später“.

## So startest du

1. Das Modul gehört fest zu HydraHive. Fehlt es oder ist es beschädigt, richtet HydraHive es beim Start selbst
   wieder ein.
2. Öffne einen Chat mit einem Agenten. Rechts siehst du den Bereich **Workspace**. Ist er eingeklappt, klapp ihn
   auf.
3. Wähle dort den Reiter **Aufgaben**.
4. Klicke auf das „+“ (**Neuen Task anlegen**), gib einen Titel ein, wähle die Priorität und klicke auf
   **Hinzufügen**. Die Aufgabe erscheint sofort in der Liste.

## Was du damit machen kannst

### Liste und Filter
- Oben wählst du, was die Liste zeigt: **Alle**, **Offen**, **In Arbeit**, **Erledigt** oder **Abgebrochen**.
- Wichtige Aufgaben stehen oben: zuerst **Hoch**, dann **Mittel**, dann **Niedrig**. Innerhalb einer Priorität
  steht die älteste Aufgabe oben.
- Vor dem Titel zeigt ein kleines Zeichen die Priorität: „!“ für hoch, „~“ für mittel, „↓“ für niedrig. Hat eine
  Aufgabe eine Beschreibung, steht deren Anfang unter dem Titel.
- Die Liste aktualisiert sich alle paar Sekunden von selbst. Was dein Agent anlegt oder abhakt, siehst du also
  ohne Neuladen.
- Gibt es nichts zu zeigen, steht dort **Keine Aufgaben**.

### Neue Aufgabe
- Das „+“ öffnet ein kleines Formular. Gib einen Titel ein und wähle **Hoch**, **Mittel** (vorausgewählt) oder
  **Niedrig**.
- **Hinzufügen** legt die Aufgabe an, **Abbrechen** schließt das Formular.
- Im Formular gibt es nur Titel und Priorität. Eine Beschreibung oder ein Projekt vergibt hier nur dein Agent.

### Abhaken und Status ändern
- Das Kästchen links vor einer Aufgabe heißt **Als erledigt markieren**. Bei erledigten oder abgebrochenen
  Aufgaben heißt es **Wieder öffnen** und setzt sie zurück auf offen.
- Erledigte und abgebrochene Aufgaben erscheinen blasser und durchgestrichen.
- Fährst du mit der Maus über eine Aufgabe, erscheint rechts eine Auswahl für den Status: **Offen**,
  **In Arbeit**, **Erledigt** oder **Abgebrochen**.

### Löschen
- Der Mülleimer rechts (**Task löschen**) entfernt die Aufgabe sofort und endgültig. Es gibt keine Rückfrage.

### Verlauf
- Wurden Titel oder Beschreibung einer Aufgabe geändert, steht darunter **Verlauf** mit der Zahl der früheren
  Fassungen. Ein Klick klappt sie auf, jeweils mit Datum und Uhrzeit.
- Der Zusatz **aus Chat-Verlauf wiederhergestellt** zeigt eine Fassung, die nachträglich aus einem alten Chat
  zurückgeholt wurde.

### Herkunft aus einer Idee
- Ist eine Aufgabe aus einer Idee im Modul Ideen entstanden, steht darunter **Aus Idee**. Ein Klick öffnet diese
  Idee.

## Mit Buddy und Agenten

Das Modul bringt vier Werkzeuge mit. Hauptagenten bekommen sie automatisch. Die Werkzeuge gehören zu diesem
Modul, nicht zum Kern.

| Werkzeug | Was es tut |
|---|---|
| `task_write` | Legt eine Aufgabe an oder ändert eine bestehende: Titel, Beschreibung, Priorität, Status. Eine Notiz hängt einen Absatz mit Datum an die Beschreibung an. |
| `task_list` | Listet Aufgaben kurz auf, auf Wunsch nur einen Status oder ein Projekt. Höchstens 100 Aufgaben pro Abfrage, sonst 20. |
| `task_read` | Zeigt eine Aufgabe vollständig, auf Wunsch mit allen früheren Fassungen und der Herkunft. |
| `task_delete` | Löscht eine Aufgabe endgültig. |

Das kannst du zum Beispiel fragen:
- „Welche Aufgaben sind noch offen? Gib mir eine kurze Übersicht.“
- „Leg eine Aufgabe an: Rechnungen abheften, Priorität hoch.“
- „Setz die Aufgabe mit dem Drucker auf erledigt.“

Gut zu wissen:
- Agenten sollen Aufgaben von sich aus anlegen, etwa bei längeren Arbeiten oder wenn du sagst „vergiss nicht …“.
  Fortschritt halten sie als Notiz mit Datum fest.
- Ersetzt ein Agent die ganze Beschreibung, bleibt die alte Fassung im **Verlauf** erhalten.
- Arbeitet der Agent in einem Projekt, ordnet er neue Aufgaben diesem Projekt zu. Beim Auflisten sieht er dann
  nur die Aufgaben dieses Projekts, außer er fragt ausdrücklich nach einem anderen Projekt.
- Aufgaben werden über ihre Kennung angesprochen. Die ersten acht Zeichen reichen, solange sie eindeutig sind.
- Nicht verwechseln: Die kurze Arbeitsliste, die ein Agent nur für den laufenden Chat führt, ist etwas anderes.
  Sie gehört zum Kern und erscheint nicht unter **Aufgaben**.

## Gut zu wissen

- Jeder sieht nur seine eigenen Aufgaben. Auch Agenten erreichen nur die Aufgaben des Nutzers, für den sie
  gerade arbeiten.
- Die Liste unter **Aufgaben** zeigt alle deine Aufgaben, unabhängig vom Projekt.
- Ein Titel darf höchstens 500 Zeichen lang sein.
- Pro Aufgabe werden bis zu 200 frühere Fassungen aufbewahrt. Danach fallen die ältesten weg. Aus einem alten
  Chat wiederhergestellte Fassungen bleiben immer erhalten.
- Kennt dein HydraHive den Föderations-Katalog, meldet sich das Modul dort als Quelle an. Im Katalog erscheinen
  Titel, Status, Priorität und Projekt einer Aufgabe. Die Beschreibung gibt das Modul nur auf Abruf einer
  einzelnen Aufgabe heraus. Verlauf und Herkunft gibt es nicht an den Katalog.
- **Aufgaben konnten nicht geladen werden** erscheint, wenn die Liste nicht abgerufen werden kann. Lädt der
  Verlauf nicht, steht dort **Verlauf nicht ladbar**.

*Stand: Aufgaben 1.5.1, 22.11.2026*
