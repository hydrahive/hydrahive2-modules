# Cryptoboard — Maximalausbau zum Crypto-Management-Cockpit

Status: **✅ Vollständig umgesetzt (v1.1.0)** · Cost-Basis-Methode: **FIFO** · Default-Währung: **EUR**

> Alle 4 Phasen sind auf `main` gemergt:
> 1. Portfolio-Core (FIFO-Ledger, Trade-Log, P&L) — Commit `4034991`
> 2. Analyse (Indikatoren, Sentiment, Compare) — Commit `5813d00`
> 3. Alerts-Ausbau (Preis-/Portfolio-Alarme, In-App-Benachrichtigung) — Commit `e7de8aa`
> 4. Agent-Tools (query_portfolio, query_crypto_analysis) — Commit `f95b7fe`
>
> 112 Backend-Tests grün · TSC + Vite-Build grün · alle Dateien ≤ 200 Zeilen.

## Was

Erweiterung des bestehenden Cryptoboard-Moduls (Kurse/Charts/News/Watchlist/Alerts)
zu einem vollständigen privaten Crypto-Verwaltungs-Cockpit:

1. **Portfolio / Holdings** — Bestände pro User, berechnet aus einem Transaktions-Ledger.
2. **Manuelles Trade-Log** — Buy / Sell / Transfer-in / Transfer-out von Hand erfassen.
3. **P&L & Kennzahlen** — realisierter & unrealisierter Gewinn (FIFO), Allocation, Gesamtwert.
4. **Technische Indikatoren** — RSI, MACD, SMA/EMA als Chart-Overlay.
5. **Sentiment** — Fear & Greed Index (alternative.me).
6. **Vergleichs-View** — mehrere Coins nebeneinander (Preis-Charts normalisiert).
7. **Alerts-Ausbau** — Portfolio-Wert-Alerts, %-Change-Condition, TeamChat-Action.
8. **Agent-Tools** — `query_portfolio`, `query_crypto_analysis`.

## Warum

Till verwaltet reale, nennenswerte Crypto-Bestände und will sie zentral in HydraHive
führen: Bestände, Performance, Analyse, News, Sentiment und Alarme an einem Ort —
**ohne** Autotrading, **ohne** Wallet-/Exchange-Zugriff, **ohne** Handels-API-Keys.
Reines manuelles Tracking + Analyse + Benachrichtigung.

## Nicht-Ziele (explizit ausgeschlossen)

