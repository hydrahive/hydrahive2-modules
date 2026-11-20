// Klartexte zu den Fehlercodes des Bankimports: was passt nicht + was ist zu tun.
// Jeder Code, den das Backend (import_*.py, routes_imports.py) werfen kann, braucht hier einen Eintrag –
// importCodes.test.ts liest die Codes aus dem Backend-Quelltext und schlägt sonst fehl.

export const SPARKASSE_CSV_HINT = "Sparkasse „CSV-MT940“/„CSV-CAMT“ ist eine CSV-Datei – Format „Automatisch“ wählen."

export const IMPORT_FILE_MESSAGES: Record<string, string> = {
  // Datei lesen / Format erkennen
  unsupported_format: "Das Dateiformat wird nicht erkannt. Erlaubt sind CAMT (XML), MT940, CSV, PDF-Kontoauszug und PayPal-Export. Lade die Datei noch einmal direkt aus dem Online-Banking herunter.",
  file_too_large: "Die Datei ist größer als 10 MiB. Exportiere einen kürzeren Zeitraum (zum Beispiel ein Quartal) und lade die Teile nacheinander hoch.",
  too_many_records: "Die Datei enthält mehr als 10.000 Buchungen. Exportiere einen kürzeren Zeitraum und lade die Teile nacheinander hoch.",
  no_records: "In der Datei wurde keine Buchung gefunden. Prüfe, ob es der richtige Export ist, und wähle das passende Format. " + SPARKASSE_CSV_HINT,
  invalid_encoding: "Die Zeichen der Datei lassen sich nicht lesen (Umlaute kaputt). Wähle als Zeichensatz „Automatisch“ oder „Windows-1252“ – oder exportiere die Datei noch einmal aus dem Online-Banking.",
  // CSV
  csv_mapping_required: "Diese CSV-Datei stammt von einer Bank, die noch nicht automatisch erkannt wird. Ordne die Spalten einmal zu – danach kannst du die Zuordnung als Profil speichern.",
  csv_header_missing: "In der CSV-Datei fehlt die Kopfzeile mit den Spaltennamen. Prüfe, ob die Datei leer ist oder ob die erste Zeile die Spaltennamen enthält, und exportiere sie sonst neu.",
  csv_column_missing: "Eine zugeordnete Spalte gibt es in der Datei nicht. Prüfe Trennzeichen und Spaltenzuordnung (Groß-/Kleinschreibung zählt) oder wähle das Format „Automatisch“.",
  invalid_csv_mapping: "Die CSV-Zuordnung ist unvollständig oder ungültig. Wähle die Spalte für das Buchungsdatum und entweder einen Betrag oder ein Soll-/Haben-Paar aus.",
  debit_credit_invalid: "In einer Zeile stehen Soll- und Haben-Betrag gleichzeitig oder gar keiner. Prüfe diese Zeile in der Datei oder die Zuordnung der Soll-/Haben-Spalten.",
  paypal_header_invalid: "Das ist kein gültiger PayPal-Aktivitäten-Export: Pflichtspalten fehlen. Exportiere die Aktivitäten in PayPal erneut als CSV mit allen Spalten.",
  // Werte in Zeilen
  invalid_date: "Ein Datum lässt sich nicht lesen. Prüfe das Datumsformat (üblich: TT.MM.JJJJ) in der Zuordnung oder korrigiere die Zeile von Hand.",
  invalid_amount: "Ein Betrag lässt sich nicht lesen. Prüfe das Dezimaltrennzeichen (Komma oder Punkt) in der Zuordnung oder korrigiere die Zeile von Hand.",
  invalid_currency: "Die Währung einer Zeile ist ungültig (erwartet: dreistelliger Code wie EUR). Korrigiere die Zeile oder wähle ein passendes Zielkonto.",
  // CAMT / MT940
  unsupported_camt_version: "Diese CAMT-Version wird nicht unterstützt (möglich: camt.053.001.02 und .08). Wähle im Online-Banking eine dieser Versionen oder nutze CSV.",
  invalid_xml: "Die XML-Datei ist beschädigt oder unvollständig. Lade den Kontoauszug noch einmal herunter und lade ihn ohne Änderungen hoch.",
  invalid_xml_encoding: "Die XML-Datei ist nicht in UTF-8 gespeichert und lässt sich nicht lesen. Exportiere sie im Online-Banking mit UTF-8 oder nutze CSV.",
  xml_declaration_forbidden: "Die XML-Datei enthält Konstrukte (DOCTYPE/ENTITY), die aus Sicherheitsgründen abgelehnt werden. Lade die Datei frisch von deiner Bank herunter, ohne sie zu bearbeiten.",
  invalid_camt_contract: "Die CAMT-Datei hat nicht den erwarteten Aufbau (genau ein Kontoauszug-Block „BkToCstmrStmt“). Exportiere einen einzelnen Kontoauszug oder nutze CSV.",
  invalid_camt_record: "Eine Buchung in der CAMT-Datei ist unvollständig. Lade die Datei neu herunter oder nutze CSV.",
  camt_batch_amount_missing: "Eine Sammelbuchung in der CAMT-Datei hat keinen Betrag. Exportiere die Umsätze als CSV oder ohne Sammelbuchungen.",
  invalid_mt940_record: "Ein MT940-Satz lässt sich nicht lesen. Prüfe, ob es wirklich SWIFT-MT940 ist (.sta/.txt) – bei Sparkasse „CSV-MT940“ handelt es sich um CSV, dann Format „Automatisch“ wählen.",
  pdf_no_text_layer: "Dieses PDF enthält keinen lesbaren Text (eingescannt). Bitte als Beleg über die Beleg-Erkennung hochladen oder einen CSV-/CAMT-Export deiner Bank verwenden.",
  pdf_unreadable: "Das PDF lässt sich nicht lesen. Es ist vermutlich beschädigt oder passwortgeschützt. Lade den Kontoauszug bitte noch einmal ohne Passwortschutz bei deiner Bank herunter.",
  pdf_too_many_pages: "Das PDF hat mehr als 50 Seiten. Bitte teile den Kontoauszug in kürzere Zeiträume auf.",
  pdf_no_transactions: "In diesem PDF wurde keine Buchungszeile erkannt. Prüfe, ob es wirklich ein Kontoauszug ist, oder nutze einen CSV-/CAMT-Export deiner Bank.",
  pdf_extraction_unavailable: "Das Auslesen von PDFs ist auf diesem Server gerade nicht verfügbar. Bitte nutze vorerst einen CSV- oder CAMT-Export oder wende dich an die Administration.",
  pdf_line_ambiguous: "Datum oder Betrag dieser Zeile sind im PDF nicht eindeutig. Bitte mit dem Kontoauszug vergleichen und die Zeile von Hand korrigieren oder verwerfen.",
  paypal_status_not_completed: "Diese PayPal-Zahlung ist noch nicht abgeschlossen (z. B. ausstehend oder abgelehnt). Sie kann erst importiert werden, wenn sie abgeschlossen ist.",
  camt_batch_amount_mismatch: "Bei einer Sammelbuchung stimmt die Summe der Einzelbuchungen nicht mit dem Gesamtbetrag überein. Die Zeile lässt sich nicht annehmen – verwirf sie oder prüfe die Datei bei deiner Bank.",
  pending_transaction: "Vorgemerkt – noch nicht gebucht: Die Bank hat diesen Umsatz erst vorgemerkt. Er lässt sich noch nicht übernehmen und kommt mit dem nächsten Export, sobald er gebucht ist.",
}

