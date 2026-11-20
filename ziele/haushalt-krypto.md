# Zieldokument: Haushaltsbuch + Krypto als ein Kassenbuch

> **Status:** ENTWURF – wartet auf Tills Freigabe. Nichts bauen, bevor oben „FREIGEGEBEN“ steht.
> **Verbindlich für:** jeden Auftrag an `haushaltsbuch` und `cryptoboard`, der dieses Ziel berührt.
> **Regel:** Fertig ist ein Auftrag erst, wenn alle Abnahme-Punkte seiner Etappe **an Tills echten Daten** erfüllt sind.
> Grüne Tests allein zählen nicht. Kollidiert ein älteres SPEC/PLAN-Dokument mit diesem hier, **gilt dieses**
> (insbesondere `haushaltsbuch/SPEC-V9-AUSWERTUNGEN-CRYPTO.md`, das Trade-Buchungen im Haushaltsbuch als Nicht-Ziel nennt).

## 1. Zielbild (Tills Worte, bestätigt 20.11.2026)

1. Das **Haushaltsbuch ist das eine Kassenbuch** für alles Geld, auf Bankkonten und in Krypto.
2. **Krypto-Wallets sind Konten** im Haushaltsbuch, mit Bestand und Wert in EUR.
3. **Swaps** (z. B. TRX → USDC) sind **Umbuchungen** zwischen Tills eigenen Krypto-Konten, **keine Ausgaben**.
   Gewinn/Verlust daraus zeigt das Cryptoboard.
4. **Zahlungen mit Krypto** (USDC über den Zahlungsdienst) sind **Ausgaben**: Datum, Betrag, EUR-Wert am Tag,
   **Kategorie** – wie eine Kartenzahlung vom Girokonto. **Till weist die Kategorie selbst zu.**
   Rechnungen/Belege lassen sich hochladen und **Buchungen zuordnen**.
5. **Auswertung:** Einnahmen und Ausgaben je Monat und Kategorie, **über alle Konten zusammen**,
   dazu Vermögensentwicklung inklusive Krypto.
6. **Cryptoboard** bleibt zuständig für Kurse, Wallets, Trade-Erkennung und Gewinn/Verlust;
   **das Haushaltsbuch übernimmt die Buchungen** aus dem Cryptoboard.

## 2. Begriffe (damit alle dasselbe meinen)

| Begriff | Bedeutung | Im Haushaltsbuch | Im Cryptoboard |
|---|---|---|---|
| **Swap** | Tausch eigener Werte (TRX → USDC), auch über zwei Chains | Umbuchung Krypto-Konto A → Krypto-Konto B (kein Einnahme/Ausgabe-Posten) | sell TRX + buy USDC (FIFO, Gewinn/Verlust) |
| **Krypto-Zahlung** | USDC verlässt Tills Wallet an einen Zahlungsdienst/Händler | **Ausgabe** mit Kategorie, EUR-Wert am Tag | transfer_out (Bestand sinkt) |
| **Krypto-Eingang ohne Swap** | z. B. Einzahlung von außen | **Einnahme** oder Umbuchung (Till entscheidet) | transfer_in |
| **Transfer eigene Wallets** | zwischen Tills eigenen Adressen | Umbuchung, nie Einnahme/Ausgabe | transfer_out + transfer_in |
| **Spam-Token** | Fake-Token (z. B. „ꓴ឵ՏᎠ឵Ⲧ“, „www.afomo.top ✅“) | taucht nie auf | ausgeblendet |

## 3. Ausgangslage (geprüft 20.11.2026)

- Cryptoboard 1.7.0 live: erkennt Tills 17 TRX→USDC-Swaps (12.06.–17.11.) und 102 USDC-Zahlungen; Swaps sind gebucht
  (17× sell TRX, 17× buy USDC), **Zahlungen nicht**.
- Haushaltsbuch 1.11.0 live: Kontotypen inkl. `wallet`, Buchungen mit Gegenkonto, Kategorien, Reports
  (Cashflow, Vermögen, Kategorien, Budgets, Fixkosten), Crypto-Brücke (liest nur buy/sell, ignoriert transfer_*).
  **Tills Haushalt hat noch keine eigenen Konten und keine Buchungen.**
- Belege gibt es nur für Lidl-Kassenbons (Loyalty), **keine Belege/Anhänge an beliebigen Buchungen**.
- **Bekannter Fehler:** Cryptoboard zeigt +18.164 € realisierten TRX-Gewinn – falsch, weil die TRX-Einstände fehlen
  (CSV-Import: transfer_in mit Preis 0). Nicht steuerlich verwenden, bis Etappe D erledigt ist.

## 4. Abnahme (pro Punkt: Was Till sieht/tut + wie es geprüft wird)

Legende Stand: ✅ geht schon · 🟡 teilweise · ❌ fehlt

