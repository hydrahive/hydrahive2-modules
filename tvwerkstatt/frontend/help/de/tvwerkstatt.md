# TV-Werkstatt – eigener Startbildschirm, weniger Werbung und Zusätze für Android-TV

Die TV-Werkstatt baut für Fernseher mit Android TV oder Google TV einen eigenen, geprüften Startbildschirm und
schiebt ihn auf das Gerät. Sie kann vorinstallierte Werbe- und Tracking-Apps abschalten, selbst installierte Apps
verwalten und Zusätze aus einem Katalog bauen. Alles Fremde läuft in einem abgeschotteten Bereich auf dem Server.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Danach steht **TV-Werkstatt** in der
   Navigation (Gruppe **Arbeiten**). Die Seite ist nur für Admins.
2. Öffne den Reiter **Bauumgebung**. Setze den Haken bei „Ich nehme die Lizenzbedingungen von Google für die
   Android-Werkzeuge an“ und klicke auf **Werkstatt einrichten**. Das lädt etwa 1 GB und dauert einige Minuten.
3. Schalte am Fernseher das Debugging über das Netzwerk ein. Trage ihn im Reiter **Geräte** unter
   **Fernseher hinzufügen** mit **Name** und **Adresse im Heimnetz** ein und klicke auf **Hinzufügen und prüfen**.
4. Der Fernseher fragt „Debugging zulassen?“. Bestätige mit der Fernbedienung, am besten mit „Immer zulassen“.
5. Wähle oben den Fernseher aus und öffne den Reiter **Desktop**. Klicke auf **1 · Bauen** und danach auf
   **2 · Auf den Fernseher schieben**.

## Was du damit machen kannst

Oben auf der Seite wählst du bei **Fernseher wählen** das Gerät, um das es gehen soll. Die Reiter **Desktop**,
**Entrümpeln**, **Apps** und **Zusätze** brauchen eine eingerichtete Werkstatt und einen eingetragenen Fernseher.
Sonst steht dort ein Hinweis, was zuerst zu tun ist.

### Desktop
Die Seite hat drei Spalten.
- Links stehen die Angaben zum Gerät (Modell, System, **Debugging**) und der **Stand auf dem Fernseher**:
  ob der Startbildschirm der Werkstatt oder das Original läuft, ob das **Aussehen** aktuell ist und wie viele
  Apps bekannt sind. Mit **Apps vom Fernseher lesen** holt die Werkstatt die Liste der Apps vom Gerät.
- In der Mitte siehst du eine Vorschau des Startbildschirms. Das ist kein echtes Bild vom Fernseher. Du kannst
  die Tageszeit **Morgen**, **Abend** oder **Nacht** umschalten. Darunter liegen die Knöpfe **1 · Bauen**,
  **2 · Auf den Fernseher schieben**, **Nur das Aussehen schieben** und **Zurück zum Original**.
- Rechts stellst du das **Aussehen** ein:
  - **Hintergrund je Tageszeit**: ein eigenes Bild je Tageszeit (JPEG, PNG oder WebP). Ohne Bild gilt die
    Hintergrundfarbe.
  - **Hintergrund abdunkeln** (0 bis 90 %) und **Kacheln pro Reihe** (4 bis 7).
  - Welche Apps in der Leiste stehen: per Ziehen oder mit den Pfeilen sortieren, mit dem Schalter herausnehmen,
    umbenennen. Unter **Weitere Apps** kannst du Apps **Ausblenden**.
  - **Speichern** merkt sich die Änderung, **Verwerfen** nimmt sie zurück.

**Nur das Aussehen schieben** bringt geänderte Einstellungen auf den Fernseher, ohne neu zu bauen. Der
Startbildschirm startet dabei kurz neu. Das geht nur, wenn der Startbildschirm der Werkstatt schon aktiv ist.

### Entrümpeln
Hier geht es um die vorinstallierten Apps.
- **Vom Fernseher lesen** holt die Liste. Die Werkstatt vergleicht sie mit den Listen von cleanyourtv für
  Fernseher mit derselben Firmware. Die Apps sind in Gruppen sortiert, z. B. „Tracking und Fernwartung“ oder
  „Werbung und Inhalte“.
- „Empfohlen“ ist, was die Mehrheit der passenden Listen abschaltet und keine davon bewusst anlässt.
  **Empfohlene anhaken** setzt die Haken dafür.
- **Ausgewählte abschalten** schaltet die angehakten Apps ab, **Wieder einschalten** schaltet sie wieder ein.
  **Alles zurück** schaltet alles wieder ein, was die Werkstatt auf diesem Fernseher abgeschaltet hat.
- Nach einem Firmware-Update prüfst du mit **Nach Update prüfen**, ob abgeschaltete Apps wieder an sind.

Abgeschaltet wird nur, gelöscht wird nichts. Vorher wird der Stand gesichert. Teile von Android und der
Startbildschirm sind gesperrt und bleiben an. Braucht der Fernseher eine gewählte App für Eingänge oder
Einstellungen, schaltet die Werkstatt gar nichts ab. Geht beim Abschalten etwas schief, schaltet sie alles aus
diesem Schritt wieder ein.

### Apps
- **Play Store am Fernseher**: Gib einen Suchtext ein und klicke auf **Suchen**. Der Play Store öffnet sich am
  Fernseher. Das Installieren bestätigst du dort mit der Fernbedienung, das lässt Google nur am Gerät zu.
