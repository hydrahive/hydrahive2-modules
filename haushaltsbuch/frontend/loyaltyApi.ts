import { api } from "@/shared/api-client"
import type {
  LidlAuthCompleteRequest, LidlAuthStartResult, LoyaltyConnection, LoyaltyProviderStatus,
  LoyaltyReceipt, LoyaltyReceiptDetail, LoyaltySyncResult, LoyaltySyncRun, PaybackBridgeStartResult,
  PaybackBridgeStatus, PaybackDataResult, PaybackExtensionPackage,
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
  startPaybackBridge: () => api.post<PaybackBridgeStartResult>(`${BASE}/payback/bridge/start`, {
    accepted_experimental_risk: true,
    alias: "PAYBACK",
    visibility: "owner",
  }),
  paybackBridgeStatus: (flowId: string) =>
    api.get<PaybackBridgeStatus>(`${BASE}/payback/bridge/status/${encodeURIComponent(flowId)}`),
  paybackExtensionPackage: () =>
    api.get<PaybackExtensionPackage>(`${BASE}/payback/bridge/extension-package`),
  paybackData: (connectionId: number) =>
    api.get<PaybackDataResult>(`${BASE}/payback/connections/${connectionId}/data`),
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
