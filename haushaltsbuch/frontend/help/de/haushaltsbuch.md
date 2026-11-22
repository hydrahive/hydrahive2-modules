# Haushaltsbuch – gemeinsam den Überblick über Geld, Budgets und Konten behalten

Das Haushaltsbuch ist ein gemeinsames Finanzbuch für dich und die Menschen, mit denen du wirtschaftest.
Du erfasst Buchungen oder importierst Kontoauszüge, lässt dir Kategorien vorschlagen und behältst Budgets,
feste Zahlungen und die Entwicklung deines Geldes im Blick. Die Daten bleiben in HydraHive und sind mit deiner
Vault-PIN geschützt.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Öffne das **Haushaltsbuch** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich
   **Zuhause & Privat**).
3. Das Haushaltsbuch ist ein geschützter Bereich. Beim ersten Mal legst du eine Vault-PIN fest (6 bis 12
   Ziffern, dazu einmal dein Login-Passwort). Danach entsperrst du den Bereich mit dieser PIN.
4. Wähle **Haushalt anlegen** und trage **Haushaltsname**, **Basiswährung** und **Zeitzone** ein. Mit
   **Standardkategorien anlegen** bekommst du gleich Kategorien wie Gehalt, Wohnen und Lebensmittel.
   Hast du einen Code bekommen, wähle stattdessen **Einladung annehmen**, füge den **Einladungscode** ein und
   klicke **Beitreten**.
5. Lege im Reiter **Konten & Kategorien** mit **Konto** dein erstes Konto an, zum Beispiel ein Girokonto mit
   Anfangssaldo.
6. Erfasse im Reiter **Buchungen** mit **Buchung erfassen** die erste Ausgabe oder lade im Reiter **Importe** mit
   **Neuer Import** einen Kontoauszug hoch.

## Was du damit machen kannst

### Übersicht
Oben stehen **Gesamtsaldo**, **Einnahmen diesen Monat**, **Ausgaben diesen Monat** und die **90-Tage-Prognose**.
Darunter zeigt **Entwicklung** zwei kleine Diagramme: Einnahmen und Ausgaben der letzten 6 Monate und den
Vermögensverlauf der letzten 12 Monate. **Alle Auswertungen** führt zum Reiter **Auswertungen**.
Außerdem siehst du den **Budgetverbrauch**, die **Nächste Zahlungen** aus deinen Serien und die
**Letzte Buchungen**. Würde dein Kontostand in den nächsten 30 Tagen ins Minus rutschen, erscheint oben die
Warnung **Prognostizierte Unterdeckung** mit Datum und erwartetem Saldo.

### Auswertungen
Wähle oben den Zeitraum: **3 Monate**, **6 Monate**, **12 Monate**, **24 Monate** oder **Seit Beginn**.
Es gibt fünf Auswertungen:
- **Einnahmen und Ausgaben** je Monat, mit einer Linie für das, was übrig bleibt.
- **Vermögensverlauf**: die Summe aller Konten am Ende jedes Monats.
- **Ausgabenverteilung** nach Kategorien. Ein Klick auf eine Kategorie mit › zeigt ihre Unterkategorien,
  **Zurück** geht wieder eine Ebene hoch.
- **Budget-Verlauf**: geplant gegen tatsächlich ausgegeben, Monat für Monat.
- **Fixkosten und variable Kosten**: feste Ausgaben gegenüber dem Rest, mit dem Fixkosten-Anteil.

Unter jedem Diagramm öffnet **Als Tabelle anzeigen** dieselben Zahlen als Tabelle. **CSV** lädt sie als Datei
für Excel oder LibreOffice herunter.

### Buchungen
Die Liste lässt sich nach Zeitraum, Konto, Kategorie und Suchbegriff (Empfänger, Zweck, Notiz) eingrenzen.
Danach **Filtern** klicken.
**Buchung erfassen** öffnet ein Formular mit vier Arten:
- **Ausgabe** und **Einnahme** mit Konto und Kategorie,
- **Umbuchung** zwischen zwei deiner Konten,
- **Split**: ein Betrag, aufgeteilt auf mehrere Kategorien, zum Beispiel ein Einkauf mit Lebensmitteln und
  Drogerie. Die Teilbeträge müssen zusammen den Gesamtbetrag ergeben.