- Darunter stehen die selbst installierten Apps, nachdem du **Vom Fernseher lesen** geklickt hast. Pro App gibt es
  **Im Store öffnen** und **Deinstallieren**. Beim Deinstallieren gehen die Daten der App auf dem Fernseher verloren.
- Vorinstallierte Apps stehen nicht hier, sondern unter **Entrümpeln**.

### Zusätze
- Mit **Katalog laden** holt die Werkstatt den Katalog der Zusätze aus cleanyourtv. Du kannst darin suchen und
  filtern (**Alle**, **Ohne Rechte**, **Bildschirmschoner**, **Installiert**).
- Jede Karte zeigt, welche Rechte der Zusatz verlangt. Gelb und Rot markieren Rechte, die mehr dürfen.
- **Bauen & installieren** baut den Zusatz aus dem Quelltext und spielt ihn auf. Das dauert beim ersten Mal etwa
  eine Minute. Danach gibt es **Neu bauen** und **Entfernen**.

Installationsskripte der Zusätze laufen nicht, und die Werkstatt vergibt keine Sonderrechte. Was ein Zusatz danach
noch braucht, steht in seiner Beschreibung.

### Geräte
Der Reiter hat zwei Bereiche.
- **Fernseher**: Fernseher eintragen, mit **Erneut prüfen** neu abfragen und **Entfernen**. Die Werkstatt zeigt,
  ob es Android TV oder Google TV ist, welches Android läuft und ob das Debugging offen ist. Beim Prüfen wird am
  Fernseher nur gelesen. Auch hier gibt es **Auf den Fernseher schieben** und **Zurück zum Original**.
- **HydraHive-App**: eine kleine App für Fernseher und Tablets, die sich mit HydraHive verbindet.
  - **App bauen** baut sie, **App herunterladen** lädt die fertige Datei herunter. Die Datei bringst du von Hand
    auf das Gerät und öffnest sie dort.
  - Zum Koppeln gibst du einen Namen ein und klickst auf **Code erzeugen**. Den Code tippst du zusammen mit der
    Adresse des Servers in der App ein. Er gilt 15 Minuten und nur einmal. Die App zeigt einen
    **Fingerabdruck**. Er muss genau so aussehen wie in der Werkstatt, sonst brichst du ab.
  - Gekoppelte Geräte zeigen „verbunden“ oder „nicht verbunden“. Mit **Schicken** kannst du eine Testmeldung mit
    **Knöpfe** senden. **Sperren** nimmt dem Gerät sofort den Zugang, danach kannst du es **Entfernen**.

### Bauumgebung
- **Bauumgebung**: Hier richtest du die Werkstatt ein, hältst sie mit **Anhalten** an oder baust sie mit
  **Werkstatt abbauen** ab. Beim Abbauen werden die Werkzeuge gelöscht, der Schlüssel zum Signieren bleibt
  gesichert. Die Werkstatt ruht, solange nichts gebaut wird.
- **Startbildschirm**: **Startbildschirm bauen** bzw. **Neu bauen** baut den Startbildschirm von cleanyourtv aus
  einem festen, geprüften Stand. Danach siehst du Version, Größe und Prüfsumme. **Protokoll anzeigen** zeigt den
  Ablauf. Ein Bau dauert etwa eine Minute, am Fernseher passiert dabei nichts.

## Gut zu wissen

- Nur für Admins: Die Seite und alle ihre Funktionen sind Admins vorbehalten. Werkzeuge für Buddy oder Agenten
  hat die TV-Werkstatt nicht.
- Container nötig: Ohne Container-Umgebung auf dem Server kommt der Hinweis „Auf diesem Server gibt es keine
  Container-Umgebung“.
- Abschottung: Der Bauraum darf ins Internet und nur zu den eingetragenen Fernsehern, nicht zum Server oder zu
  anderen Geräten zu Hause. Greift die Sperre nicht, bricht die Werkstatt ab.
- Adresse: Erlaubt ist nur eine einzelne Adresse im Heimnetz, nicht die des Servers selbst. Sonst kommt „Diese
  Adresse passt nicht zu einem Fernseher im Heimnetz.“
- Android-Version: Der Startbildschirm braucht mindestens Android 8.
- Zurück zum Original geht jederzeit: Beim Aufspielen wird der bisherige Startbildschirm nur abgeschaltet, nicht
  gelöscht.
- Google TV: Vor dem Aufspielen schaltet die Werkstatt Googles Einrichtungs-Helfer ab. Danach tun die Tasten
  YouTube und TV-Symbol auf der Fernbedienung nichts mehr. **Zurück zum Original** schaltet alles wieder ein.
  Gehört das gespeicherte WLAN diesem Helfer, stellt die Werkstatt nichts um. Dann am Fernseher das WLAN entfernen
  und neu verbinden.
- Geprüfte Quellen: Passen Quelle, Prüfsumme oder Unterschrift nicht, baut die Werkstatt nicht bzw. verwendet
  die App nicht.
- Hintergrundbilder: höchstens 15 MB je Bild und 30 Bilder je Fernseher.
- Typische Meldungen:
  - „Am Fernseher wurde „Debugging zulassen?“ nicht bestätigt.“ – **Erneut prüfen** und am Fernseher bestätigen.
  - „Der Fernseher antwortet nicht.“ – Ist er an und das Debugging über das Netzwerk eingeschaltet?
  - „Es läuft gerade schon etwas. Bitte kurz warten.“ – Warte, bis die laufende Aufgabe fertig ist.

*Stand: TV-Werkstatt 0.14.1, 22.11.2026*
