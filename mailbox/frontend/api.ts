import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { FolderRow } from "./mailFormat"
import type { ComposeMode, Draft, Prefill } from "./composeFormat"
import type { FlowStart } from "./msFlow"

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
  auth: "password" | "oauth_microsoft" | "oauth_google"
  status: "new" | "ok" | "auth_failed" | "error"
  status_detail: string
  sync?: { running: number; messages_done: number; folders_done: number; folders_total: number; finished_at: string | null; last_error: string }
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
  auth: "password" | "oauth_microsoft"
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
  account_id: string
  folder: string
  folder_id: number
  folder_role: string
  seen: number
  flagged: number
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

export interface SendResult {
  sent: boolean
  message_id: string
  refused: string[]
  sent_copy: "server" | "provider" | "archive_only"
  warning: string
}

export interface SavedDraft extends Draft {
  id: string
  updated_at: string
  server?: "ok" | "local_only"
  by_agent?: boolean
}

export type MailAction = "seen" | "unseen" | "flag" | "unflag" | "move" | "delete" | "archive" | "junk"

function withToken(path: string, extra = ""): string {
  const token = useAuthStore.getState().token ?? ""
  return `/api${BASE}${path}?token=${encodeURIComponent(token)}${extra}`
}

export type ShareLevel = "read" | "draft"
export interface Share { target: string; level: ShareLevel; name: string; created_by: string; created_at: string }
export interface ShareAudit { at: string; username: string; project_id: string; tool: string; message_id: number | null; result: string }
export interface SharesInfo { shares: Share[]; projects: { id: string; name: string }[]; audit: ShareAudit[] }

export const mailApi = {
  shares: (id: string) => api.get<SharesInfo>(`${BASE}/accounts/${encodeURIComponent(id)}/shares`),
  addShare: (id: string, target: string, level: ShareLevel = "read") =>
    api.put<Share>(`${BASE}/accounts/${encodeURIComponent(id)}/shares`, { target, level }),
  removeShare: (id: string, target: string) =>
    api.delete<void>(`${BASE}/accounts/${encodeURIComponent(id)}/shares/${encodeURIComponent(target)}`),
  accounts: () => api.get<Account[]>(`${BASE}/accounts`),
  account: (id: string) => api.get<Account>(`${BASE}/accounts/${encodeURIComponent(id)}`),
  suggest: (address: string) => api.get<Suggestion>(`${BASE}/suggest?address=${encodeURIComponent(address)}`),
  createAccount: (a: AccountIn) => api.post<Account>(`${BASE}/accounts`, a),
  updateAccount: (id: string, a: Partial<AccountIn> & { signature?: string; sender_name?: string }) =>
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
  // M2: Schreiben, Entwürfe, Aktionen
  send: (form: FormData) => api.postForm<SendResult>(`${BASE}/send`, form),
  prefill: (accountId: string, mode: Exclude<ComposeMode, "new">, ref: number) =>
    api.get<Prefill>(`${BASE}/compose/prefill?${new URLSearchParams({ account_id: accountId, mode, ref_message: String(ref) })}`),
  drafts: () => api.get<SavedDraft[]>(`${BASE}/drafts`),
  saveDraft: (d: Draft, id: string | null) =>
    id ? api.patch<SavedDraft>(`${BASE}/drafts/${encodeURIComponent(id)}`, d) : api.post<SavedDraft>(`${BASE}/drafts`, d),
  deleteDraft: (id: string) => api.delete<void>(`${BASE}/drafts/${encodeURIComponent(id)}`),
  // M1b: Microsoft-Anmeldung (App einmal global durch den Admin, Anmeldung je Konto per Geräte-Code)
  msStatus: () => api.get<{ configured: boolean }>(`${BASE}/microsoft/status`),
  msApp: () => api.get<{ client_id: string; tenant: string }>(`${BASE}/microsoft/app`),
  msSaveApp: (client_id: string, tenant: string) =>
    api.put<{ client_id: string; tenant: string }>(`${BASE}/microsoft/app`, { client_id, tenant }),
  msCheckApp: () => api.post<{ ok: boolean; error?: string; message?: string }>(`${BASE}/microsoft/app/check`, {}),
  msStart: () => api.post<FlowStart>(`${BASE}/microsoft/flows`, {}),
  msPoll: (flowId: string) => api.get<{ state: string; error?: string }>(`${BASE}/microsoft/flows/${encodeURIComponent(flowId)}`),
  msCreate: (flow_id: string, address: string, label: string) =>
    api.post<Account>(`${BASE}/microsoft/accounts`, { flow_id, address, label }),
  msReauth: (id: string, flow_id: string) =>
    api.post<Account>(`${BASE}/accounts/${encodeURIComponent(id)}/microsoft`, { flow_id }),
  act: (ids: number[], action: MailAction, target?: string) =>
    api.post<{ done: number; skipped: number }>(`${BASE}/messages/actions`, { ids, action, ...(target ? { target } : {}) }),
}
