import { api } from "@/shared/api-client"
import type { LoyaltyConnection, LoyaltySyncResult, LoyaltySyncRun } from "./loyaltyTypes"

const BASE = "/modules/haushaltsbuch/loyalty"

export const loyaltyApi = {
  connections: () => api.get<LoyaltyConnection[]>(`${BASE}/connections`),
  sync: (id: number) => api.post<LoyaltySyncResult>(`${BASE}/connections/${id}/sync`, {}),
  syncRuns: (id: number) => api.get<LoyaltySyncRun[]>(`${BASE}/connections/${id}/sync-runs`),
  update: (
    id: number,
    body: Pick<LoyaltyConnection, "alias" | "visibility" | "revision">,
  ) => api.put<LoyaltyConnection>(`${BASE}/connections/${id}`, body),
  remove: (id: number, revision: number) =>
    api.delete<void>(`${BASE}/connections/${id}?revision=${revision}`),
}
