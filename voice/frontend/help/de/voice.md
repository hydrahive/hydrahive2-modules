# Voice – dein Sprachassistent zum Anfassen

Voice verbindet eine Voicebox (Home Assistant Voice PE) mit HydraHive.
Du sagst „OK Nabu …“, HydraHive erkennt deine Sprache, ein KI-Agent antwortet, und die Box spricht die Antwort.
Auf der Seite **Voicebox** siehst du den Verlauf, kannst auch tippen und stellst Box, Sprachmodell und Stimme ein.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Ein Admin installiert die Sprachdienste: **System** → Reiter **Erweiterungen** → **Zusatz-Module** →
   **Voice (Sprache rein/raus)** → **Installieren** → **Jetzt installieren**. Fehlen Container, nennt die Rückfrage,
   was vorher mitinstalliert wird.
3. Voice ist ab Start nur für Admins freigegeben (**Start: nur Admin**). Andere Nutzer gibt ein Admin unter
   **Freigaben** bei **Voice-Box nutzen** frei (**benutzen**).
4. Öffne **Voice** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Kommunikation**).
5. Ist die Box verbunden, steht rechts unter **Status** bei **Gerät** „**Verbunden**“. Sag „OK Nabu …“ – dein
   Gespräch erscheint in der Mitte.

## Was du damit machen kannst

### Voicebox
In der Mitte steht, was du zur Box gesagt hast (**Du**) und was sie geantwortet hat (**Voicebox**), jeweils mit
Uhrzeit. Der Verlauf aktualisiert sich alle paar Sekunden von selbst. Einträge zu Musik und Medien tragen die
Markierung ♪ **Medien**. Ist noch nichts da, steht dort „Sag „OK Nabu …“ — dein gesprochener Verlauf erscheint hier.“

Unten kannst du auch tippen statt sprechen: Nachricht eingeben und mit Enter oder dem Knopf **Senden**
(Papierflieger) abschicken. Die Antwort erscheint nur im Verlauf, die Box bleibt dabei still. Eine Nachricht darf
höchstens 2000 Zeichen lang sein. Klappt das Senden nicht, erscheint „Konnte nicht gesendet werden.“

### Einstellungen
Links stellst du die Box selbst ein. Änderungen gehen sofort an die Box:
- **Lautstärke** (0 bis 100 %)
- **Stumm**
- **Wake-Sound**
- **Wake-Word-Empfindlichkeit**: **Niedrig**, **Mittel** oder **Hoch**
- **LED-Ring** an oder aus; ist er an, regelst du darunter die **Helligkeit**

Geht etwas schief, steht dort „Speichern fehlgeschlagen. Bitte erneut versuchen.“ und die Seite holt den echten
Stand der Box zurück.

### Sprachmodell
Hier legst du fest, welches KI-Modell in deinen Gesprächen über die Box antwortet. Vorgabe ist
**Standard des Agenten** – das Modell deines Buddys. Wählst du ein anderes Modell, steht darunter „Eigenes Modell
für die Voicebox aktiv.“ Das gilt nur für die Sprach-Gespräche, dein normaler Chat mit Buddy bleibt unverändert.
Die Auswahl ist erst möglich, wenn du einmal mit der Box gesprochen hast („Erst nach dem ersten Gespräch wählbar.“).

### Spracherkennung (STT)
Zeigt, welches Whisper-Modell deine Sprache erkennt. Umstellen lässt es sich hier nicht – das geht nur auf dem
Server mit Adminrechten. Ist der Dienst nicht da, steht dort „STT-Dienst nicht erreichbar.“

### Stimme
Wähle, womit die Box spricht:
- **Lokal**: eine feste Stimme (Piper/Thorsten), die auf deinem Server läuft – offline und schnell.
- **Cloud**: Unter **TTS-Modell** wählst du ein Sprachmodell (oder das **Standardmodell**). Bringt das Modell
  mehrere Stimmen mit, wählst du darunter die **Stimme**. Die Liste der Cloud-Modelle kommt von OpenRouter.

### Status
Rechts siehst du, ob die **Bridge** (der Sprachdienst auf dem Server) **Läuft** oder **Offline** ist und ob das
**Gerät** **Verbunden** oder **Getrennt** ist. Der Status wird alle 5 Sekunden neu abgefragt.

### Voicebox einrichten
Erreicht HydraHive den Sprachdienst der Box (die Bridge) nicht, zeigt die Seite statt Verlauf und Einstellungen **Voicebox einrichten** mit den
drei Schritten **Firmware aufspielen**, **Mit WLAN verbinden** und **Mit HydraHive koppeln**. Diese Schritte sind
hier nur beschrieben, bedienen lässt sich davon nur der Knopf **Verbindung erneut prüfen**. Ist deine Box schon
eingerichtet und trotzdem nicht erreichbar, wende dich an deinen Admin.

## Gut zu wissen

- Eine Box, ein Besitzer: Verlauf, Geräte-Einstellungen, Tippen und die Stimmen-Auswahl sind nur für Admins und
  für den Besitzer der Box da. Wer der Besitzer ist, ist auf dem Server hinterlegt. Für alle anderen zeigt die
  Seite **Voicebox einrichten**, auch wenn die Box läuft.
- Kein Zugriff? Fehlt die Freigabe **Voice-Box nutzen**, sperrt HydraHive den Bereich („Kein Zugriff“).
- Breiter Bildschirm nötig: Einstellungen, Sprachmodell, Stimme und Status stehen in den Seitenspalten. Die
  sieht man nur auf einem breiten Bildschirm, auf schmalen Bildschirmen und Handys nur den Verlauf.
- Was bleibt lokal? Spracherkennung und die Stimme **Lokal** laufen auf deinem Server, ohne Cloud. Stellst du bei
  **Stimme** auf **Cloud**, spricht ein Cloud-Dienst. Ohne hinterlegten OpenRouter-Schlüssel ist die Cloud-Liste
  leer. Die Antwort selbst kommt vom gewählten **Sprachmodell** – je nach Modell also auch aus der Cloud.
- Aufweckwort: Die Box hört auf „OK Nabu“.
- Typische Meldung: „Die Voice-Bridge ist nicht erreichbar. Läuft der Bridge-Dienst?“ – dann antwortet der
  Sprachdienst auf dem Server nicht. Ein Admin muss ihn prüfen.

*Stand: Voice 0.8.7, 22.11.2026*
