# Atelier – Bilder, Videos, Musik und Kurzfilme mit KI erzeugen

Das Atelier ist eine Medienwerkstatt mit KI. Hier entstehen Bilder, kurze Videoclips, Musik und ganze Kurzfilme,
alles in einem Projekt. Eigene Figuren mit Steckbrief und Referenzbildern sorgen dafür, dass dieselbe Figur in vielen
Bildern gleich aussieht.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Das Atelier braucht dafür auch das Modul
   Video-Editor.
2. Das Atelier arbeitet immer in einem Projekt. Hast du noch keins, lege zuerst unter **Projekte** eines an.
3. Öffne das **Atelier** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Medienstudio**).
4. Wähle oben rechts das **Projekt**.
5. Öffne den Reiter **Generieren**, beschreibe die Szene und klicke **Bild generieren**. Das fertige Bild erscheint
   in der **Galerie**.

## Was du damit machen kannst

Oben gibt es acht Reiter. Unter den Reitern erklärt ein blauer Kasten kurz den gerade offenen Reiter. Mit „–“ klappst
du ihn zu.

### Charaktere
- **Neue Figur** öffnet das Formular. Trage einen **Name** ein, dazu den Steckbrief (Aussehen, Merkmale), einen
  eigenen Stil-Anker, eine Farbpalette als Hex-Werte und auf Wunsch einen **Seed**. Mit **Anlegen** wird die Figur
  gespeichert. Ohne Namen geht das nicht.
- Der Steckbrief wird wörtlich in jeden Prompt übernommen, in dem die Figur vorkommt.
- **Referenzbilder**: Nach dem Anlegen lädst du mit **Bild hochladen** eigene Vorlagen hoch (PNG, JPG oder WebP,
  bis 15 MB). Das ist der stärkste Hebel für ein gleichbleibendes Aussehen. Genutzt werden höchstens 3 Bilder,
  weitere erscheinen blass.
- Ein Klick auf eine Figur in der Liste wählt sie aus (grüner Rahmen). Ausgewählte Figuren fließen in den Reiter
  **Generieren** ein. ✎ bearbeitet eine Figur, ✕ löscht sie nach einer Rückfrage.

### Generieren
- Oben steht, welche Figuren gewählt sind. Ohne Figur erscheint „Keine Figur gewählt — es wird nur nach CI + Szene
  generiert.“
- Beschreibe ins Textfeld nur die Szene, zum Beispiel „winkt am Strand, sonniger Tag“.
- **Stil-Look** setzt einen festen Stil, etwa **Fotorealistisch**, **Aquarell**, **Comic** oder **Pixel-Art**.
- Unter **Modell** wählst du das Bildmodell. Cloud-Modelle stehen in der Gruppe „Cloud · OpenRouter“, lokale Modelle
  auf eigener Grafikkarte in einer eigenen Gruppe. **Format** legt das Seitenverhältnis fest (1:1, 16:9, 9:16, 4:3,
  3:4). **Seed** ist freiwillig und wirkt nur bei manchen Modellen. Leer bedeutet zufällig.
- **Regie & Kamera** klappt Auswahllisten für **Kameraeinstellung**, **Objektiv / Brennweite**, **Licht**,
  **Wetter**, **Tageszeit** und **Stimmung / Look** auf. **Zurücksetzen** leert sie wieder.
- **Bild generieren** erzeugt das Bild. Danach springt das Atelier in die **Galerie**.

### Galerie
- Alle Bilder des Projekts. Die Ansicht stellst du mit **Klein**, **Mittel**, **Groß** oder **Liste** ein.
- Ein Klick öffnet die große Vorschau. Mit den Pfeilen blätterst du weiter. Rechts unter **Details** stehen der
  Prompt (mit **Prompt kopieren**), das Modell, der Seed und der Dateiname.