Bei Konten in fremder Währung trägst du zusätzlich den Betrag in deiner Basiswährung und den
**Manueller Wechselkurs** ein. Mit **Verbindlich buchen** wird gespeichert.
Buchungen werden nie gelöscht. Über das Storno-Symbol in der Zeile und **Storno erzeugen** entsteht eine
Gegenbuchung. Die alte Buchung bleibt als „Storniert“ sichtbar.

### Importe
Kontoauszüge kommen zuerst als **Entwurf** in die **Bankimport-Inbox**. Gebucht wird erst, wenn du den Import
abschließt.
1. **Neuer Import** klicken, **Zielkonto** und **Datei** wählen. Möglich sind CAMT (XML), MT940, CSV,
   PDF-Kontoauszüge und der PayPal-Export (CSV), jeweils bis 10 MiB.
2. Beim **Format** reicht meist **Automatisch erkennen**. Bekannte Banken werden ohne weitere Angaben erkannt.
   Bei einer unbekannten Bank öffnet sich die **CSV-Zuordnung**. Kopfzeile und Beispielzeilen aus deiner Datei
   sind dort schon eingetragen. Du ordnest die Spalten einmal zu und speicherst das als Profil (**Profilname**,
   **Speichern**). Beim nächsten Mal klappt es ohne Zuordnung.
3. **Als Entwurf hochladen**. Der Entwurf öffnet sich mit allen Zeilen.
4. Jede Zeile kannst du **Annehmen**, **Verwerfen** oder **Korrigieren** (Datum, Betrag, Gegenpartei, Zweck).
   Für viele Zeilen gibt es **Alle gültigen annehmen** und **Alle gültigen verwerfen**. Doppelte und fehlerhafte
   Zeilen sind markiert und erklärt. Umsätze, die die Bank erst vorgemerkt hat, heißen
   „Vorgemerkt – noch nicht gebucht“ und kommen mit dem nächsten Export.
5. **Kategorien automatisch vorschlagen**: Mit **Vorschlagen** sucht HydraHive zuerst in deiner Historie, wie du
   denselben Händler früher eingeordnet hast. Nur unbekannte Händler gehen an das gewählte KI-Modell. Jeder
   Vorschlag zeigt, ob er „aus deiner Historie“ oder „per KI“ stammt und wie sicher er ist. Übernimm ihn einzeln mit
   **Übernehmen** oder alle mit **Alle Vorschläge übernehmen**.
6. **Import abschließen** und mit **Verbindlich buchen** bestätigen. **Entwurf löschen** verwirft den Entwurf
   stattdessen, ohne dass etwas gebucht wird.

Abgeschlossene Importe stehen unter **Historie**. Dort zeigt **Details** die Zeilen, und **Paket stornieren**
erzeugt Gegenbuchungen für den ganzen Import.

**Krypto-Buchungen übernehmen** holt die Buchungen aus dem Modul Cryptoboard als Entwurf. Dafür müssen an einem
Wallet-Konto Adressen verknüpft sein (siehe **Konten & Kategorien**). Der Entwurf zeigt getrennt:
- **Umbuchungen (Swaps)**: Tausch zwischen deinen eigenen Krypto-Konten, keine Ausgabe.
- **Ausgaben (MetaMask Card)**: Kartenzahlungen mit USDC, umgerechnet in Euro am Tag der Zahlung, als Ausgabe
  ohne Kategorie.
- Sonstige Abgänge stehen als „Verworfen“ im Entwurf. Willst du sie doch buchen, nimmst du sie dort an.
- Unklare Einträge, zum Beispiel ohne Euro-Wert, werden mit Grund aufgelistet und nicht gebucht.

Bereits übernommene Einträge werden erkannt und nicht doppelt gebucht.

