import { api } from "@/shared/api-client"

const BASE = "/modules/vr"

export interface Pairing {
  code: string
  name: string
  expires_at: string
  server: string
  pinned: boolean
  /** QR-Modul-Matrix (1 = dunkel), vom Server berechnet. */
  qr: number[][]
}

export interface Headset {
  id: string
  name: string
  paired_at: string
}

export const vrApi = {
  pair: (name: string) => api.post<Pairing>(`${BASE}/pairing`, { name }),
  headsets: () => api.get<Headset[]>(`${BASE}/headsets`),
  remove: (id: string) => api.delete<{ ok: boolean }>(`${BASE}/headsets/${id}`),
  status: () => api.get<{ headsets: number }>(`${BASE}/status`),
}
