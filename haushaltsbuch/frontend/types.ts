export type Currency = string
export type IsoDate = string
export type Revision = number

export interface Member {
  id: number
  user_id: string
  username: string
  role: "owner" | "member"
  revision: Revision
  joined_at: string
}

export interface Household {
  id: number
  name: string
  base_currency: Currency
  timezone: string
  owner_user_id: string
  revision: Revision
  current_role: "owner" | "member"
  members: Member[]
  created_at?: string
  updated_at?: string
}

export interface HouseholdCreate {
  name: string
  base_currency: Currency
  timezone: string
  create_default_categories: boolean
}

export type AccountType = "checking" | "savings" | "cash" | "credit_card" | "wallet" | "liability" | "asset" | "custom"
export interface Account {
  id: number
  name: string
  type: AccountType
  owner_member_id: number | null
  currency: Currency
  bank_identifier: string | null
  balance_base: number
  archived: boolean
  revision: Revision
}
export interface AccountCreate {
  name: string
  type: AccountType
  owner_member_id: number | null
  currency: Currency
  bank_identifier: string | null
  opening_balance: number
}
export interface AccountUpdate extends Omit<AccountCreate, "currency" | "opening_balance"> {
  archived: boolean
  revision: Revision
}

export type CategoryKind = "income" | "expense"
export interface Category {
  id: number
  parent_id: number | null
  name: string
  kind: CategoryKind
  icon: string | null
  color: string | null
  sort_order: number
  archived: boolean
  revision: Revision
}
export interface CategoryCreate {
  name: string
  kind: CategoryKind
  parent_id: number | null
  icon: string | null
  color: string | null
  sort_order: number
}
export interface CategoryUpdate extends CategoryCreate { archived: boolean; revision: Revision }

export interface Posting {
  id?: number
  account_id: number | null
  category_id: number | null
  original_amount: number
  currency: Currency
  base_amount: number
  exchange_rate: string | null
  exchange_rate_date: IsoDate | null
  exchange_rate_source: string | null
  member_id: number | null
}
export interface Transaction {
  id: number
  booking_date: IsoDate
  value_date: IsoDate
  counterparty: string | null
  purpose: string | null
  note: string | null
  status: "posted" | "reversed"
  source: "manual" | "import" | "receipt" | "lidl_plus" | "payback"
  reversal_of_id: number | null
  revision: Revision
  created_at: string
  postings?: Posting[]
}
export interface TransactionCreate {
  booking_date: IsoDate
  value_date: IsoDate | null
  counterparty: string | null
  purpose: string | null
  note: string | null
  source: "manual"
  postings: Posting[]
}
export interface TransactionFilters {
  date_from?: IsoDate
  date_to?: IsoDate
  account_id?: number
  category_id?: number
  query?: string
  limit?: number
  offset?: number
}

export type BudgetType = "monthly" | "monthly_rollover" | "reserve" | "one_time" | "yearly"
export interface Budget {
  id: number
  category_id: number | null
  type: BudgetType
  amount: number
  start_date: IsoDate
  end_date: IsoDate
  warning_threshold: number
  active: boolean
  revision: Revision
  spent: number
  available_amount: number
  remaining: number
  warning: boolean
  periods: BudgetPeriod[]
}
export interface BudgetPeriod {
  id: number
  start_date: IsoDate
  end_date: IsoDate
  allocated_amount: number
  spent_amount: number
  adjustment_amount: number
  base_allocation_amount: number
  effective_spent_amount: number
  effective_allocated_amount: number
  effective_rollover_amount: number
}
export interface BudgetCreate {
  category_id: number | null
  type: BudgetType
  amount: number
  start_date: IsoDate
  end_date: IsoDate
  warning_threshold: number
}
export interface BudgetUpdate extends BudgetCreate { active: boolean; revision: Revision }

export type RecurringFrequency = "daily" | "weekly" | "monthly" | "yearly"
export interface RecurringRule {
  id: number
  kind: CategoryKind
  account_id: number
  category_id: number
  frequency: RecurringFrequency
  interval_count: number
  next_due_date: IsoDate
  end_date: IsoDate | null
  anchor_day: number | null
  amount: number
  tolerance: number
  counterparty: string | null
  cancellation_notice_days: number | null
  note: string | null
  status: "draft" | "confirmed" | "inactive"
  confidence: string
  revision: Revision
  overdue: boolean
}
export type RecurringCreate = Omit<RecurringRule, "id" | "revision" | "overdue">
export type RecurringUpdate = RecurringCreate & { revision: Revision }

