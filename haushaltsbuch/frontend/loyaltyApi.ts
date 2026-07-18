import { api } from "@/shared/api-client"
import type {
  LidlAuthCompleteRequest, LidlAuthStartResult, LoyaltyConnection, LoyaltyProviderStatus,
  LoyaltyReceipt, LoyaltyReceiptDetail, LoyaltySyncResult, LoyaltySyncRun,
} from "./loyaltyTypes"

const BASE = "/modules/haushaltsbuch/loyalty"

export const loyaltyApi = {
  connections: () => api.get<LoyaltyConnection[]>(`${BASE}/connections`),
  providerStatus: () => api.get<LoyaltyProviderStatus>(`${BASE}/provider-status`),
  startLidlAuth: () => api.post<LidlAuthStartResult>(`${BASE}/lidl/auth/start`, {
    accepted_experimental_risk: true,
    country_code: "DE",
    language_code: "de",
  }),
  completeLidlAuth: (body: LidlAuthCompleteRequest) =>
    api.post<LoyaltyConnection>(`${BASE}/lidl/auth/complete`, body),
  receipts: () => api.get<LoyaltyReceipt[]>(`${BASE}/receipts`),
  receipt: (id: number) => api.get<LoyaltyReceiptDetail>(`${BASE}/receipts/${id}`),
  sync: (id: number) => api.post<LoyaltySyncResult>(`${BASE}/connections/${id}/sync`, {}),
  syncRuns: (id: number) => api.get<LoyaltySyncRun[]>(`${BASE}/connections/${id}/sync-runs`),
  update: (
    id: number,
    body: Pick<LoyaltyConnection, "alias" | "visibility" | "revision">,
  ) => api.put<LoyaltyConnection>(`${BASE}/connections/${id}`, body),
  remove: (id: number, revision: number) =>
    api.delete<void>(`${BASE}/connections/${id}?revision=${revision}`),
}
