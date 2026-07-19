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

export interface PaybackBridgeStartResult {
  flow_id: string
  pairing_code: string
  expires_at: string
  import_path: string
}

export interface PaybackBridgeStatus {
  flow_id: string
  status: "pending" | "consumed" | "expired"
  expires_at: string
  connection?: LoyaltyConnection
}

export interface PaybackExtensionPackage {
  filename: string
  sha256: string
  base64: string
}

export interface PaybackBalance {
  id: number
  observed_at: string
  available_points: number
  money_value_minor: number | null
  money_value_currency: string | null
  valuation_version: string | null
  created_at: string
}

export interface PaybackExpiration {
  id: number
  expiration_date: string
  points: number
  status: "scheduled" | "expired" | "cancelled"
  provider_updated_at: string | null
  first_seen_at: string
  last_seen_at: string
}

export interface PaybackActivity {
  id: number
  provider_activity_id: string | null
  activity_type: "earn" | "redeem" | "expire" | "reversal" | "adjustment"
  activity_date: string
  points_delta: number
  partner_id: number | null
  partner_name: string | null
  original_description: string | null
  purchase_amount_minor: number | null
  purchase_currency: string | null
  provider_updated_at: string | null
  first_seen_at: string
  last_seen_at: string
  remote_status: string
}

export interface PaybackCoupon {
  id: number
  provider_coupon_id: string | null
  partner_id: number | null
  partner_name: string | null
  title: string
  description: string | null
  valid_from: string | null
  valid_until: string | null
  activation_status: "available" | "activated" | "redeemed" | "expired" | "unavailable"
  multiplier: string | null
  bonus_points: number | null
  condition_text: string | null
  first_seen_at: string
  last_seen_at: string
  provider_updated_at: string | null
  remote_status: string
}

export interface PaybackPartner {
  id: number
  provider_partner_id: string
  name: string
  active: 0 | 1
  first_seen_at: string
  last_seen_at: string
}

export interface PaybackMetrics {
  activity_count: number
  points_collected: number
  points_redeemed: number
  partner_frequency: { partner_id: number; name: string; activity_count: number }[]
  purchase_totals: { currency: string; amount_minor: number; activity_count: number }[]
  coupon_status: Record<string, number>
}

export interface PaybackDataResult {
  connection: LoyaltyConnection
  latest_balance: PaybackBalance | null
  balance_history: PaybackBalance[]
  expirations: PaybackExpiration[]
  activities: PaybackActivity[]
  coupons: PaybackCoupon[]
  partners: PaybackPartner[]
  metrics: PaybackMetrics
  limits: {
    balance_history: number
    expirations: number
    activities: number
    coupons: number
    partners: number
  }
}
