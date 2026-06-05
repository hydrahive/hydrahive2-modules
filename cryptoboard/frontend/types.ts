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
