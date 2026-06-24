# Cryptoboard — Wertverlauf & Auswertungen (Option C)

Status: **Genehmigt** · Basis: nur Marktwert (EUR), KEIN P&L/Einstandskosten

## Was

Auswertungs-Dashboard für das Portfolio auf reiner **Marktwert-Basis**:
1. **Portfolio-Wert-Verlauf** — Chart „Gesamtwert über Zeit" ab erster Transaktion
2. **Wertänderung** — 24h / 7d / 30d / 1J (absolut + %)
3. **Allzeithoch** — höchster Portfolio-Wert + Datum
4. **Wert je Coin** — heutiger Wert + Allocation (gibt es teils schon)

## Warum

Alle Coins stammen aus Mining (kein Kaufpreis, keine nachvollziehbaren Tausch-
Pfade). Echter Gewinn/Verlust ist daher nicht berechenbar und auch nicht
gewünscht. Sinnvoll ist die **Wertentwicklung**: „Was war mein Bestand wann
wert." Reine Markt-Bewertung, ehrlich, ohne Cost-Basis-Fiktion.

## Nicht-Ziele

- ❌ Realisierter/unrealisierter P&L, Einstandskosten, Steuer-Aussagen
- ❌ Intraday-Auflösung (CoinGecko Free = Tageskurse)
- ❌ Tausch-Rekonstruktion zwischen Coins

## Wie (grob)

### Datenquelle: historische Tageskurse
- `client.market_chart(coin_id, "eur", "max")` liefert `[[ts_ms, price], …]` in
  Tagesauflösung über die gesamte Historie.
- Historische Kurse ändern sich **nie** → einmal holen, dauerhaft in DB cachen.

### Neue Migration `005_price_history.sql`
```sql
CREATE TABLE IF NOT EXISTS module_cryptoboard_price_history (
    coin_id  TEXT NOT NULL,
    day      TEXT NOT NULL,          -- ISO-Datum YYYY-MM-DD
    price    REAL NOT NULL,          -- Tageskurs in EUR
    PRIMARY KEY (coin_id, day)
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_pricehist_coin
    ON module_cryptoboard_price_history(coin_id);
```
Global (nicht user-scoped) — Kurse sind öffentlich, für alle gleich.

### Backend-Dateien (≤200 Zeilen, eine Verantwortung)
| Datei | Verantwortung |
|-------|---------------|
| `price_history_store.py` | Cache lesen/schreiben (coin_id, day → price), fehlende Tage ermitteln |
| `price_history.py` | CoinGecko-Fetch + Cache-Befüllung (max-Range, Tages-Buckets) |
| `valuation.py` | reine Logik: Ledger + Tageskurse → tägliche Bestände → Wertreihe |
| `valuation_routes.py` | `/portfolio/history`, `/portfolio/stats` |

### Kern-Algorithmus (valuation.py, rein/testbar)
1. Aus dem Ledger pro Coin die **kumulative Bestandsmenge je Tag** bilden
   (Σ Zugänge − Σ Abgänge bis zu diesem Tag; netto, ≥ 0 — wie im FIFO-Fix).
2. Zeitachse: erster Transaktionstag … heute, in Tagesschritten.
3. Pro Tag: Σ über Coins (Bestand[coin][tag] × Tageskurs[coin][tag]) = Tageswert.
4. Tage ohne Kurs (Wochenende/Lücke): letzten bekannten Kurs forward-fillen.

### API
```
GET /portfolio/history          -> { points: [{day, value}], currency }
GET /portfolio/stats            -> { current, ath:{value,day},
                                      change_24h, change_7d, change_30d, change_1y }
POST /portfolio/history/refresh -> historische Kurse für alle Coins (nach)laden
```
`refresh` befüllt den Cache (rate-limit-schonend, nur fehlende Coins/Tage).

### Frontend
| Datei | Inhalt |
|-------|--------|
| `views/AnalyticsView.tsx` | neuer Tab „Auswertung": Wertverlauf-Chart + Stat-Cards |
| `components/ValueChart.tsx` | Flächen-Chart Gesamtwert über Zeit (recharts) |
| `components/StatCard.tsx` | Kennzahl-Kachel (Änderung 24h/7d/30d/1J, ATH) |
| erweitern: `CryptoboardApp.tsx`, `api.ts`, `types.ts`, `index.tsx` (Nav+i18n) |

Beim ersten Öffnen: wenn Cache leer → Hinweis „Kursdaten werden geladen" +
`refresh` anstoßen, dann Chart rendern.

## Akzeptanzkriterien
- [ ] Wertverlauf-Chart ab erster Transaktion bis heute, Tagesauflösung
- [ ] Tageswert = Σ (Bestand × historischer Tageskurs), Lücken forward-filled
- [ ] Stats: aktueller Wert, ATH+Datum, Änderung 24h/7d/30d/1J korrekt
- [ ] Historische Kurse dauerhaft gecacht (zweiter Aufruf ohne API-Call)
- [ ] valuation.py rein/ohne I/O → Unit-Tests gegen bekannte Reihen
- [ ] Tests mocken CoinGecko (kein echter Traffic)
- [ ] Alle Dateien ≤200 Zeilen
- [ ] Kein P&L/Einstand in der Auswertung (nur Marktwert)

## Lieferung in 2 Phasen
1. **Wertverlauf-Core**: Migration, price_history_store/fetch, valuation,
   Routes, AnalyticsView + ValueChart, Tests.
2. **Stats**: ATH + Änderungs-Kennzahlen, StatCards.