### Kundenkarten
Hier verbindest du **Lidl Plus** und holst deine digitalen Kassenbons ab, mit Artikeln, Rabatten und Pfand.
Die Verbindung ist experimentell, inoffiziell und liest nur. Coupons werden nicht aktiviert, Buchungen bleiben
unverändert.
1. **Experimentell verbinden** klicken und **Ich akzeptiere das experimentelle Risiko ausdrücklich.** ankreuzen.
2. **Sicheren Browserflow starten**, dann **Direkt bei Lidl anmelden**.
3. Nach der Anmeldung die komplette Adresse aus der Adresszeile des Browsers (sie beginnt mit
   `com.lidlplus.app://callback`) in **Komplette Callback-URL** einfügen und **Verbindung abschließen**.
4. Mit **Jetzt synchronisieren** holst du neue Belege. Sie erscheinen unter **Synchronisierte Lidl-Belege**.
   **Details** zeigt die einzelnen Artikel, der **Sync-Verlauf** die bisherigen Abrufe.

**Verbindung trennen** entfernt die Verbindung und die abgeholten Belege. Buchungen bleiben dabei unverändert.

### Konten & Kategorien
Mit **Konto** legst du ein Konto an. Mögliche Kontotypen sind Girokonto, Tages-/Sparkonto, Bargeld, Kreditkarte,
PayPal/Wallet, Darlehen/Verbindlichkeit, Wertkonto/Depot und Benutzerdefiniert. Als **Kontoinhaber** wählst du
„Gemeinsam“ oder ein Mitglied. Die Währung darf von der Basiswährung abweichen und ist nach dem Anlegen fest.
Mit **Kategorie** legst du Kategorien für Ausgaben oder Einnahmen an, auf Wunsch mit
**Übergeordnete Kategorie** und **Farbe**.
Konten und Kategorien werden nicht gelöscht, sondern archiviert. Für alte Buchungen bleiben sie erhalten.
**Archivierte anzeigen** blendet sie wieder ein, dort kannst du sie auch reaktivieren.

Konten vom Typ PayPal/Wallet lassen sich zusätzlich mit dem Modul Cryptoboard verbinden:
- **Adressen verknüpfen**: Du wählst deine eigenen Cryptoboard-Adressen aus. Das Konto zeigt dann den Bestand
  je Coin mit Wert. Es wird nur gelesen, nie etwas gesendet oder signiert.
- **Mit Cryptoboard verknüpfen**: Du verbindest das Konto mit einem Cryptoboard-Portfolio. Neben dem gebuchten
  Saldo erscheint dann der Live-Wert. Manuelle Buchungen auf diesem Konto sind danach gesperrt.
- **Trades importieren**: Käufe und Verkäufe aus Cryptoboard kommen als Entwurf in die Importe. Du wählst das
  **Konto für Käufe und Verkäufe**, auf Wunsch eine Kategorie für Gebühren und ein Startdatum, dann
  **Entwurf anlegen** und **Zur Prüfung**. Käufe und Verkäufe werden als Umbuchung zwischen deinem Konto und dem
  Wallet gebucht, Gebühren als Ausgabe.

### Budgets
**Budget anlegen** öffnet das Formular. Als **Geltungsbereich** wählst du den ganzen Haushalt oder eine
Ausgaben-Kategorie, deren Unterkategorien mitzählen. Als **Budgetart** gibt es Monatlich ohne Übertrag,
Monatlich mit Restübertrag, Dauerhafte Rücklage, Einmaliger Zeitraum und Jahresbudget. Dazu kommen Betrag,
Beginn, Ende und die **Warnschwelle (%)**, vorbelegt mit 80 %.
Jede Budgetkarte zeigt, wie viel verbraucht und wie viel noch verfügbar ist. Ist die Warnschwelle erreicht, steht
das auf der Karte. Budgets lassen sich deaktivieren und reaktivieren, ihre Geschichte bleibt dabei erhalten.

### Wiederkehrend
Mit **Serie anlegen** erfasst du regelmäßige Zahlungen wie Miete, Gehalt oder Abos: Art, Konto, Kategorie,
**Frequenz** (Täglich, Wöchentlich, Monatlich, Jährlich), **Intervall**, Betrag, **Nächste Fälligkeit**,
**Enddatum (optional)**, **Vertragspartner**, Toleranz, **Kündigungsfrist (Tage)** und Notiz.
Bestätigte Serien fließen in die Prognose und in die **Nächste Zahlungen** auf der Übersicht ein. Gebucht wird
dabei nichts. Auch überfällige Serien werden niemals automatisch gebucht. Eine Serie lässt sich pausieren und mit
**Fortsetzen** wieder aufnehmen.

