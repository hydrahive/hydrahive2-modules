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

export interface LoyaltyProviderStatus {
  lidl_plus: { enabled: boolean; experimental: true }
  payback: { enabled: boolean; experimental: true }
}

export interface LidlAuthStartResult {
  authorization_url: string
  flow_token: string
  expires_at: string
}

export interface LidlAuthCompleteRequest {
  flow_token: string
  callback_url: string
  alias?: string
  visibility: "owner"
}

export interface LoyaltyReceipt {
  id: number
  connection_id: number
  provider_receipt_id: string
  merchant_name: string
  store_id: string | null
  store_name: string | null
  store_address: string | null
  purchased_at: string | null
  total_minor: number | null
  currency: string | null
  total_discount_minor: number | null
  validation_status: "valid" | "needs_review"
  warnings: string[]
  first_seen_at: string
  last_seen_at: string
}

export interface LoyaltyReceiptItem {
  id: number
  sequence: number
  original_name: string
  gtin: string | null
  quantity: string | null
  unit: "piece" | "kg" | null
  unit_price_minor: number | null
  total_minor: number | null
  tax_group: string | null
  is_return: boolean
}

export interface LoyaltyReceiptAdjustment {
  id: number
  item_id: number | null
  kind: "discount" | "coupon" | "deposit" | "rounding"
  amount_minor: number
  description: string | null
}

export interface LoyaltyReceiptDetail extends LoyaltyReceipt {
  items: LoyaltyReceiptItem[]
  adjustments: LoyaltyReceiptAdjustment[]
}
