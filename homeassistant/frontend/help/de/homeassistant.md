# Home Assistant – dein Smart Home in HydraHive sehen und schalten

Das Modul verbindet HydraHive mit deinem Home Assistant. Du siehst deine Geräte mit ihrem aktuellen Zustand und
schaltest Lampen, Schalter und Ventilatoren, ohne die Home-Assistant-App zu öffnen. Auf Wunsch fragt auch dein Agent
Zustände ab oder steuert Geräte für dich.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Ein Admin trägt unter **Globale Einstellungen** im Reiter **Home Assistant** zwei Werte ein:
   - „Home-Assistant-URL“: die Adresse deiner Home-Assistant-Instanz, ohne `/api` am Ende.
   - „Long-Lived Access Token“: einen Zugangsschlüssel, den du in Home Assistant unter Profil → Sicherheit →
     „Long-Lived Access Tokens“ erstellst.

   Ein Wert wird gespeichert, sobald du das Feld verlässt. Ist der Schlüssel gespeichert, zeigt das Feld nur noch
   „(gesetzt)“.
3. Öffne **Home Assistant** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich
   **Zuhause & Privat**).
4. Klappt die Verbindung, erscheint ein grünes Band „Verbunden mit …“ mit dem Namen deines Zuhauses und der
   Home-Assistant-Version. Darunter stehen deine Geräte.

## Was du damit machen kannst

### Geräte sehen
- Die Geräte sind nach Art gruppiert, zum Beispiel **Lampen**, **Schalter**, **Heizung & Klima**,
  **Rollos & Türen**, **Medien**, **Szenen**, **Sensoren** oder **Kontakte & Melder**. Steuerbares steht oben,
  Sensoren und technische Helfer weiter unten. Arten ohne deutschen Namen erscheinen mit ihrem englischen Kürzel aus
  Home Assistant.
- Jede Gruppe zeigt die Zahl ihrer Geräte. Ein Klick auf die Überschrift klappt sie auf oder zu. Beim ersten Öffnen
  der Seite sind die Gruppen zugeklappt.
- Jede Zeile zeigt den Namen, darunter die genaue Kennung (`entity_id`, zum Beispiel `light.wohnzimmer`) und rechts
  den Zustand. Werte mit Einheit stehen mit Einheit da, etwa „21.5 °C“. Sonst liest du „an“, „aus“, „offen“, „zu“,
  „nicht verfügbar“ oder „unbekannt“.
- **Aktualisieren** oben rechts lädt alle Geräte und Zustände neu.

### Suchen und filtern
- Im Suchfeld **Gerät suchen (Name oder entity_id)…** filterst du nach Name oder Kennung. Das „x“ rechts im Feld
  leert die Suche.
- Unter dem Suchfeld stehen Knöpfe: **Alle**, **Favoriten** (nur wenn du welche hast) und je ein Knopf pro Geräteart
  mit Anzahl. Ein Klick zeigt nur diese Auswahl.
- Passt nichts, steht dort **Keine passenden Geräte gefunden.**

### Schalten
- Lampen, Schalter, Ventilatoren, virtuelle Schalter, Automationen, Skripte und Sirenen haben rechts einen
  Schiebeschalter (**Einschalten** bzw. **Ausschalten**). Ein Klick schaltet um. Danach liest HydraHive den neuen
  Zustand dieses Geräts nach.
- Alle anderen Arten zeigen nur ihren Zustand an, auch Heizung, Rollos, Szenen und Schlösser. Die lassen sich auf
  dieser Seite nicht bedienen.
- Schalten dürfen nach der Installation nur Admins (siehe „Gut zu wissen“).

### Favoriten
- Der Stern links in einer Zeile setzt ein Gerät auf deine Favoritenliste (**Zu Favoriten**) oder nimmt es wieder
  herunter (**Aus Favoriten**).
- Ohne Suche und Filter stehen deine **Favoriten** oben als eigene Liste. Der Knopf **Favoriten** zeigt nur sie.
- Favoriten sind persönlich. Jeder sieht nur seine eigenen. Pro Person sind bis zu 100 Favoriten möglich. Klappt das
  Speichern nicht, springt der Stern zurück.

## Mit Buddy und Agenten