### Haushalt
- **Haushalt**: Name und Zeitzone ändern und mit **Einstellungen speichern** sichern (nur der Eigentümer).
- **Mitglieder**: Der Eigentümer fügt Mitglieder über den exakten Benutzernamen mit **Hinzufügen** hinzu. Er kann
  Mitglieder entfernen oder die Eigentümerschaft mit **Übertragen** abgeben. Danach ist er selbst normales
  Mitglied.
- **Einladungen**: **Einladung erzeugen** erstellt einen Code, der 24 Stunden gilt. Er wird nur einmal angezeigt,
  sichere ihn also gleich mit **Kopieren**. Offene Einladungen lassen sich **Widerrufen**.
- **Datenexport**: **JSON exportieren** lädt Haushalt, Finanzdaten und das Änderungsprotokoll als Datei herunter.
- **Gefahrenbereich**: **Haushalt löschen** entfernt den ganzen Haushalt unwiderruflich. Dafür tippst du den
  Haushaltsnamen und das Wort DELETE ein (nur der Eigentümer).

## Gut zu wissen

- Vault-PIN: Ohne entsperrten Vault öffnet sich das Haushaltsbuch nicht. Nach 15 Minuten ohne Nutzung sperrt er
  sich wieder. Hast du die PIN vergessen, legst du über „PIN vergessen?“ mit deinem Login-Passwort eine neue fest.
  Deine Daten bleiben dabei erhalten.
- Gemeinsame Daten: Alle Mitglieder eines Haushalts sehen und bearbeiten alle Finanzdaten. Jeder Nutzer kann nur
  in einem Haushalt sein.
- Basiswährung: Sie wird beim Anlegen des Haushalts festgelegt und lässt sich danach nicht mehr ändern. Importe
  gehen nur auf Konten in der Basiswährung.
- Nichts verschwindet heimlich: Buchungen und Importe werden storniert statt gelöscht. Jede Änderung landet im
  Änderungsprotokoll, das der Datenexport mitliefert.
- Gleichzeitig bearbeitet: Hat jemand anderes denselben Eintrag inzwischen geändert, erscheint
  **Zwischenzeitlich geändert**. Lade dann neu und prüfe erneut.
- KI-Vorschläge: An das gewählte KI-Modell gehen nur Empfänger und Verwendungszweck unbekannter Händler, keine
  Beträge. Je nach Modell läuft das lokal oder bei einem Cloud-Anbieter. Ist die KI nicht erreichbar, bekommst du
  nur Vorschläge aus deiner Historie und ordnest den Rest von Hand zu.
- Import-Grenzen: höchstens 10 MiB und 10.000 Buchungen je Datei. PDFs dürfen höchstens 50 Seiten haben und
  müssen echten Text enthalten, eingescannte Auszüge gehen nicht. Dieselbe Datei wird kein zweites Mal
  importiert. Bei einem Fehler erklärt die Meldung, was nicht passt und was zu tun ist.
- Cryptoboard: Die Verbindung braucht das installierte Modul Cryptoboard. Die Portfolio-Verknüpfung funktioniert
  nur, wenn Haushalt und Konto in Euro geführt werden. Live-Wert und Bestand sieht nur das Mitglied, das das Konto
  verknüpft hat, die anderen sehen nur, dass es verknüpft ist. Trades importieren kann nur dieses Mitglied.
- Lidl Plus: Die Anmeldung bei Lidl liegt im Vault, nicht im Haushaltsbuch, und wird beim Trennen dort wieder
  gelöscht. Die Lidl-Schnittstelle ist nicht öffentlich und kann sich jederzeit ändern oder den Zugriff
  blockieren. Der Betreiber kann die Lidl-Verbindung für die ganze Installation abschalten.
- Buddy und Agenten haben keinen Zugriff auf das Haushaltsbuch. Es gibt dafür keine Werkzeuge.

*Stand: Haushaltsbuch 1.14.4, 22.11.2026*