export const IMPORT_FLOW_MESSAGES: Record<string, string> = {
  // Konto / Paket / Zeilen
  account_archived: "Das Zielkonto ist archiviert. Stelle es wieder her oder wähle ein aktives Konto.",
  account_not_found: "Das Zielkonto gibt es nicht (mehr). Lade die Seite neu und wähle ein vorhandenes Konto.",
  import_base_currency_account_required: "Importiert werden kann nur auf Konten in der Haushaltswährung. Wähle ein Konto in dieser Währung.",
  duplicate_import_file: "Genau diese Datei wurde schon importiert. Öffne das vorhandene Paket unter „Importe“ – oder lade eine andere Datei hoch.",
  duplicate_import_row: "Diese Zeile gibt es schon (gleiche Buchung bereits im Haushalt). Verwirf die Zeile, statt sie anzunehmen.",
  import_batch_not_found: "Dieses Import-Paket gibt es nicht (mehr). Gehe zurück zur Übersicht und lade sie neu.",
  import_row_has_errors: "Diese Zeile hat noch Fehler und kann nicht angenommen werden. Korrigiere Datum, Betrag und Währung oder verwirf die Zeile.",
  import_row_incomplete: "Mindestens eine angenommene Zeile ist unvollständig (Datum, Betrag oder Währung fehlt). Korrigiere sie oder verwirf sie, dann den Import erneut abschließen.",
  no_accepted_import_rows: "Es ist keine Zeile angenommen. Nimm mindestens eine Zeile an, bevor du den Import abschließt.",
  import_category_required: "Mindestens eine angenommene Zeile hat keine Kategorie. Wähle für jede Zeile eine Kategorie, dann den Import erneut abschließen.",
  import_category_kind_mismatch: "Eine Kategorie passt nicht zur Buchung (Einnahme-Kategorie bei einer Ausgabe oder umgekehrt). Wähle eine passende Kategorie.",
  category_not_found: "Diese Kategorie gibt es nicht (mehr) oder sie ist archiviert. Wähle eine andere Kategorie.",
  transaction_not_found: "Die zugehörige Buchung gibt es nicht (mehr). Lade die Seite neu.",
  // Profile
  import_profile_conflict: "Ein CSV-Profil mit diesem Namen gibt es schon (oder es wurde zwischenzeitlich geändert). Wähle einen anderen Namen oder lade die Profile neu.",
  import_profile_in_use: "Dieses CSV-Profil wird von einem Import-Paket verwendet und lässt sich nicht löschen. Lösche zuerst das Paket – oder behalte das Profil.",
  import_profile_not_found: "Dieses CSV-Profil gibt es nicht (mehr). Lade die Profile neu und wähle ein vorhandenes.",
  // Warnungen
  paypal_currency_conversion_discarded: "PayPal-Währungsumrechnung ausgeblendet: Die Umrechnungszeile wurde nicht übernommen, die eigentliche Zahlung steht in der Zeile davor.",
  possible_duplicate: "Mögliches Duplikat (schwacher Treffer): Eine ähnliche Buchung gibt es schon. Prüfe sie und verwirf diese Zeile, falls sie doppelt ist.",
  account_currency_mismatch: "Die Währung der Zeile passt nicht zum Zielkonto. Wähle ein Konto in dieser Währung oder korrigiere die Zeile.",
}
