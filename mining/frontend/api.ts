import { api } from "@/shared/api-client"

const BASE = "/modules/mining"

export interface CoinRow {
  coin: string
  name: string
  algo: string
  fee: number
  fee_type: string
  price_usd: number | null
  estimated: boolean
  hashrate: number | null
  usd_day: number | null
  eur_day: number | null
}

export interface Overview {
  gpu: string
  fetched_at: string | null
  usd_per_eur: number | null
  rows: CoinRow[]
  reference: { source: string; fetched: string; note: string }
}

export interface Gpu {
  id: string
  name: string
  vendor: string
  watts: number
}

export interface MiningConfig {
  kryptex_user: string
  region: string
  switch_threshold: number
  min_runtime_min: number
  prop_discount: number
}

export interface Rig {
  id: string
  name: string
  status: "pending" | "active" | "revoked"
  enabled: number
  hostname: string | null
  os: string | null
  client_version: string | null
  gpu_vendor: string | null
  gpu_model: string | null
  gpu_mem_mb: number | null
  driver: string | null
  remote_ip: string | null
  last_seen: string | null
  last_report: { miner?: string; temp_c?: number | null; power_w?: number | null; util_pct?: number | null } | null
}

export interface Pairing {
  code: string
  name: string
  expires_at: string
  server: string
  pin: string | null
  command: string
}

export const REGIONS = ["global", "eu", "us", "br", "sg", "hk", "ru", "ae"] as const

export const miningApi = {
  overview: (gpu: string) => api.get<Overview>(`${BASE}/overview?gpu=${encodeURIComponent(gpu)}`),
  gpus: () => api.get<Gpu[]>(`${BASE}/gpus`),
  config: () => api.get<MiningConfig>(`${BASE}/config`),
  saveConfig: (c: Partial<MiningConfig>) => api.put<MiningConfig>(`${BASE}/config`, c),
  refresh: () => api.post<{ coins: number }>(`${BASE}/refresh`, {}),
  rigs: () => api.get<Rig[]>(`${BASE}/rigs`),
  pair: (name: string) => api.post<Pairing>(`${BASE}/rigs/pairing`, { name }),
  approve: (id: string) => api.post<{ ok: boolean }>(`${BASE}/rigs/${id}/approve`, {}),
  revoke: (id: string) => api.post<{ ok: boolean }>(`${BASE}/rigs/${id}/revoke`, {}),
  setEnabled: (id: string, enabled: boolean) => api.post<{ ok: boolean }>(`${BASE}/rigs/${id}/enabled`, { enabled }),
  remove: (id: string) => api.delete<{ ok: boolean }>(`${BASE}/rigs/${id}`),
}
