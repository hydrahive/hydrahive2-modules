# Meine Akte – deine Gesundheitsdaten an einem Ort

**Meine Akte** ist deine persönliche, strukturierte Patientenakte. Du pflegst darin Diagnosen, Medikamente, Laborwerte, Allergien, Arztbesuche und Dokumente. Du kannst die Gesundheitsakte deiner Krankenkasse importieren und Verläufe aus Apple Health ansehen.

> Wichtig: Die Akte ist ein Ablage- und Übersichts-Werkzeug, kein Diagnose-System. Sie ersetzt keine ärztliche Beratung.

## So startest du
1. Ein Admin installiert das Modul. Danach steht **Meine Akte** in der Navigation.
2. Öffne **Meine Akte**. Die Akte ist ein geschützter Bereich: HydraHive fragt zuerst nach deiner Vault-PIN (**Vault entsperren**). Hast du noch keine, legst du sie einmal fest (**Vault-PIN festlegen**).
3. Beim ersten Öffnen siehst du **Meine Patientenakte** mit einem kurzen Formular. Trag **Vorname**, **Nachname**, **Geburtsdatum** und **Geschlecht** ein und klicke **Akte anlegen**.
4. Danach öffnet sich die **Übersicht**. Links wählst du einen Bereich, zum Beispiel **Medikamente**, und legst mit **+ Neu** den ersten Eintrag an.

## Was du damit machen kannst

### Meine Akte
- **Übersicht** – oben deine Stammdaten. Mit **Bearbeiten** änderst du sie, mit **Speichern** übernimmst du die Änderung. Darunter stehen Kacheln mit der Anzahl der Einträge je Bereich. Ein Klick auf eine Kachel öffnet den Bereich. Außerdem siehst du kurze Listen **Aktive Diagnosen**, **Allergien** und **Dauermedikation**, je höchstens fünf Einträge.
- **Zeitstrahl** – alle Einträge nach Datum. Mit den Knöpfen oben filterst du nach einem Bereich.
- **Diagnosen**, **Medikamente**, **Allergien**, **Ereignisse**, **Bildgebung**, **Ärzte**, **Dokumente**, **Notizen** – je eine Liste. Mit **Suchen…** filterst du, mit **+ Neu** legst du einen Eintrag an. Hinter jedem Eintrag stehen **Bearbeiten** (Stift) und **Löschen** (Kreuz). Vor dem Löschen fragt HydraHive nach.
- **Laborwerte** – zeigt für jeden Messwert, der mindestens zweimal erfasst wurde, eine Verlaufskurve. Bei einigen gängigen Werten ist ein Referenzbereich hinterlegt, Messungen darüber oder darunter werden farbig markiert. Mit **+ Neu** trägst du einen weiteren Wert ein.

### Verifizieren
Jeder Eintrag hat einen farbigen Punkt. Grün heißt **Manuell verifiziert**. Ein oranger Punkt heißt **Nicht verifiziert — klicken zum Verifizieren**: Ein Klick darauf markiert den Eintrag als von dir geprüft. So siehst du, was du selbst kontrolliert hast.

### Import (eGA / FHIR)
Unter **eGA / FHIR** liest du Daten deiner Krankenkasse ein, statt sie abzutippen. Importierte Daten sind schreibgeschützt und bleiben von deiner eigenen Akte getrennt.
1. In der TK-Safe App deine Akte exportieren. Du erhältst eine ZIP-Datei.
2. Auf **TK-eGA-ZIP** klicken und die ZIP-Datei wählen. Alternativ nimmt **FHIR-Bundle** eine FHIR-Datei (JSON) oder eine eGA-ZIP an.
3. Nach dem Import siehst du, wie viele Einträge neu und wie viele aktualisiert wurden.