- **Als Referenz** übernimmt ein Bild als Referenzbild in eine Figur, die du danach auswählst.
- **Zu Video machen** öffnet das Video-Fenster mit diesem Bild als Startbild.
- **Wiederholen** übernimmt Szene, Figuren, Modell, Seed, Format, Kamera und Stil des Bildes in den Reiter
  **Generieren**. Dort kannst du alles noch ändern.
- **Löschen** entfernt ein Bild nach einer Rückfrage.

### Videos
- **Video aus Text** startet einen Clip ohne Startbild. Clips aus einem Bild startest du in der **Galerie**.
- Im Video-Fenster beschreibst du unter **Bewegung / Beschreibung**, was passieren soll, und wählst **Modell**,
  **Dauer** und **Format**. Die Auswahl passt sich dem Modell an, damit keine ungültige Kombination entsteht. Ohne
  Startbild ist eine Beschreibung Pflicht.
- **Endbild (optional)**: Mit Startbild und einem Modell, das das kann, bewegt sich das Video zu einem zweiten Bild.
  **Startbild als Endbild** ergibt eine Schleife.
- **Video erstellen** startet den Clip. Er braucht meist 1–2 Minuten. Die Liste aktualisiert sich von selbst.
- Jeder Clip zeigt Modell, Dauer, Format und ob er „aus Startbild“ oder „aus Text“ entstand. **Wiederholen** öffnet
  das Fenster mit denselben Einstellungen. **Fortsetzen** nimmt das letzte Bild des Clips als Startbild für einen
  Anschluss-Clip. Dieses Bild landet auch in der Galerie. 🗑️ löscht den Clip nach einer Rückfrage.

### Audio
- Links legst du **Sound-Profile** an (**Neues Profil**): einen Namen und eine Beschreibung mit Genre, Stimmung,
  Instrumenten und Tempo. Die Beschreibung wird wörtlich in jeden Prompt übernommen. Ein Klick wählt ein Profil aus.
- **Studio-Sound (CI)** ist der Klang, der für das ganze Projekt gilt. Er wird beim Verlassen des Feldes gespeichert.
- Unter **Szene** beschreibst du nur das, was diesmal anders ist. Optional wählst du ein **Modell**.
- **Musik generieren** erzeugt ein Stück, das dauert etwa 10–30 Sekunden. Es erscheint in der **Bibliothek** mit
  einem Abspieler.
- Das Atelier erzeugt hier nur Musik, keine Sprache.

### Filme
- Hier fügst du fertige Clips aus dem Reiter **Videos** zu einem Film zusammen. Klicke die Clips in der gewünschten
  Reihenfolge an. Die Nummer zeigt die Position.
- Wähle das Format (16:9, 9:16 oder 1:1). Clips mit anderem Format werden mit Rändern eingepasst.
- **Musik unterlegen** nimmt ein Stück aus der Audio-Bibliothek dazu.
- „Film rendern“ startet das Zusammensetzen. Fertige Filme lassen sich abspielen und löschen.

### Schnitt
- Hier ist der Video-Editor ins Atelier eingebaut. **Aus Projekt hinzufügen** holt Videos aus dem Projekt, auch die
  Atelier-Clips. **Video hochladen** lädt ein eigenes Video hoch.
- Ein Klick auf ein Video öffnet den Editor. Wie er funktioniert, steht in der Hilfe zum Video-Editor.

### Regie
Aus einem Drehbuch entsteht ein ganzer Film.
- **Drehbuch**: Titel, Logline (der Film in einem Satz) und eine allgemeine Beschreibung. Dazu **Film-Modell** (das
  Video-Modell), **Audio-Modell** (für die Musik), **Format** und **Standard-Dauer (Sek.)**. **Speichern** sichert
  den Kopf.
- **Szene hinzufügen** legt eine Szene an. Ein Klick auf den Titel klappt sie auf. Dort gibt es Titel,
  Beschreibung, **Ort**, **Tageszeit**, **Charaktere in dieser Szene**, **Dialoge** (mit **Dialog** eine Zeile
  hinzufügen: Figur, Text, **Emotion**), **Musik-Untermalung** und **Regie & Kamera**. **Szene speichern** sichert
  sie. Mit den Pfeilen änderst du die Reihenfolge, ✕ löscht die Szene.