### Etappe A – Kassenbuch-Grundlage
| # | Till kann … | Prüfung (an echten Daten) | Stand |
|---|---|---|---|
| A1 | einen Haushalt mit seinen Konten haben: mindestens Girokonto + ein Konto je Krypto-Wallet (Tron TWgdiv…ZeyD, Base/Ethereum 0xa1aE…696E) | Haushaltsbuch → Konten zeigt diese Konten; DB: Konten vom Typ `wallet` mit Verknüpfung zur Cryptoboard-Adresse | ❌ |
| A2 | je Krypto-Konto den **Bestand je Coin** und den **EUR-Wert** sehen, aktuell wie im Cryptoboard | Wert im Haushaltsbuch = Wert im Cryptoboard (± Kursrundung, gleiche Uhrzeit) | 🟡 (nur Gesamtwert eines Portfolios) |

### Etappe B – Krypto-Buchungen übernehmen
| # | Till kann … | Prüfung | Stand |
|---|---|---|---|
| B1 | die **17 Swaps** als **Umbuchungen** TRX-Konto → USDC-Konto sehen, **nicht** als Ausgaben | Report „Kategorien/Cashflow“ zählt sie nicht als Ausgabe; Liste zeigt 17 Umbuchungen mit Datum und EUR-Wert | ❌ |
| B2 | die **102 USDC-Zahlungen** als **Ausgaben** sehen (Datum, USDC-Betrag, EUR-Wert am Tag) | Haushaltsbuch → Buchungen: 102 Ausgaben vom USDC-Konto; Summe EUR = Summe der Tageswerte | ❌ |
| B3 | erneut importieren, **ohne Doppelungen** | zweiter Import: 0 neue Buchungen | ❌ |
| B4 | in der Import-Vorschau sehen, **was** übernommen wird (Swaps/Zahlungen getrennt) und es **bestätigen** | Vorschau zeigt zwei Gruppen mit Anzahl und Summe; ohne Bestätigung wird nichts gebucht | ❌ |

### Etappe C – Kategorien und Belege
| # | Till kann … | Prüfung | Stand |
|---|---|---|---|
| C1 | jeder Krypto-Ausgabe eine **Kategorie** geben (auch mehreren auf einmal) | Kategorie setzen bei der Zahlung vom 19.11. 23:12 (2.951,44 USDC); erscheint im Kategorien-Report | 🟡 (Kategorien gibt es, Mehrfachauswahl?) |
| C2 | eine **Rechnung/Beleg** (PDF/Bild) hochladen und einer oder mehreren Buchungen **zuordnen** | Beleg hochladen, der Zahlung zuordnen, an der Buchung sichtbar und wieder öffnen | ❌ |
| C3 | Zahlungen **ohne** Kategorie bzw. **ohne** Beleg filtern | Filter „ohne Kategorie“ zeigt alle noch offenen Krypto-Ausgaben | ❌ |

### Etappe D – Auswertung
| # | Till kann … | Prüfung | Stand |
|---|---|---|---|
| D1 | **Einnahmen/Ausgaben je Monat** über **alle** Konten (Bank + Krypto) sehen | Cashflow-Report Juni–Nov enthält die Krypto-Ausgaben; Swaps nicht | 🟡 (Report da, Krypto fehlt) |
| D2 | **Ausgaben je Kategorie** über alle Konten sehen | Kategorien-Report enthält die kategorisierten Krypto-Ausgaben | 🟡 |
| D3 | **Vermögensentwicklung** inklusive Krypto über die Zeit sehen | Net-Worth-Report enthält Krypto-Konten mit Monatswerten | 🟡 |
| D4 | im Cryptoboard einen **korrekten** Gewinn/Verlust sehen | TRX-Einstände nachgetragen (Quelle klären), realisierter Gewinn plausibel statt +18.164 € | ❌ |

## 5. Was ausdrücklich NICHT Teil dieses Ziels ist
- Steuerbericht/Steuerformulare (eigenes Vorhaben, setzt D4 voraus).
- Automatische Kategorisierung der Krypto-Zahlungen (Till weist selbst zu; Vorschläge später möglich).
- Verbesserte Datenpflege allgemein (Rechnungs-Upload-Komfort, Massenbearbeitung) – laut Till „später“;
  **C2 (Beleg zuordnen) gehört aber dazu.**
- Schreibzugriff des Haushaltsbuchs auf Cryptoboard-Daten (Cryptoboard bleibt Quelle).

## 6. Offene Fragen an Till
1. **Zahlungsdienst:** Welcher Dienst/welche Karte steckt hinter den USDC-Abgängen? Gibt es dort einen Export (CSV/PDF)? (Hilft später beim Zuordnen von Belegen; für B2 nicht nötig.)
2. **TRX-Einstände (D4):** Woher kamen die TRX ursprünglich (Börse? Mining? Kauf)? Gibt es Belege/Exporte mit Kaufpreis?
3. **Girokonto (A1):** Soll das Girokonto gleich mit rein (Kontoauszug-Import CSV/PDF ist vorhanden)?
4. **Die 3 ungepaarten TRX-Abgänge** (31.05. 1000, 03.08. 3500, 03.10. 450 TRX): Was waren die?

## 7. Reihenfolge
A → B → C → D. Jede Etappe ist einzeln abnehmbar. Gebaut wird erst, wenn **die Kern-Arbeitsweise steht**
(Task „Arbeitsweise fest im Kern“: Zieldokument + Originalauftrag + Abnahme per Skript).