export interface ForecastOccurrence {
  rule_id: number
  due_date: IsoDate
  amount: number
  effect: number
  kind: CategoryKind
  counterparty: string | null
  projected_balance: number
}
export interface Forecast {
  days: 30 | 90 | 365
  opening_balance: number
  net_change: number
  closing_balance: number
  occurrences: ForecastOccurrence[]
  warnings: { date: IsoDate; projected_balance: number }[]
}
export interface Dashboard {
  total_balance: number
  month_income: number
  month_expense: number
  budget_spent: number
  budget_amount: number
  upcoming: ForecastOccurrence[]
  forecast_30: Forecast
  forecast_90: Forecast
  recent_transactions: Transaction[]
}

export interface Invite {
  id: number
  expires_at: string
  status: "pending" | "accepted" | "revoked"
  revision: Revision
  created_at: string
  accepted_at: string | null
  code?: string
}
export interface AuditEvent {
  id: number
  actor_user_id: string
  entity_type: string
  entity_id: string
  action: string
  before: unknown
  after: unknown
  created_at: string
}

export type ImportFormat = "auto" | "camt" | "mt940" | "csv"
export type StoredImportFormat = Exclude<ImportFormat, "auto">
export type ImportBatchStatus = "draft" | "imported" | "reversed"
export type ImportRowStatus = "pending" | "accepted" | "rejected" | "duplicate" | "error" | "imported" | "reversed"
export type CsvEncoding = "utf-8" | "utf-8-sig" | "cp1252" | "iso-8859-1"
export type CsvDelimiter = ";" | "," | "\t"

export interface CsvColumnMapping {
  booking_date: string
  amount?: string | null
  debit_amount?: string | null
  credit_amount?: string | null
  value_date?: string | null
  currency?: string | null
  counterparty?: string | null
  purpose?: string | null
  bank_reference?: string | null
  counterparty_identifier?: string | null
  category_hint?: string | null
}

export interface CsvImportMapping extends CsvColumnMapping {
  delimiter: CsvDelimiter
  encoding: CsvEncoding
  decimal_separator: "." | ","
  date_format: string
}

export interface ImportProfile {
  id: number
  name: string
  delimiter: CsvDelimiter
  encoding: CsvEncoding
  decimal_separator: "." | ","
  date_format: string
  mapping: CsvColumnMapping
  revision: Revision
  created_at: string
  updated_at: string
}
export type ImportProfileCreate = Omit<ImportProfile, "id" | "revision" | "created_at" | "updated_at">
export type ImportProfileUpdate = ImportProfileCreate & { revision: Revision }

export interface ImportRow {
  id: number
  batch_id: number
  source_line: number
  booking_date: IsoDate | null
  value_date: IsoDate | null
  amount_minor: number | null
  currency: Currency | null
  counterparty: string | null
  purpose: string | null
  counterparty_identifier: string | null
  bank_reference: string | null
  category_hint: string | null
  warnings: string[]
  errors: string[]
  fingerprint_strength: "strong" | "weak"
  status: ImportRowStatus
  category_id: number | null
  suggested_category_id: number | null
  suggestion_source: "history" | "llm" | null
  suggestion_confidence: number | null
  transaction_id: number | null
  revision: Revision
  created_at: string
  updated_at: string
}

export interface ImportBatch {
  id: number
  account_id: number
  profile_id: number | null
  display_filename: string
  source_format: StoredImportFormat
  status: ImportBatchStatus
  revision: Revision
  rows_revision: Revision | 0
  created_by: string
  created_at: string
  updated_at: string
  completed_at: string | null
  reversed_at: string | null
  rows?: ImportRow[]
}

export interface ImportRowUpdate {
  revision: Revision
  status?: "pending" | "accepted" | "rejected"
  category_id?: number | null
  booking_date?: IsoDate
  value_date?: IsoDate | null
  amount_minor?: number | null
  currency?: Currency | null
  counterparty?: string | null
  purpose?: string | null
}

export interface ImportUpload {
  file: File
  account_id: number
  format: ImportFormat
  csv_mapping?: CsvImportMapping
  profile_id?: number
}
