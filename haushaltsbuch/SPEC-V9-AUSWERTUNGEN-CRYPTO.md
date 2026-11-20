# Haushaltsbuch Etappe 9+ — Auswertungen, erweiterte Importe, Crypto-Brücke

> **Vorrang-Hinweis (VERTRAG-B.md, 20.11.2026):** Das Zieldokument
> `hydrahive2-modules/ziele/haushalt-krypto.md` erklärt Krypto-Trade-Buchungen im
> Haushaltsbuch ausdrücklich NICHT mehr zum Nicht-Ziel (siehe unten "Kein automatisches
> Trade-Tracking ... das Haushaltsbuch zeigt nur den aggregierten Vermögenswert und bietet
> einen manuellen Trade-Import an"). Seit Etappe B gilt stattdessen: Swaps werden als
> Umbuchungen zwischen Krypto-Konten gebucht, Krypto-Zahlungen (Kartenzahlung/Abgang) als
> echte Ausgaben-Buchungen (`crypto_ledger_import.py`, `POST /crypto-bridge/ledger-imports`).
> Kollidiert diese Spec mit dem Zieldokument, gilt das Zieldokument.

## Was

Diese Spec konkretisiert die bisher nur stichwortartige Roadmap-Etappe 9
("Auswertungen und Exporte") und ergänzt sie um zwei bisher fehlende
Bausteine, die beim Review vom 2026-11-19 als größte Lücken auffielen:

1. **Grafische Auswertungen im Dashboard und in einer neuen Reports-Ansicht.**
   Aktuell zeigt `DashboardView.tsx` ausschließlich vier Kennzahlkacheln,
   eine einzelne Budget-Fortschrittsleiste und zwei Listen. Es existiert
   kein einziges Zeit- oder Verteilungsdiagramm, obwohl `recharts` und `d3`
   bereits Kern-Abhängigkeiten sind und in `cryptoboard` und `patientenakte`
   produktiv genutzt werden.
2. **Eine Brücke zum Modul `cryptoboard`**, damit Krypto-Bestände als Teil
   des Haushaltsvermögens sichtbar werden, statt als isolierter
   Handeintrag im Kontotyp `wallet` zu verstauben.

Zusätzlich wird der Importumfang um ein PDF-Kontoauszug-Format und PayPal-CSV
erweitert, weil beide bei vergleichbaren Haushaltsbuch-Apps (Finanzguru,
Outbank, Monavio-Vergleich 2026) Standard sind und beim Review als Lücke
auffielen.

## Warum

- Ohne Verlaufsdiagramme lässt sich eine Entwicklung (Sparquote, Vermögen,
  Fixkosten-Anteil) nur durch Kopfrechnen aus Einzelzahlen ablesen. Das
  widerspricht dem Zielbild "gemeinsam nutzbares Haushaltsbuch" — gerade für
  Familien ist der Trend über Monate interessanter als der Monatswert allein.
- Krypto-Bestände gehören wirtschaftlich zum Haushaltsvermögen. Ein Konto
  vom Typ `wallet` ohne Kursanbindung zwingt zu manueller, schnell
  veraltender Pflege. `cryptoboard` hat Kurs-Client, FIFO-Portfolio und
  CSV-Exchange-Import bereits fertig — doppelte Implementierung wäre
  unnötiger Wartungsaufwand und Kursdrift-Risiko.
- PDF-Kontoauszüge sind bei vielen Banken der einzige Export ohne
  Online-Banking-Freischaltung. CAMT/MT940/CSV deckt das nicht ab.
- PayPal ist für private Haushalte ein eigenständiges Zahlungsmittel mit
  eigenem CSV-Export; fehlt aktuell komplett.

## Verbindliche Produktentscheidungen

### Auswertungen (Charts)

- Reine Lesefunktion auf bereits vorhandenen Ledger-/Budget-/Asset-Daten.
  Keine neuen Buchungsarten, keine neuen Rechte.
- Alle Diagramme serverseitig vorberechnet (Backend liefert fertige
  Zeitreihen/Aggregate als JSON), kein Client-seitiges Aufsummieren großer
  Transaktionsmengen. Grund: Haushalte mit mehreren Jahren Historie dürfen
  das Frontend nicht einfrieren.
- Zeiträume wählbar: 3/6/12/24 Monate sowie "seit Haushaltsgründung".
- Jedes Diagramm hat eine textuelle/tabellarische Alternative (Barrierefreiheit
  und Export), analog zur bestehenden Praxis in `DashboardView.tsx`
  ("Fortschritt wird zusätzlich als Prozentwert angezeigt").
- Kein Float für Geldwerte — Aggregation bleibt in Minor Units (Integer) bis
  zur reinen Darstellungsschicht.
- Neue Diagramme:
  1. Cashflow-Balken: Einnahmen/Ausgaben je Monat, rollierend, mit Netto-Linie.
  2. Vermögensentwicklung: Linie über Gesamtsaldo aller Konten (inkl. Assets/
     Crypto-Bridge, siehe unten) am Ende jedes Monats.
  3. Ausgaben-Verteilung: Donut/Balken nach Kategorie für den gewählten
     Zeitraum, mit Drill-down auf Unterkategorien.
  4. Budget-Verlauf: Ist/Soll je Budget über mehrere Perioden statt nur der
     aktuellen (Erweiterung des bestehenden Einzelbalkens).
  5. Fixkosten-vs-variabel: Anteil erkannter wiederkehrender Zahlungen am
     Gesamtausgaben, je Monat.
- Export: Die zugrunde liegenden Aggregate sind über denselben Endpunkt als
  CSV abrufbar wie sie das Chart zeigt (ein Datenvertrag, zwei Darstellungen).

### Import-Erweiterung

- Neues Format `pdf` im gemeinsamen Importvertrag (`ImportFormat`). PDF wird
  nicht per LLM-OCR interpretiert, sondern über strukturierte Text-Extraktion
  (vorhandene PDF-Text-Schicht der Bank-PDFs, kein Bild-OCR in Etappe 9).
  Scan-PDFs ohne Textschicht werden mit klarer Fehlermeldung abgelehnt und
  auf den bestehenden Beleg-OCR-Pfad (Etappe 4) verwiesen — beide Pfade bleiben
  getrennt, da unterschiedliche Vertrauens- und Prüfanforderungen gelten.
- Neues CSV-Profil `paypal` mit fester Spaltenzuordnung für den offiziellen
  PayPal-Aktivitäten-Export (inkl. Gebührenzeile als eigene Splitbuchung,
  Währungsumrechnungszeilen werden erkannt und verworfen statt doppelt
  gebucht).
- Beide Formate durchlaufen denselben Prüfbereich wie bestehende Importe
  (Vorschau, Duplikaterkennung über Fingerprint, atomarer Abschluss). Keine
  Sonderpfade, kein Bypass der Etappe-2-Garantien.

### Crypto-Brücke zu Cryptoboard

- Kein eigener Kurs-Client, kein eigenes Wallet-/Adressmodell im
  Haushaltsbuch. Die Brücke liest ausschließlich über eine stabile,
  modulinterne Schnittstelle von `cryptoboard` (Portfolio-Bestand,
  aktueller Bewertungswert in Haushaltsbasiswährung).
- Ein Konto vom Typ `wallet` kann optional mit genau einem
  `cryptoboard`-Portfolio-Eintrag verknüpft werden (`linked_portfolio_id`,
  nullable, 1:1). Ohne Verknüpfung verhält sich `wallet` wie bisher
  (manueller Saldo).
- Verknüpfte Wallet-Konten zeigen den Saldo als Read-only-Live-Wert aus
  Cryptoboard; manuelle Saldo-Buchungen auf diesem Konto sind gesperrt,
  solange die Verknüpfung besteht. Das Entfernen der Verknüpfung ist
  jederzeit möglich und fällt auf den letzten gebuchten Saldo zurück
  (keine Datenverluste).
- Cryptoboard-Exchange-Trades sind **nicht** automatisch Buchungen. Ein
  optionaler, expliziter Import holt Trades aus Cryptoboard und bildet sie
  im bestehenden Importvertrag ab (Kauf = Transfer vom Fiat-Konto auf das
  verknüpfte Wallet-Konto, Gebühr = Ausgabe-Splitbuchung in eine wählbare
  Kategorie). Dieser Import läuft durch dieselbe Vorschau/Prüf-Pipeline wie
  Bank-CSV-Importe.
- Berechtigungsgrenze: Die Brücke liest nur Portfolios, die dem
  anfragenden Benutzer in Cryptoboard selbst gehören. Kein Haushaltsmitglied
  erhält über das Haushaltsbuch Zugriff auf ein Cryptoboard-Portfolio eines
  anderen Mitglieds, auch wenn beide im selben Haushalt sind, außer das
  Portfolio wurde in Cryptoboard explizit freigegeben (vorhandener
  Freigabe-Mechanismus von Cryptoboard gilt unverändert fort).
- Kill-Switch: Die Verknüpfung lässt sich pro Konto trennen; bei
  deinstalliertem oder deaktiviertem `cryptoboard`-Modul fällt das
  Haushaltsbuch auf den zuletzt bekannten Wert plus deutlich sichtbarem
  "Kurs nicht aktuell"-Hinweis zurück, statt zu crashen oder stillschweigend
  zu veralten.

## Nicht-Ziele dieser Etappe

- Keine FinTS/PSD2-Anbindung (bleibt Etappe 10, eigenes Security-Audit).
- Kein Bild-OCR für PDF-Kontoauszüge (nur Textschicht-Extraktion).
- Kein automatisches Trade-Tracking/Steuerreport für Krypto — das bleibt
  Aufgabe von `cryptoboard`, das Haushaltsbuch zeigt nur den aggregierten
  Vermögenswert und bietet einen manuellen Trade-Import an.
- Keine Schreibrechte des Haushaltsbuchs auf Cryptoboard-Daten.

## Abgrenzung zu bestehenden Etappen

- Etappe 2 (Bankimport-Inbox): PDF und PayPal sind neue Formate im selben
  Vertrag, keine neue Pipeline.
- Etappe 4 (Belege/OCR): bleibt zuständig für Kassenbon-/Belegbilder;
  PDF-Kontoauszüge sind strukturierter Text, kein OCR-Fall.
- Etappe 6 (Loyalty): eigenständiges Provider-Adapter-Muster; die
  Crypto-Brücke übernimmt bewusst nicht dessen Sync-Engine, weil
  Cryptoboard bereits eine eigene, vollständige Preis-/Portfolio-Pipeline
  betreibt, die nur gelesen statt neu gebaut wird.