- **An Regieagent senden**: Eine KI zerlegt jede Szene in einzelne Einstellungen (**Shots**) mit Kameraeinstellung,
  Prompt, Figuren und Dauer. Sie soll je Szene 2 bis 5 Shots planen. Dabei wird noch nichts erzeugt. Unter jeder
  Szene stehen dann die Shots. Den Prompt eines Shots kannst du ändern, ✕ löscht ihn.
- **Freigeben & generieren** rendert nach einer Rückfrage alle Shots: je Shot zuerst ein Bild, daraus ein Clip, am
  Ende ein Film. Ein Balken zeigt den Fortschritt, jeder Shot zeigt seinen Stand. Schlägt ein Shot fehl, läuft der
  Rest weiter. Der Film entsteht dann aus den fertigen Clips.
- Ist bei einer Szene **Musik-Untermalung** angehakt, wird beim Rendern Musik erzeugt und ab dieser Szene leise unter
  den Ton der Clips gelegt.

### Im Bereich Media
Unter **Media** in der Navigation gibt es einen geführten Ablauf mit den Schritten **Charaktere**, **Bild erzeugen**,
**Galerie**, **Videoclips** und **Film erstellen**. Dahinter stecken dieselben Atelier-Reiter.

## Mit Buddy und Agenten

Das Atelier bringt zehn Werkzeuge mit. Sie sind nicht automatisch an: Du gibst sie einem Agenten in seinen
Einstellungen im Reiter **Tools & MCP**. Ohne Angabe arbeiten sie im Projekt des Chats, sonst im genannten Projekt.
Erreichbar sind nur Projekte, in denen du Mitglied bist.

Nur lesen:

| Werkzeug | Was es tut |
|---|---|
| `atelier_projects` | listet deine Projekte und nennt das gerade aktive |
| `atelier_overview` | Überblick über ein Projekt: Projekt-Stil, Drehbuch-Kopf, Anzahl Figuren, Bilder und Szenen |
| `atelier_models` | listet die Modelle für Bild, Video, Musik oder Sprache, bei Video mit Dauern und Formaten |
| `atelier_characters` | listet die Figuren mit Steckbrief |
| `atelier_gallery` | listet die Bilder mit Prompt, Seed und Modell, auf Wunsch nur die neuesten |
| `atelier_scenes` | liest Drehbuch-Kopf und Szenen |

Voreinstellen (speichert nur Einstellungen):

| Werkzeug | Was es tut |
|---|---|
| `atelier_set_ci` | setzt den Stil des ganzen Projekts: Stil-Anker, Standard-Bildmodell, Format, Farbpalette |
| `atelier_character` | legt eine Figur an, ändert oder löscht sie |
| `atelier_scene` | legt Szenen an, ändert, löscht oder sortiert sie um |
| `atelier_set_screenplay` | setzt den Drehbuch-Kopf: Titel, Logline, Beschreibung, Modelle, Format, Dauer |

Das kannst du zum Beispiel fragen:
- „Lies mein Atelier und sag mir, was schon da ist.“
- „Welche Video-Modelle gibt es?“
- „Leg eine Figur ‚Lotte‘ an: rote Locken, gelber Regenmantel.“
- „Schreib mir ein Drehbuch mit drei Szenen für einen Kurzfilm über einen verlorenen Schlüssel.“

Den Stil für das ganze Projekt (Stil-Anker, Standard-Bildmodell, Standard-Format) stellst du derzeit nur über
`atelier_set_ci` ein. In der Oberfläche gibt es dafür kein Feld. Gewählte Werte erscheinen im Reiter **Generieren**
als „(Standard)“.