Das Modul bringt vier Werkzeuge mit. Buddy und Master-Agenten bekommen sie automatisch. Anderen Agenten kann man sie
in ihren Werkzeugen zuschalten.

- `ha_list_entities` listet Geräte mit Zustand, auf Wunsch nur eine Art (etwa Lampen) oder passend zu einem
  Suchwort. Es zeigt höchstens 200 Geräte auf einmal.
- `ha_get_state` liest ein einzelnes Gerät mit Zustand und Angaben wie Helligkeit, Temperatur oder Akkustand.
- `ha_render_template` lässt Home Assistant eine Vorlage auswerten (bis 2000 Zeichen), zum Beispiel „wie viele
  Lampen sind gerade an?“.
- `ha_call_service` schaltet und steuert: Licht an oder aus, Helligkeit, Thermostat auf eine Temperatur, Szene
  aktivieren. Damit geht mehr als mit dem Schiebeschalter auf der Seite.

So kannst du fragen:
- „Welche Lampen sind gerade an?“
- „Wie warm ist es im Wohnzimmer?“
- „Mach das Licht im Wohnzimmer aus.“
- „Stell die Heizung im Bad auf 21 Grad.“

Absicherung beim Schalten:
- Ein Agent kann nur schalten, wenn sein Besitzer die Freigabe „Geräte schalten“ hat. Die haben nach der
  Installation nur Admins. Ohne Freigabe fehlt dem Agenten das Schalt-Werkzeug, Lesen geht weiter.
- Vor dem Senden prüft HydraHive die Schreibweise von Art, Befehl und Gerät. Nennt der Agent ein Gerät, das nicht
  zur Art passt (etwa eine Lampe mit einem Heizungsbefehl), lehnt HydraHive ab.
- Eine zusätzliche Rückfrage vor dem Schalten gibt es nicht. Der Agent führt den Befehl direkt aus. Bei unklaren
  Namen soll er vorher mit `ha_list_entities` die genaue Kennung suchen.

Was nicht geht:
- Es gibt kein Werkzeug, um Automationen oder Skripte zu bearbeiten. `ha_call_service` löst nur Befehle aus, die
  dein Home Assistant schon kennt.
- Den Verlauf eines Sensors abfragen. Gelesen wird immer nur der aktuelle Zustand.
- Mehrere Home-Assistant-Instanzen. Es gibt genau eine Verbindung für das ganze HydraHive.

## Gut zu wissen

- Eine Verbindung für alle: Adresse und Schlüssel gelten für das ganze HydraHive. Alle, die das Modul nutzen dürfen,
  sehen dieselben Geräte.
- Der Zugangsschlüssel bleibt auf dem Server. Dein Browser spricht nie direkt mit Home Assistant, sondern immer über
  HydraHive.
- Rechte: Ansehen dürfen nach der Installation alle. Schalten braucht die Freigabe „Geräte schalten“, die zuerst nur
  Admins haben. Ein Admin kann sie unter **Freigaben** an andere vergeben. Sie gilt für den Schiebeschalter auf der
  Seite und für das Schalt-Werkzeug der Agenten. Ohne Freigabe ist der Schiebeschalter trotzdem zu sehen, das
  Schalten scheitert dann mit einer Meldung.
- Ein Agent mit Schaltrecht kann jeden Befehl senden, den dein Home Assistant kennt, auch für Schlösser oder Rollos.
  Das Werkzeug erlaubt auch Befehle ohne einzelnes Gerät. Je nach Befehl trifft das mehrere Geräte. Vergib die
  Freigabe darum mit Bedacht.
- Typische Meldungen:
  - „Keine Verbindung zu Home Assistant“ mit dem Hinweis, URL und Token zu prüfen: Adresse oder Schlüssel fehlen,
    Home Assistant ist nicht erreichbar oder lehnt den Schlüssel ab (etwa weil er abgelaufen ist oder gelöscht
    wurde).
  - Dasselbe rote Band erscheint, wenn ein Schaltversuch scheitert, zum Beispiel ohne Schaltrecht.
    **Aktualisieren** lädt neu und blendet es aus, solange alles klappt.
  - Antwortet Home Assistant nicht innerhalb von 15 Sekunden, bricht der Aufruf mit einem Verbindungsfehler ab.

*Stand: Home Assistant 1.0.7, 22.11.2026*
