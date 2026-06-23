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
