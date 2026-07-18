export type LoyaltyProvider = "lidl_plus" | "payback"
export type LoyaltyConnectionStatus =
  | "disconnected" | "active" | "syncing" | "reauth_required"
  | "blocked" | "disabled" | "error"

export interface LoyaltyCapabilities {
  receipts?: boolean
  receipt_items?: boolean
  discounts?: boolean
  deposits?: boolean
  balance?: boolean
  expirations?: boolean
  activities?: boolean
  coupons?: boolean
  partners?: boolean
  scheduled_sync?: boolean
  token_refresh?: boolean
  remote_revoke?: boolean
}

export interface LoyaltyConnection {
  id: number
  household_id: number
  provider: LoyaltyProvider
  owner_member_id: number
  credential_ref: string
  masked_account: string
  alias: string | null
  country_code: string
  language_code: string
  visibility: "owner" | "household"
  status: LoyaltyConnectionStatus
  capabilities: LoyaltyCapabilities
  feature_enabled: boolean
  sync_enabled: boolean
  sync_interval_hours: number | null
  sync_cursor: string | null
  last_sync_at: string | null
  last_success_at: string | null
  next_sync_at: string | null
  last_error_code: string | null
  revision: number
  created_at: string
  updated_at: string
}

export interface LoyaltySyncRun {
  id: number
  connection_id: number
  trigger: "manual" | "scheduled"
  started_at: string
  finished_at: string | null
  status: "running" | "succeeded" | "partial" | "failed" | "cancelled"
  fetched_count: number
  created_count: number
  updated_count: number
  skipped_count: number
  error_code: string | null
  next_allowed_attempt_at: string | null
}

export interface LoyaltySyncResult {
  connection: LoyaltyConnection
  run: LoyaltySyncRun
}
