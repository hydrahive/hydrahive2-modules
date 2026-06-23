import { api } from "@/shared/api-client"
import type {
  ChartResponse, CoinDetail, CoinPnl, MarketRow, NewsItem,
  PortfolioSummary, SearchResult, Transaction, TxInput, WatchItem,
} from "./types"

const BASE = "/modules/cryptoboard"

export const cryptoApi = {
  search: (q: string): Promise<SearchResult[]> =>
    api.get<SearchResult[]>(`${BASE}/search?q=${encodeURIComponent(q)}`),

  markets: (ids: string[], vs = "eur"): Promise<MarketRow[]> =>
    ids.length === 0
      ? Promise.resolve([])
      : api.get<MarketRow[]>(`${BASE}/markets?ids=${ids.join(",")}&vs=${vs}`),

  top: (n = 10, vs = "eur"): Promise<MarketRow[]> =>
    api.get<MarketRow[]>(`${BASE}/top?n=${n}&vs=${vs}`),

  chart: (id: string, days: string, vs = "eur"): Promise<ChartResponse> =>
    api.get<ChartResponse>(`${BASE}/chart/${id}?days=${days}&vs=${vs}`),

  coin: (id: string, vs = "eur"): Promise<CoinDetail> =>
    api.get<CoinDetail>(`${BASE}/coin/${id}?vs=${vs}`),

  news: (categories?: string): Promise<NewsItem[]> =>
    api.get<NewsItem[]>(`${BASE}/news${categories ? `?categories=${encodeURIComponent(categories)}` : ""}`),

  watchlist: (): Promise<WatchItem[]> => api.get<WatchItem[]>(`${BASE}/watchlist`),

  addWatch: (coin_id: string, symbol: string, name: string): Promise<{ ok: boolean }> =>
    api.post<{ ok: boolean }>(`${BASE}/watchlist`, { coin_id, symbol, name }),

  removeWatch: (coin_id: string): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/watchlist/${coin_id}`),

  // ---- Portfolio (FIFO-Ledger, EUR) ----
  portfolio: (): Promise<PortfolioSummary> => api.get<PortfolioSummary>(`${BASE}/portfolio`),

  portfolioCoin: (coin_id: string): Promise<CoinPnl> =>
    api.get<CoinPnl>(`${BASE}/portfolio/coin/${coin_id}`),

  transactions: (coin_id?: string): Promise<Transaction[]> =>
    api.get<Transaction[]>(`${BASE}/portfolio/transactions${coin_id ? `?coin_id=${coin_id}` : ""}`),

  addTx: (tx: TxInput): Promise<{ ok: boolean; id: number }> =>
    api.post<{ ok: boolean; id: number }>(`${BASE}/portfolio/transactions`, tx),

  updateTx: (id: number, tx: TxInput): Promise<{ ok: boolean }> =>
    api.patch<{ ok: boolean }>(`${BASE}/portfolio/transactions/${id}`, tx),

  deleteTx: (id: number): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/portfolio/transactions/${id}`),
}