Was NICHT geht:
- Die Werkzeuge erzeugen nichts: keine Bilder, Videos, Musik und keinen Film. Zerlegen und Rendern startest du im
  Reiter **Regie** selbst.
- Referenzbilder hochladen, Bilder, Clips oder Filme löschen und Sound-Profile bearbeiten geht nur in der Oberfläche.
- Das Bildmodell und das Sprach-Modell, die ein Agent bei einer Figur bzw. im Drehbuch einträgt, werden gespeichert,
  beim Erzeugen aber derzeit nicht benutzt.

## Gut zu wissen

- Kosten: Bilder, Videos, Musik und das Zerlegen durch den Regieagenten rufen eine KI beim Anbieter auf. Ein Video
  ist deutlich teurer als ein Bild. **Freigeben & generieren** erzeugt viele Bilder und Videos auf einmal. Lokale
  Modelle auf eigener Grafikkarte kosten nichts beim Anbieter. Das Zusammensetzen im Reiter **Filme** läuft auf dem
  Server selbst und ruft keine KI auf.
- Zugriff: Es gibt keine eigene Freigabe. Jeder sieht nur die Projekte, in denen er Mitglied ist. Alles, was im
  Atelier entsteht, liegt im Projekt im Ordner „atelier“.
- Figuren: Ein Bild nutzt höchstens 6 gewählte Figuren und zusammen höchstens 3 Referenzbilder. Gibst du keinen
  Seed an, nimmt das Atelier den Seed einer gewählten Figur, falls eine einen hat.
- Videos: Höchstens 2 Videos entstehen gleichzeitig, weitere warten. Ein Endbild geht nur zusammen mit einem
  Startbild.
- Musik im Film: Legst du im Reiter **Filme** Musik unter, ersetzt sie den Ton der Clips. Der Film endet, sobald
  Bild oder Musik zu Ende ist.
- Regie:
  - Der fertige Regie-Film erscheint derzeit nicht im Reiter **Filme**. Du findest ihn im Reiter **Schnitt** über
    **Aus Projekt hinzufügen**. Dasselbe gilt für die Clips der einzelnen Shots, die nicht im Reiter **Videos**
    stehen. Die Bilder der Shots landen in der **Galerie**.
  - Den Film setzt das Atelier nur in 16:9, 9:16 oder 1:1 zusammen. Bei 4:3 oder 21:9 wird er als 16:9 ausgegeben.
  - Die **Standard-Dauer (Sek.)** wird gespeichert. Wie lang ein Shot wird, legt derzeit der Regieagent fest.
  - Dialoge helfen dem Regieagenten beim Planen. Vertont werden sie nicht.
  - Ist ein **Film-Modell** gewählt, gibt das Atelier es derzeit auch an den Regieagenten zum Zerlegen weiter.
    Kommen dabei „0 Shots“ heraus, stelle das **Film-Modell** zum Zerlegen auf „— Standard —“ und versuche es erneut.
- Der Knopf **Schnitt** in der großen Videoansicht hat derzeit keine Funktion. Nutze den Reiter **Schnitt**.
- Typische Fehlermeldungen:
  - „Keine Projekte vorhanden. Lege zuerst ein Projekt an.“ Lege unter **Projekte** eines an.
  - „Kein OpenRouter-API-Key konfiguriert.“ Für Cloud-Modelle muss ein Admin einen OpenRouter-Schlüssel eintragen.
  - „Regieagent fehlgeschlagen. Ist ein LLM-Modell konfiguriert?“ Für das Zerlegen braucht HydraHive ein
    eingerichtetes Sprachmodell.
  - „Prompt ist leer — Studio-Sound, Profil oder Szene angeben.“ Für Musik muss mindestens eines davon gefüllt sein.
  - „Video fehlgeschlagen“ oder „Rendern fehlgeschlagen“: Am Clip bzw. Film steht der Grund. Versuche ein anderes
    Modell oder später erneut.

*Stand: Atelier 1.8.1, 22.11.2026*
