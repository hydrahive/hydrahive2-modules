import { api } from "@/shared/api-client"
import type {
  Account, AccountCreate, AccountUpdate, AuditEvent, Budget, BudgetCreate, BudgetUpdate,
  Category, CategoryCreate, CategoryUpdate, Dashboard, Forecast, Household, HouseholdCreate,
  ImportBatch, ImportProfile, ImportProfileCreate, ImportProfileUpdate, ImportRow,
  ImportRowUpdate, ImportUpload, Invite, Member, RecurringCreate, RecurringRule,
  RecurringUpdate, Transaction, TransactionCreate, TransactionFilters,
} from "./types"

const BASE = "/modules/haushaltsbuch"
const query = (values: object) => {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)) })
  const encoded = params.toString()
  return encoded ? `?${encoded}` : ""
}

export const haushaltsbuchApi = {
  household: () => api.get<Household>(`${BASE}/household`),
  createHousehold: (body: HouseholdCreate) => api.post<Household>(`${BASE}/household`, body),
  updateHousehold: (body: HouseholdCreate & { revision: number }) => api.put<Household>(`${BASE}/household`, body),
  addMember: (username: string) => api.post<Member>(`${BASE}/household/members`, { username }),
  removeMember: (id: number, revision: number) => api.delete<void>(`${BASE}/household/members/${id}?revision=${revision}`),
  transferOwnership: (member_id: number, revision: number) => api.post<Member>(`${BASE}/household/ownership`, { member_id, revision }),
  invites: () => api.get<Invite[]>(`${BASE}/household/invites`),
  createInvite: (expires_in_hours = 24) => api.post<Invite>(`${BASE}/household/invites`, { expires_in_hours }),
  revokeInvite: (id: number, revision: number) => api.delete<void>(`${BASE}/household/invites/${id}?revision=${revision}`),
  acceptInvite: (code: string) => api.post<Member>(`${BASE}/household/invites/accept`, { code }),
  exportHousehold: () => api.get<Record<string, unknown>>(`${BASE}/household/export`),
  deleteHousehold: (household_name: string) => api.post<void>(`${BASE}/household/delete`, { confirmation: "DELETE", household_name }),

  accounts: (include_archived = false) => api.get<Account[]>(`${BASE}/accounts${query({ include_archived })}`),
  createAccount: (body: AccountCreate) => api.post<Account>(`${BASE}/accounts`, body),
  updateAccount: (id: number, body: AccountUpdate) => api.put<Account>(`${BASE}/accounts/${id}`, body),
  categories: (include_archived = false) => api.get<Category[]>(`${BASE}/categories${query({ include_archived })}`),
  createCategory: (body: CategoryCreate) => api.post<Category>(`${BASE}/categories`, body),
  updateCategory: (id: number, body: CategoryUpdate) => api.put<Category>(`${BASE}/categories/${id}`, body),

  transactions: (filters: TransactionFilters = {}) => api.get<Transaction[]>(`${BASE}/transactions${query(filters)}`),
  transaction: (id: number) => api.get<Transaction>(`${BASE}/transactions/${id}`),
  createTransaction: (body: TransactionCreate) => api.post<Transaction>(`${BASE}/transactions`, body),
  reverseTransaction: (id: number, revision: number) => api.post<Transaction>(`${BASE}/transactions/${id}/reverse`, { revision }),

  importProfiles: () => api.get<ImportProfile[]>(`${BASE}/import-profiles`),
  createImportProfile: (body: ImportProfileCreate) => api.post<ImportProfile>(`${BASE}/import-profiles`, body),
  updateImportProfile: (id: number, body: ImportProfileUpdate) => api.put<ImportProfile>(`${BASE}/import-profiles/${id}`, body),
  deleteImportProfile: (id: number, revision: number) => api.delete<void>(`${BASE}/import-profiles/${id}?revision=${revision}`),
  imports: () => api.get<ImportBatch[]>(`${BASE}/imports`),
  importBatch: (id: number) => api.get<ImportBatch>(`${BASE}/imports/${id}`),
  createImport: ({ file, account_id, format, csv_mapping, profile_id }: ImportUpload) => {
    const form = new FormData()
    form.append("file", file, file.name)
    form.append("account_id", String(account_id))
    form.append("format", format)
    if (csv_mapping) form.append("mapping", JSON.stringify(csv_mapping))
    if (profile_id) form.append("profile_id", String(profile_id))
    return api.postForm<ImportBatch>(`${BASE}/imports`, form)
  },
  updateImportRow: (batchId: number, rowId: number, body: ImportRowUpdate) => api.patch<ImportRow>(`${BASE}/imports/${batchId}/rows/${rowId}`, body),
  completeImport: (id: number, revision: number) => api.post<ImportBatch>(`${BASE}/imports/${id}/complete`, { revision }),
  reverseImport: (id: number, revision: number) => api.post<ImportBatch>(`${BASE}/imports/${id}/reverse`, { revision }),

  budgets: (active_only = true) => api.get<Budget[]>(`${BASE}/budgets${query({ active_only })}`),
  createBudget: (body: BudgetCreate) => api.post<Budget>(`${BASE}/budgets`, body),
  updateBudget: (id: number, body: BudgetUpdate) => api.put<Budget>(`${BASE}/budgets/${id}`, body),

  recurring: (include_inactive = false) => api.get<RecurringRule[]>(`${BASE}/recurring${query({ include_inactive })}`),
  createRecurring: (body: RecurringCreate) => api.post<RecurringRule>(`${BASE}/recurring`, body),
  updateRecurring: (id: number, body: RecurringUpdate) => api.put<RecurringRule>(`${BASE}/recurring/${id}`, body),
  forecast: (days: 30 | 90 | 365) => api.get<Forecast>(`${BASE}/forecast?days=${days}`),
  dashboard: () => api.get<Dashboard>(`${BASE}/dashboard`),
  audit: (limit = 100, offset = 0) => api.get<AuditEvent[]>(`${BASE}/audit?limit=${limit}&offset=${offset}`),
}

export function isConflict(error: unknown): boolean {
  return error instanceof Error && (error as Error & { status?: number }).status === 409
}
export function isNotFound(error: unknown): boolean {
  return error instanceof Error && (error as Error & { status?: number }).status === 404
}
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unbekannter Fehler"
}
