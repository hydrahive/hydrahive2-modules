# Cryptoboard — On-Chain-Wallet-Tracking (Option C, separate Ansicht)

Status: **Genehmigt** · Nur Lesen (kein Key/keine Private Keys) · separate "Wallets"-Ansicht

## Was

Nutzer hinterlegt **mehrere Wallet-Adressen pro Chain** (Base/EVM, Tron, Bitcoin)
und sieht deren **aktuelle On-Chain-Bestände**, in EUR umgerechnet. Getrennt vom
Portfolio (keine Vermischung, keine Doppelzählung).

## Warum

Bestände auf MetaMask-Adressen (USDC/ETH auf Base, TRX, BTC) automatisch sehen,
ohne manuelles Eintippen. Erweitert das Cryptoboard um echte On-Chain-Sicht.

## Verifizierte Datenquellen (alle kostenlos, keyless — getestet 2026-06-24)

| Chain | Endpoint | Holt |
|-------|----------|------|
| base | `https://mainnet.base.org` (JSON-RPC) | eth_getBalance (ETH) + eth_call balanceOf (ERC-20 wie USDC) |
| tron | `https://apilist.tronscanapi.com/api/account?address=` | TRX + TRC20-Token-Balances |
| bitcoin | `https://blockstream.info/api/address/` | BTC-Saldo (funded − spent, in Sats) |

## Nicht-Ziele
- ❌ Private Keys, Signieren, Senden — NUR Lesen
- ❌ Transaktionshistorie/Import (späteres, separates Thema)
- ❌ Vermischung mit Portfolio-Beständen
- ❌ Beliebige EVM-Chains — vorerst nur Base (erweiterbar)

## Wie (grob)

### Migration `006_addresses.sql`
```sql
CREATE TABLE IF NOT EXISTS module_cryptoboard_addresses (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"    TEXT NOT NULL,
    chain     TEXT NOT NULL,           -- base | tron | bitcoin
    address   TEXT NOT NULL,
    label     TEXT NOT NULL DEFAULT '',
    added_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE("user", chain, address)
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_addr_user
    ON module_cryptoboard_addresses("user");
```

### Backend (≤200 Zeilen/Datei, eine Verantwortung)
| Datei | Verantwortung |
|-------|---------------|
| `addresses_store.py` | CRUD Adressen, user-scoped, Limit (z.B. 100) |
| `chain_clients.py` | 3 keylose Fetcher: base_balance, tron_balance, btc_balance → einheitliches {asset, amount, coin_id} |
| `wallets.py` | Aggregation: Adressen × Bestände, Live-Kurs (client.markets) → EUR, gruppiert |
| `wallet_routes.py` | /wallets (CRUD Adressen) + /wallets/balances |
| `address_validators.py` | strikte Format-Validierung je Chain (kein URL-Schmuggel) |

Adress-Validierung (Regex, vor jedem Upstream-Call):
- base/EVM: `^0x[a-fA-F0-9]{40}$`
- tron: `^T[1-9A-HJ-NP-Za-km-z]{33}$`
- bitcoin: `^(bc1[a-z0-9]{20,80}|[13][a-km-zA-HJ-NP-Z1-9]{25,39})$`

### Balance-Cache
Kurz-TTL (5 Min) im bestehenden cache.py — On-Chain-Calls schonen, aber aktuell genug.

### Bekannte Coins je Chain (Mapping für €-Kurs)
- base: ETH (ethereum), USDC (usd-coin) — ERC-20 via Contract-Liste
- tron: TRX (tron) + TRC20 (USDT etc.)
- bitcoin: BTC (bitcoin)

### API
```
GET    /wallets              -> Adressliste des Users
POST   /wallets              -> Adresse hinzufügen {chain, address, label}
DELETE /wallets/{id}         -> Adresse entfernen
GET    /wallets/balances     -> [{chain, address, label, assets:[{symbol, amount, coin_id, price, value}]}], + total_eur
```

### Frontend
| Datei | Inhalt |
|-------|--------|
| `views/WalletsView.tsx` | neuer Tab "Wallets": Adress-Verwaltung + Bestands-Tabelle + Gesamtwert |
| `components/AddressForm.tsx` | Chain wählen + Adresse + Label eingeben |
| erweitern: CryptoboardApp/api/types/index (Nav+i18n) |