Die Seite zeigt danach den Import über **TK-eGA-ZIP**: Kacheln je Art, zum Beispiel **Arztbesuche**, **Abrechnungen**, **Krankenhaus** oder **Vorsorge**. Ein Klick zeigt die Einträge dieser Art, **Alle** führt zurück zum **Zeitstrahl**. Der Block **Kosten (Kassenleistungen)** fasst **Arztbesuche abgerechnet**, **Apothekenpreise gesamt** und **Davon deine Zuzahlung** zusammen.

### Tracking
- **Apple Health** – der **Verlauf** deiner Gesundheitsdaten, zum Beispiel Schritte, Herzfrequenz oder aktive Kalorien. Oben wählst du den Zeitraum: 7, 14, 30 oder 90 Tage.
- **Schlaf** – der **Schlafverlauf** für dieselben Zeiträume.

Die Daten schickt die iPhone-App „Health Auto Export“. Damit HydraHive sie annimmt, muss ein Admin den Empfang auf dem Server einrichten.

### Datenschutz: Daten löschen
Unter **Daten löschen** entfernst du deine eigenen Gesundheitsdaten endgültig:
- **Apple Health** – alles, oder mit **Nur Zeitraum (optional)** nur die Tage von–bis. Lieferungen, die auch Tage außerhalb des Zeitraums enthalten, bleiben erhalten. Ihre Tageswerte im Zeitraum werden trotzdem gelöscht.
- **FHIR-Import** oder **eGA-Import (TK)** komplett.
- **Alles löschen** – Apple Health, beide Importe und deine komplette Akte mit allen Einträgen.

Nach **Löschen…** tippst du zur Bestätigung **LÖSCHEN** ein und klickst **Endgültig löschen**. Es gibt keinen Papierkorb. Große Apple-Health-Bestände brauchen einige Minuten.

## Mit Buddy und Agenten
Das Modul bringt zwei Werkzeuge mit, die nur lesen:
- **query_fhir_data** liest die Einträge, die du über **FHIR-Bundle** importiert hast. Auf Wunsch filtert es nach Art oder nach einem Suchbegriff.
- **query_health_data** fasst deine Apple-Health-Daten zusammen, für 1 bis 365 Tage (Standard 7).

Im Buddy-Fenster gibt es die Box **Gesundheit** mit drei fertigen Fragen: **Tagesauswertung**, **Wochentrend** und **Schlafqualität**. Du kannst auch frei fragen, etwa „Wie viele Schritte hatte ich in den letzten 7 Tagen?“ oder „Welche Arztbesuche stehen in meinem Import?“.

Was nicht geht:
- Die Werkzeuge liefern nur Daten, solange dein Vault in HydraHive entsperrt ist. Sonst antworten sie mit „Vault gesperrt – bitte in HydraHive entsperren.“
- Deine selbst gepflegten Einträge und den Import über **TK-eGA-ZIP** lesen die Werkzeuge nicht.
- Agenten können nichts ändern und nichts löschen. Löschen geht nur unter **Daten löschen**.
- Die Werkzeuge stellen keine Diagnosen. Sie geben wieder, was gespeichert ist.

## Gut zu wissen
- Nach 15 Minuten ohne Nutzung sperrt der Vault wieder. Dann fragt HydraHive erneut nach der PIN.
- Jeder sieht nur seine eigene Akte und seine eigenen Importe.
- Importierte Einträge kannst du nicht ändern. Eigene Ergänzungen machst du in deiner Akte.
- Solange die Automation in „Health Auto Export“ aktiv ist, kommen neue Apple-Health-Daten nach. Schalte sie dort ab, wenn du nichts mehr schicken willst.
- Backups außerhalb von HydraHive sind vom Löschen nicht betroffen.
- „Daten konnten nicht geladen werden.“ – Apple Health oder Schlaf konnten nicht geladen werden. Lade die Seite neu.
- „Import fehlgeschlagen“ – die Datei war keine gültige eGA-ZIP und kein gültiges FHIR-Bundle.

*Stand: Meine Akte 1.3.3, 22.11.2026*
