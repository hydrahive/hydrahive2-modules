# VR (HydraVR) – die Meta Quest mit HydraHive verbinden

Dieses Modul verbindet die App HydraVR auf einer Meta Quest mit deinem HydraHive-Zugang. Du koppelst die Brille
einmal per QR-Code. Danach können deine Agenten auf deiner Brille etwas sagen, Hinweise zeigen, Apps öffnen und Film
oder Musik steuern.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Öffne **VR-Brillen** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Freizeit**).
3. Klicke **Brille koppeln**, gib bei **Name der Brille** einen Namen ein und klicke **QR-Code erzeugen**.
4. Öffne HydraVR in der Brille und tippe „📷 QR-Code scannen“ an. Schau den QR-Code ein paar Sekunden aus 30–60 cm
   Abstand an.
5. Nach kurzer Zeit erscheint die Brille in der Liste **Gekoppelte Brillen**.

## Was du damit machen kannst

### Brille koppeln
- Der Name ist zuerst „Quest 3“. Erlaubt sind bis zu 40 Zeichen: Buchstaben, Ziffern, Leerzeichen, Punkt,
  Bindestrich und Unterstrich.
- Neben dem QR-Code läuft ein Zähler: „gültig noch …, nur einmal verwendbar“. Ein Code gilt 10 Minuten und lässt
  sich nur ein einziges Mal einlösen. Darunter steht der Code auch als Text.
- Ist die Zeit um, steht statt des QR-Codes **Abgelaufen**. Mit **Neuer Code** erzeugst du einen neuen.
  **Schließen** blendet den Kasten aus.
- Der QR-Code enthält keinen Zugangsschlüssel, nur den Einmal-Code und die Adresse des Servers. Erst beim Einlösen
  bekommt die Brille einen eigenen Schlüssel. Sie arbeitet dann mit deinem Konto und deiner Rolle.
- Steht „Server-Zertifikat ist im QR hinterlegt – die Brille vertraut genau diesem Server.“ da, prüft die Brille
  das Zertifikat genau dieses Servers. Das passiert nur, wenn du das Cockpit über eine IP-Adresse oder einen
  Heimnetz-Namen geöffnet hast. Über eine öffentliche Adresse prüft die Brille ganz normal.

### Gekoppelte Brillen
- Die Liste zeigt jede deiner Brillen mit Namen und dem Zeitpunkt der Kopplung. Oben rechts steht, wie viele Brillen
  gerade verbunden sind („… verbunden“).
- **Entfernen** löscht eine Brille nach einer Rückfrage. Die Brille verliert sofort den Zugang und muss neu
  gekoppelt werden.
- Du siehst und verwaltest nur deine eigenen Brillen.

## Mit Buddy und Agenten

Das Modul bringt acht Werkzeuge mit. Sie wirken immer nur auf die Brillen des Nutzers, für den der Agent gerade
arbeitet. Hauptagenten bekommen sie nach der Installation automatisch.

| Werkzeug | Was es tut |
|---|---|
| `vr_status` | prüft, ob gerade eine Brille mit HydraVR verbunden ist |
| `vr_say` | lässt die Brille einen Text vorlesen (bis 2000 Zeichen) |
| `vr_notify` | zeigt eine Benachrichtigung mit Titel und Text im HydraVR-Hauptmenü |
| `vr_open_app` | öffnet eine HydraVR-App in einem der Büro-Fenster 1–8 |
| `vr_close_window` | schließt ein Büro-Fenster (1–8) |
| `vr_windows` | sagt, welche App in welchem Fenster liegt (letzte Meldung der Brille) |
| `vr_layout` | richtet das Büro auf einmal ein: Fenster 1, 2, 3 … bekommen die genannten Apps, die übrigen werden geleert |
| `vr_media` | steuert Film oder Tonstudio: abspielen, pausieren, stoppen, weiter, lauter, leiser |

Die Apps heißen für die Werkzeuge `chat`, `monitor`, `film`, `storyboard`, `music`, `book`, `tasks`, `desktop`,
`browser` und `code`.

Das kannst du zum Beispiel fragen:
- „Bin ich gerade in VR?“
- „Sag mir in der Brille Bescheid, wenn der Export fertig ist.“
- „Richte mir in VR den Arbeitsmodus ein: Chat, Monitor und Code.“
- „Pausiere den Film in der Brille.“

Was nicht geht:
- Kein Zugriff auf Kamera, Mikrofon oder Dateien der Brille.
- Keine Brillen anderer Nutzer.
- Ist HydraVR gerade nicht offen, kommt nichts an. Der Agent bekommt dann die Meldung „Keine VR-Brille verbunden —
  HydraVR ist bei diesem Nutzer gerade nicht offen. Nichts wurde zugestellt.“
- Hat die Brille noch keinen Fensterstand gemeldet, weiß `vr_windows` nicht, was offen ist.
- Nur Apps aus der Liste oben, höchstens 8 Fenster.

## Gut zu wissen

- Öffne das Cockpit zum Koppeln über die Adresse, unter der auch die Brille den Server erreicht. Diese Adresse
  landet im QR-Code.
- Pro Nutzer können höchstens 5 Codes gleichzeitig offen sein und höchstens 4 Brillen gleichzeitig verbunden sein.
- Hast du mehrere Brillen, geht jede Nachricht eines Agenten an alle, die gerade verbunden sind.
- Was die Agenten an die Brille schicken und welche Fenster offen sind, merkt sich der Server nur im Arbeitsspeicher.
  Gespeichert werden nur die Kopplungen und die Einmal-Codes, diese nur unkenntlich gemacht.
- Freigabe: Die Werkzeuge stehen unter **Freigaben** als „Eigene VR-Brille ansprechen“. Am Anfang dürfen alle sie
  nutzen. Ein Admin kann das dort einschränken.
- Das Modul ruft keine KI beim Anbieter auf. Kosten entstehen nur durch den Agenten selbst.
- Löst die Brille einen abgelaufenen oder schon benutzten Code ein, wird sie abgewiesen. Erzeuge dann mit
  **Neuer Code** oder **Brille koppeln** einen frischen Code.

*Stand: VR (HydraVR) 0.4.2, 22.11.2026*
