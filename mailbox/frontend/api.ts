import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { FolderRow } from "./mailFormat"

const BASE = "/modules/mailbox"

export interface Account {
  id: string
  label: string
  address: string
  sender_name: string
  imap_host: string
  imap_port: number
  imap_tls: "ssl" | "starttls"
  smtp_host: string
  smtp_port: number
  smtp_tls: "ssl" | "starttls"
  username: string
  signature: string
  status: "new" | "ok" | "auth_failed" | "error"
  status_detail: string
  sync?: { running: number; messages_done: number; finished_at: string | null; last_error: string }
}

export interface AccountIn {
  label: string
  address: string
  imap_host: string
  imap_port: number
  imap_tls: "ssl" | "starttls"
  smtp_host: string
  smtp_port: number
  smtp_tls: "ssl" | "starttls"
  username: string
  password: string
}

export interface Suggestion {
  imap_host: string
  imap_port: number
  imap_tls: "ssl" | "starttls"
  smtp_host: string
  smtp_port: number
  smtp_tls: "ssl" | "starttls"
  hint: string
  known: boolean
}

export interface MailItem {
  id: number
  account_id: string
  account: string
  folder: string
  folder_id: number
  date: string
  from_addr: string
  to_addr: string
  subject: string
  snippet: string
  seen: number
  flagged: number
  has_attachments: boolean
  deleted_on_server: number
  thread_key: string
}

export interface MailList {
  items: MailItem[]
  total: number
  limit: number
  offset: number
  fulltext: boolean
}

export interface Attachment {
  index: number
  name: string
  type: string
  size: number
  inline: boolean
}

export interface MailDetail {
  id: number
  account: string
  folder: string
  date: string
  from_addr: string
  to_addr: string
  cc_addr: string
  subject: string
  text: string
  has_html: boolean
  attachments: Attachment[]
  deleted_on_server: number
  parse_error: string
}

function withToken(path: string, extra = ""): string {
  const token = useAuthStore.getState().token ?? ""
  return `/api${BASE}${path}?token=${encodeURIComponent(token)}${extra}`
}

export const mailApi = {
  accounts: () => api.get<Account[]>(`${BASE}/accounts`),
  account: (id: string) => api.get<Account>(`${BASE}/accounts/${encodeURIComponent(id)}`),
  suggest: (address: string) => api.get<Suggestion>(`${BASE}/suggest?address=${encodeURIComponent(address)}`),
  createAccount: (a: AccountIn) => api.post<Account>(`${BASE}/accounts`, a),
  updateAccount: (id: string, a: Partial<AccountIn> & { signature?: string }) =>
    api.patch<Account>(`${BASE}/accounts/${encodeURIComponent(id)}`, a),
  removeAccount: (id: string) => api.delete<void>(`${BASE}/accounts/${encodeURIComponent(id)}`),
  syncNow: (id: string) => api.post<{ started: boolean }>(`${BASE}/accounts/${encodeURIComponent(id)}/sync`, {}),
  folders: () => api.get<FolderRow[]>(`${BASE}/folders`),
  messages: (p: { q?: string; folder_id?: number | null; deleted?: boolean; inbox?: boolean; offset?: number; limit?: number }) => {
    const s = new URLSearchParams()
    if (p.q) s.set("q", p.q)
    if (p.folder_id != null) s.set("folder_id", String(p.folder_id))
    if (p.deleted) s.set("deleted", "true")
    if (p.inbox) s.set("inbox", "true")
    s.set("offset", String(p.offset ?? 0))
    s.set("limit", String(p.limit ?? 50))
    return api.get<MailList>(`${BASE}/messages?${s.toString()}`)
  },
  message: (id: number) => api.get<MailDetail>(`${BASE}/messages/${id}`),
  /** <iframe> kann keinen Header setzen → ?token= (Kern: require_principal_or_query). */
  htmlUrl: (id: number, images: boolean) => withToken(`/messages/${id}/html`, images ? "&images=1" : ""),
  attachmentUrl: (id: number, index: number) => withToken(`/attachments/${id}/${index}`),
  emlUrl: (id: number) => withToken(`/messages/${id}/eml`),
}