- ❌ Automatischer Handel / Order-Ausführung
- ❌ Wallet-Anbindung / On-Chain-Signing / Private Keys
- ❌ Exchange-API-Keys mit Trade-Rechten
- ❌ Steuer-Report als Rechtsdokument (FIFO-Berechnung ja, aber „ohne Gewähr")

## Wie (grob)

### Datenmodell — Transaktions-Ledger (Option B)

Neue Migration `002_portfolio.sql`, additiv, Prefix `module_cryptoboard_`:

```sql
-- Transaktionen (Ledger). Holdings & P&L werden daraus berechnet.
CREATE TABLE IF NOT EXISTS module_cryptoboard_transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT    NOT NULL,
    coin_id     TEXT    NOT NULL,
    symbol      TEXT    NOT NULL DEFAULT '',
    kind        TEXT    NOT NULL,            -- buy | sell | transfer_in | transfer_out
    quantity    REAL    NOT NULL,            -- > 0
    price       REAL    NOT NULL DEFAULT 0,  -- Stückpreis in `vs` (transfer: 0 erlaubt)
    fee         REAL    NOT NULL DEFAULT 0,  -- Gebühr in `vs`
    vs          TEXT    NOT NULL DEFAULT 'eur',
    executed_at TEXT    NOT NULL,            -- ISO, vom User wählbar (für FIFO-Reihenfolge)
    note        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_tx_user
    ON module_cryptoboard_transactions("user");
CREATE INDEX IF NOT EXISTS idx_cryptoboard_tx_user_coin
    ON module_cryptoboard_transactions("user", coin_id);

-- Erweiterte Alerts (eigenständig, neben den bestehenden Butler-Flows).
CREATE TABLE IF NOT EXISTS module_cryptoboard_alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT    NOT NULL,
    kind        TEXT    NOT NULL,            -- price_above | price_below | pct_change_24h | portfolio_above | portfolio_below
    coin_id     TEXT    NOT NULL DEFAULT '', -- leer bei portfolio_*
    threshold   REAL    NOT NULL,
    vs          TEXT    NOT NULL DEFAULT 'eur',
    channel     TEXT    NOT NULL DEFAULT 'teamchat', -- teamchat | email
    active      INTEGER NOT NULL DEFAULT 1,
    last_fired  TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_alerts_user
    ON module_cryptoboard_alerts("user");
```

### Backend-Dateien (je ≤ 200 Zeilen, eine Verantwortung)

| Datei | Verantwortung |
|-------|---------------|
| `backend/portfolio_store.py` | CRUD auf Transaktionen, user-scoped, Limit |
| `backend/fifo.py` | **Reine** FIFO-Cost-Basis-Engine (keine DB, keine HTTP) — testbar isoliert |
| `backend/portfolio.py` | Holdings + P&L aggregieren (Ledger × Live-Preise) |
| `backend/portfolio_routes.py` | `/portfolio/*` Routen |
| `backend/indicators.py` | RSI / MACD / SMA / EMA aus Preisreihen (reine Funktionen) |
| `backend/sentiment.py` | Fear & Greed Index (alternative.me), gecacht |
| `backend/alerts_store.py` | CRUD erweiterte Alerts |
| `backend/alerts_routes.py` | `/alerts/*` Routen + Manager |
| (erweitern) `backend/client.py` | ggf. `simple_price` für Portfolio-Bulk |
| (erweitern) `backend/crypto_tool.py` | + `query_portfolio`, `query_crypto_analysis` |
| (erweitern) `backend/alerts.py` | Poller prüft auch DB-Alerts, TeamChat-Action |
| (erweitern) `backend/routes.py` | + `/indicators/{id}`, `/sentiment` |

### API-Endpunkte (neu)

```
GET    /portfolio                       -> Holdings + P&L-Summary
GET    /portfolio/transactions          -> Ledger (paginiert)
POST   /portfolio/transactions          -> neue Transaktion
PATCH  /portfolio/transactions/{id}     -> bearbeiten
DELETE /portfolio/transactions/{id}     -> löschen
GET    /portfolio/coin/{coin_id}        -> Detail-P&L eines Coins (FIFO-Lots)
GET    /indicators/{coin_id}?days=&vs=  -> { rsi, macd, sma, ema, series }
GET    /sentiment                       -> Fear & Greed (value, classification)
GET    /alerts                          -> Alert-Liste
POST   /alerts                          -> Alert anlegen
PATCH  /alerts/{id}                     -> aktiv/threshold ändern
DELETE /alerts/{id}                     -> löschen
```

### Frontend-Views (neu/erweitert)

| Datei | Inhalt |
|-------|--------|
| `frontend/views/PortfolioView.tsx` | Holdings-Tabelle, Gesamtwert, P&L-Cards, Allocation-Donut |
| `frontend/views/TradeLogView.tsx` | Transaktions-Historie + Eingabe-Form (Buy/Sell/Transfer) |
| `frontend/views/CompareView.tsx` | Multi-Coin-Vergleich (normalisierte Charts) |
| `frontend/views/AlertsView.tsx` | Alert-Manager |
| `frontend/components/PnlCard.tsx`, `AllocationDonut.tsx`, `TxForm.tsx`, `IndicatorPanel.tsx`, `FearGreedGauge.tsx`, `CompareChart.tsx` | UI-Bausteine |
| (erweitern) `frontend/views/CoinDetailView.tsx` | Indikator-Overlay + „Trade hinzufügen" |
| (erweitern) `frontend/CryptoboardApp.tsx`, `index.tsx`, `api.ts`, `types.ts` | Routing, Nav, i18n, API, Typen |

### FIFO-Logik (Kernstück)

- Transaktionen pro Coin nach `executed_at` aufsteigend sortiert.
- `buy` / `transfer_in` → neues Lot (qty, unit_cost inkl. anteiliger Fee) auf Stack.
- `sell` / `transfer_out` → Lots in FIFO-Reihenfolge abbauen; realisierter P&L =
  Erlös − Cost-Basis der verbrauchten Lots.
- Übrig bleibende Lots = aktuelle Holdings mit gewichteter Cost-Basis.
- Unrealisierter P&L = (Live-Preis − Cost-Basis) × Restmenge.
- Sell über Bestand → Fehler `insufficient_holdings` (keine Negativ-Bestände).
- Reine Funktionen in `fifo.py`, keine I/O → vollständig unit-testbar.

## Akzeptanzkriterien

- [ ] Transaktion anlegen/bearbeiten/löschen funktioniert, strikt user-scoped.
- [ ] Holdings & Gesamtwert stimmen mit manueller FIFO-Rechnung überein (Tests).
- [ ] Realisierter P&L korrekt nach FIFO bei Teilverkäufen über mehrere Lots.
- [ ] Unrealisierter P&L = (Live − Cost-Basis) × Menge; Allocation summiert auf 100 %.
- [ ] Sell über Bestand wird abgelehnt (`insufficient_holdings`).
- [ ] Indikatoren (RSI/MACD/SMA/EMA) liefern plausible Werte gegen Referenz-Reihe.
- [ ] Fear & Greed wird abgerufen, gecacht, fällt bei Upstream-Fehler sauber aus.
- [ ] Compare-View zeigt ≥2 Coins normalisiert über wählbaren Zeitraum.
- [ ] Alerts: anlegen, feuern (Poller), TeamChat-Nachricht, kein Doppel-Feuern.
- [ ] Agent-Tools `query_portfolio` / `query_crypto_analysis` liefern korrekt.
- [ ] Alle neuen Dateien ≤ ~200 Zeilen; bestehende Tests grün + neue Tests grün.
- [ ] Keine echten Netz-Calls in Tests (gemockt wie bestehend).

## Lieferung in 4 Phasen (je 1 PR)

1. **Portfolio-Core** — Migration, `fifo.py`, `portfolio_store.py`, `portfolio.py`,
   `portfolio_routes.py`, PortfolioView + TradeLogView, Tests. ← Herzstück
2. **Analyse** — `indicators.py`, `sentiment.py`, IndicatorPanel, FearGreedGauge,
   CompareView, Tests.
3. **Alerts-Ausbau** — `alerts_store.py`, `alerts_routes.py`, Poller-Erweiterung,
   TeamChat-Action, AlertsView, Tests.
4. **Agent-Tools** — `query_portfolio`, `query_crypto_analysis`, Tests.