## Akzeptanzkriterien
- [ ] Mehrere Adressen pro Chain hinzufügen/löschen, strikt user-scoped
- [ ] Ungültige Adressformate werden je Chain abgelehnt (kein Upstream-Call)
- [ ] Bestände live von base/tron/bitcoin, in EUR umgerechnet, pro Coin summiert
- [ ] Separate Gesamtsumme "Wallets" (nicht mit Portfolio vermischt)
- [ ] Fehlerhafte/nicht erreichbare Chain bricht nicht die ganze Ansicht (pro Adresse isoliert)
- [ ] chain_clients in Tests gemockt (kein echter Netz-Traffic)
- [ ] Nur-Lesen: keine Private-Key-/Sign-Logik
- [ ] Alle Dateien ≤200 Zeilen

## Lieferung in 2 Phasen
1. **Adress-Verwaltung + Bestände**: Migration, store, chain_clients, wallets,
   routes, WalletsView + AddressForm, Tests.
2. (später, separat) Transaktions-Import — NICHT Teil dieser Spec.

---

# Erweiterung — ETH-Mainnet + Token-Übersicht (Option B)

Status: **Genehmigt** (2026-06-24) · additiv zur Basis oben

## Was
- **ETH-Mainnet** als vierte Chain (`ethereum`), keyless via publicnode-RPC.
- **Token-zentrierte Übersicht**: über ALLE Wallets aggregiert (Symbol → Gesamt-
  menge, EUR-Wert, auf welchen Wallets) — zusätzlich zur adressweisen Ansicht.

## Warum (entscheidender Kontext)
Till hat ~30 Tron-Wallets. „Spam-aussehende" Token waren teils **real wertvoll**
(tausende €). Daher: **nichts pauschal wegfiltern** — alle Token werden gezeigt,
nur **priorisiert** (Wert zuerst) und gekennzeichnet (verifiziert / Wert unbekannt).
Die frühere USDT-Whitelist (Filtern) ist damit **verworfen**.

## Datenquellen (getestet 2026-06-24)
| Chain | Endpoint | Holt |
|-------|----------|------|
| ethereum | `https://ethereum-rpc.publicnode.com` (JSON-RPC, keyless) | ETH + ERC-20 (USDT, USDC) via balanceOf |
| tron | Tronscan `account` (wie oben) | TRX + **alle** TRC20 inkl. `tokenPriceInTrx`, `vip`-Flag |

Live verifiziert: publicnode liefert ETH + ERC-20-Token korrekt.

## Wert-Ermittlung je Asset (Reihenfolge)
1. `coin_id` bekannt → CoinGecko-Kurs (`client.markets`)
2. sonst `price_trx` vorhanden → Tronscan-Preis × TRX-EUR-Kurs
3. sonst → **Wert unbekannt** (`value=null`) — Token bleibt **sichtbar**

## Aggregation & Sortierung (`wallets.balances`)
- Token über alle Adressen zusammengefasst: `{symbol, amount, value, value_known,
  verified, chain, wallets:[{label, chain, amount, value}]}`
- Sortierung: bekannter Wert (absteigend) → verifiziert ohne Preis → Rest.
- `total` summiert nur Token mit bekanntem Wert.

## EVM generisch
`chain_clients._EVM` (chain → RPC, native-coin, ERC-20-Liste); `evm_balance(chain, addr)`
ersetzt das frühere `base_balance`. `base` + `ethereum` teilen denselben Code.

## Frontend
- `WalletsView`: neue **Token-Übersicht**-Box (aggregiert, Token mit >1 Wallet
  aufklappbar zu den einzelnen Wallets), darunter die Adress-Verwaltung.
- Verifiziert-Badge, „Wert unbekannt" statt Ausblenden, Hinweis dass unbekannt ≠ wertlos.
- `ethereum` als Chain-Option in `AddressForm` + Validator (gleiche EVM-Regex wie Base).

## Akzeptanzkriterien (Erweiterung)
- [x] ETH-Mainnet hinzufügbar, liefert ETH + ERC-20 (live getestet)
- [x] Alle Tron-Token sichtbar — kein pauschales Filtern von „Spam"
- [x] Wert via CoinGecko ODER Tronscan price_trx; sonst „Wert unbekannt"
- [x] Token über alle Wallets aggregiert + pro Wallet aufschlüsselbar
- [x] verifiziert-Flag (Tronscan `vip`) gekennzeichnet
- [x] Tests gemockt, alle grün (232); TS-Typecheck sauber; Dateien ≤200 Z. (außer types.ts, reine Deklarationen)
