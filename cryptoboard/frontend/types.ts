export interface MarketRow {
  id: string
  symbol: string
  name: string
  image: string | null
  price: number | null
  market_cap: number | null
  market_cap_rank: number | null
  volume: number | null
  change_24h: number | null
  change_7d: number | null
  sparkline: number[]
}

export interface SearchResult {
  id: string
  symbol: string
  name: string
  market_cap_rank: number | null
  thumb: string | null
}

export interface CoinDetail {
  id: string
  symbol: string
  name: string
  image: string | null
  price: number | null
  market_cap: number | null
  market_cap_rank: number | null
  volume: number | null
  change_24h: number | null
  change_7d: number | null
  ath: number | null
  atl: number | null
  circulating_supply: number | null
  total_supply: number | null
  max_supply: number | null
  description: string
  homepage: string | null
}

export interface ChartResponse {
  prices: [number, number][]
}

export interface NewsItem {
  id: string
  title: string
  url: string
  source: string | null
  body: string
  image: string | null
  published_at: number | null
  categories: string | null
}

export interface WatchItem {
  coin_id: string
  symbol: string
  name: string
  added_at: string
}

export type TxKind = "buy" | "sell" | "transfer_in" | "transfer_out"

export interface Transaction {
  id: number
  coin_id: string
  symbol: string
  name: string
  kind: TxKind
  quantity: number
  price: number
  fee: number
  executed_at: string
  note: string
  created_at: string
}

export interface TxInput {
  coin_id: string
  symbol: string
  name: string
  kind: TxKind
  quantity: number
  price: number
  fee: number
  executed_at: string
  note: string
}

export interface Position {
  coin_id: string
  symbol: string
  name: string
  image: string | null
  quantity: number
  avg_cost: number
  cost_basis: number
  price: number | null
  change_24h: number | null
  value: number
  unrealized_pnl: number
  unrealized_pct: number
  realized_pnl: number
  invested: number
  proceeds: number
  allocation: number
  is_open: boolean
}

export interface PortfolioTotals {
  value: number
  cost_basis: number
  unrealized_pnl: number
  unrealized_pct: number
  realized_pnl: number
  open_count: number
  position_count: number
}

export interface PortfolioSummary {
  currency: string
  positions: Position[]
  totals: PortfolioTotals
}

export interface CoinPnl {
  coin_id: string
  currency: string
  quantity: number
  avg_cost: number
  cost_basis: number
  price: number | null
  value: number
  unrealized_pnl: number
  realized_pnl: number
  invested: number
  proceeds: number
  transactions: Transaction[]
}

export interface IndicatorData {
  times: number[]
  prices: number[]
  sma20: (number | null)[]
  sma50: (number | null)[]
  ema12: (number | null)[]
  ema26: (number | null)[]
  rsi14: (number | null)[]
  macd: (number | null)[]
  macd_signal: (number | null)[]
  macd_histogram: (number | null)[]
}

export interface FngEntry {
  value: number | null
  classification: string | null
  timestamp: number | null
}

export interface Sentiment {
  current: FngEntry | null
  history: FngEntry[]
}

export type AlertKind =
  | "price_above" | "price_below"
  | "pct_change_24h_above" | "pct_change_24h_below"
  | "portfolio_above" | "portfolio_below"

export interface Alert {
  id: number
  kind: AlertKind
  coin_id: string
  symbol: string
  threshold: number
  active: number
  last_value: number | null
  last_fired: string
  note: string
  created_at: string
}

export interface AlertInput {
  kind: AlertKind
  coin_id: string
  symbol: string
  threshold: number
  note: string
}

export interface AlertEvent {
  id: number
  alert_id: number
  kind: AlertKind
  coin_id: string
  symbol: string
  threshold: number
  value: number
  message: string
  seen: number
  created_at: string
}

export interface AlertEventsResponse {
  events: AlertEvent[]
  unseen: number
}

export interface ValuePoint {
  day: string
  value: number
}

export interface ValueHistory {
  currency: string
  points: ValuePoint[]
  missing_prices: string[]
}

export interface Delta {
  abs: number
  pct: number
}

export interface PortfolioStats {
  currency: string
  current: number
  ath: { value: number; day: string | null }
  change_24h: Delta
  change_7d: Delta
  change_30d: Delta
  change_1y: Delta
}

export type WalletChain = "base" | "ethereum" | "tron" | "bitcoin"

export interface WalletAddress {
  id: number
  chain: WalletChain
  address: string
  label: string
  added_at: string
}

export interface WalletAsset {
  symbol: string
  amount: number
  coin_id?: string | null
  value: number | null
  price_trx?: number | null
  verified?: boolean
  name?: string
  token_id?: string
}

export interface WalletTokenWallet {
  label: string
  chain: WalletChain
  amount: number
  value: number | null
}

export interface WalletTokenAgg {
  symbol: string
  amount: number
  value: number
  value_known: boolean
  verified: boolean
  chain: WalletChain
  wallets: WalletTokenWallet[]
}

export interface WalletBalanceRow {
  id: number
  chain: WalletChain
  address: string
  label: string
  assets: WalletAsset[]
}

export interface WalletBalances {
  currency: string
  tokens: WalletTokenAgg[]
  addresses: WalletBalanceRow[]
  total: number
}

export interface ImportTx {
  kind: TxKind
  symbol: string
  quantity: number
  price: number
  fee: number
  executed_at: string
  hash: string
  coin_id: string | null
  coin_name: string | null
  resolved: boolean
  duplicate: boolean
}

export interface ImportError {
  row: number
  missing: string[]
}

export interface ImportPreview {
  header: string[]
  mapping: Record<string, string | null>
  fields: string[]
  transactions: ImportTx[]
  errors: ImportError[]
  unresolved_symbols: string[]
  duplicate_count: number
}

export interface ImportResult {
  ok: boolean
  imported: number
  skipped: number
}

// ---- On-Chain-Trade-Import (Alchemy) ----
// Zahlen (quantity/price/fee) kommen als exakte Dezimal-Strings und werden
// unverändert zurückgeschickt — nie über Number() runden.
export interface AlchemyKeyStatus {
  set: boolean
  masked: string | null
}

export interface OnchainEntry {
  hash: string            // "{chain}:{tx_hash}:sell|buy" — unverändert zurückgeben
  tx_hash: string
  coin_id: string | null
  symbol: string
  name: string
  kind: "sell" | "buy" | "transfer_out"
  quantity: string
  price: string | null
  fee: string | null
  executed_at: string | null
  resolved: boolean
  preis_fehlt: boolean
  gebuehr_fehlt: boolean
  duplicate: boolean
  /** Backend-Urteil nach derselben Regel wie der Commit (1.7.0, nur Info – das UI rechnet selbst). */
  buchbar?: boolean
  nicht_buchbar_grund?: string | null
}

export interface OnchainWrap {
  hash: string
  executed_at: string | null
  assets: { symbol: string | null; contract: string | null; direction: "raus" | "rein"; amount: string | null }[]
}

export interface OnchainUnklar {
  hash: string
  chain?: string          // nur bei „alle Adressen“
  executed_at: string | null
  reason: string
  tokens: { symbol: string; contract: string | null; category: string | null; direction: "raus" | "rein" | "fremd"; amount: string | null }[]
}

export interface OnchainCounts {
  swaps: number
  transactions: number
  wraps: number
  unklar: number
  duplicates: number
  preis_fehlt: number
  gebuehr_fehlt: number
  unresolved: number
}

export interface OnchainPreview {
  chain: string
  address: string
  transactions: OnchainEntry[]
  wraps: OnchainWrap[]
  unklar: OnchainUnklar[]
  truncated: boolean
  before_block: string | null
  kurs_abruf_fehlgeschlagen: boolean
  counts: OnchainCounts
}

export interface OnchainCommitTx {
  coin_id: string
  symbol: string
  name: string
  kind: "sell" | "buy" | "transfer_out"
  quantity: string
  price: string | null    // transfer_out darf ohne Preis gebucht werden (Backend: 0)
  fee: string | null
  executed_at: string
  hash: string
}

// ---- Trades aller Adressen (preview_all, Vertrag 1.7.0) ----
export interface OnchainAddressStatus {
  id: number
  chain: string
  address: string
  label: string | null
  status: "ok" | "fehler"
  error: string | null
  truncated: boolean
  before_block: string | null
}

export interface OnchainXPair {
  id: string              // xchain:{tron_tx}:{evm_chain}:{evm_tx} = tx_hash beider Einträge
  tron_tx: string
  evm_chain: string
  evm_tx: string
  sell_at: string | null
  buy_at: string | null
  delay_seconds: number
  entries: OnchainEntry[] // sell TRX, buy z. B. USDC
}

export interface OnchainCandidate {
  evm_chain: string
  evm_tx: string
  executed_at: string | null
  symbol: string
  amount: string
  delay_seconds: number
  entries: OnchainEntry[]
}

export interface OnchainMehrdeutig {
  tron_tx: string
  executed_at: string | null
  symbol: string
  amount: string
  candidates: OnchainCandidate[]
}

export type OnchainSpamGrund = "symbol_nicht_ascii" | "url_im_namen" | "unbekannter_token"

export interface OnchainSpam {
  hash: string
  chain: string
  executed_at: string | null
  symbol: string
  contract: string | null
  amount: string | null
  grund: OnchainSpamGrund | string
}

export interface OnchainAllCounts extends OnchainCounts {
  pairs: number
  mehrdeutig: number
  ausgaben: number
  spam: number
  buchbar: number
}

export interface OnchainPreviewAll {
  addresses: OnchainAddressStatus[]
  transactions: OnchainEntry[]
  pairs: OnchainXPair[]
  mehrdeutig: OnchainMehrdeutig[]
  ausgaben: OnchainEntry[]
  spam: OnchainSpam[]
  wraps: OnchainWrap[]
  unklar: OnchainUnklar[]
  kurs_abruf_fehlgeschlagen: boolean
  window_minutes: number
  counts: OnchainAllCounts
}

export interface OnchainCommitResult {
  ok: boolean
  imported: number
  skipped: number
  skipped_details: { hash: string; reason: string }[]
}

// ── Wallet-Connect (EIP-1193 / EIP-6963) — nur Lesen: einzige erlaubte Methode eth_requestAccounts ──
export type WalletRequestMethod = "eth_requestAccounts"

export interface Eip1193Provider {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>
  on?: (event: string, handler: (...args: unknown[]) => void) => void
  removeListener?: (event: string, handler: (...args: unknown[]) => void) => void
}

export interface Eip6963ProviderInfo {
  uuid: string
  name: string
  icon: string
  rdns?: string
}

export interface Eip6963ProviderDetail {
  info: Eip6963ProviderInfo
  provider: Eip1193Provider
}

export type EvmChain = "base" | "ethereum"

export type WalletConnectFailure = "rejected" | "pending" | "error" | "no_account"
export type WalletConnectResult =
  | { ok: true; address: string }
  | { ok: false; reason: WalletConnectFailure }

export type ChainChangeOutcome =
  | { kind: "same" }
  | { kind: "offer"; chain: EvmChain }
  | { kind: "unsupported" }
