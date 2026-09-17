import { useEffect, useState } from "react"
import { Check, FileText, MessageSquare, Paperclip, Send, UserRound } from "lucide-react"
import { useTranslation } from "react-i18next"
import { downloadAttachment, ticketsApi } from "./api"
import type { Team, Ticket, TicketAttachment, TicketPriority, TicketStatus } from "./types"

interface Props {
  ticket: Ticket
  teams: Team[]
  onUpdated: (ticket: Ticket) => void
}

const statuses: TicketStatus[] = ["open", "triaged", "in_progress", "waiting", "resolved", "closed", "cancelled"]
const priorities: TicketPriority[] = ["low", "normal", "high", "urgent"]

export function TicketDetail({ ticket, teams, onUpdated }: Props) {
  const { t } = useTranslation("tickets")
  const [comment, setComment] = useState("")
  const [attachments, setAttachments] = useState<TicketAttachment[]>(ticket.attachments ?? [])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setAttachments(ticket.attachments ?? [])
    void ticketsApi.attachments(ticket.id).then(setAttachments).catch(() => {})
  }, [ticket.id, ticket.attachments])

  async function update(patch: Partial<Ticket>) {
    setBusy(true); setError(null)
    try { onUpdated(await ticketsApi.update(ticket.id, patch)) } catch { setError(t("saveError")) } finally { setBusy(false) }
  }

  async function addComment() {
    if (!comment.trim()) return
    setBusy(true); setError(null)
    try { await ticketsApi.comment(ticket.id, comment.trim()); setComment(""); onUpdated(await ticketsApi.get(ticket.id)) } catch { setError(t("saveError")) } finally { setBusy(false) }
  }

  async function upload(file: File | undefined) {
    if (!file) return
    setBusy(true); setError(null)
    try { const added = await ticketsApi.upload(ticket.id, file); setAttachments((current) => [...current, added]) } catch { setError(t("uploadError")) } finally { setBusy(false) }
  }

  return (
    <section className="min-h-0 flex-1 overflow-y-auto p-4 lg:p-7">
      <div className="mx-auto max-w-4xl space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div><div className="mb-1 text-xs text-zinc-500">#{ticket.number} · {new Date(ticket.created_at).toLocaleString()}</div><h1 className="text-2xl font-semibold text-zinc-100">{ticket.title}</h1><p className="mt-2 whitespace-pre-wrap text-sm text-zinc-400">{ticket.description || t("noDescription")}</p></div>
          {error && <div className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>}
        </header>
        <div className="grid gap-3 rounded-xl border border-white/10 bg-zinc-950/40 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs text-zinc-500">{t("statusLabel")}<select disabled={busy} value={ticket.status} onChange={(event) => void update({ status: event.target.value as TicketStatus })} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-2 py-2 text-sm text-zinc-200">{statuses.map((status) => <option key={status} value={status}>{t(`status.${status}`)}</option>)}</select></label>
          <label className="text-xs text-zinc-500">{t("priorityLabel")}<select disabled={busy} value={ticket.priority} onChange={(event) => void update({ priority: event.target.value as TicketPriority })} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-2 py-2 text-sm text-zinc-200">{priorities.map((priority) => <option key={priority} value={priority}>{t(`priority.${priority}`)}</option>)}</select></label>
          <label className="text-xs text-zinc-500">{t("team")}<select disabled={busy} value={ticket.team_id ?? ""} onChange={(event) => void update({ team_id: event.target.value || null })} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-2 py-2 text-sm text-zinc-200"><option value="">{t("unassigned")}</option>{teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label>
          <label className="text-xs text-zinc-500">{t("assignedTo")}<input disabled={busy} defaultValue={ticket.assigned_to ?? ""} onBlur={(event) => { const value = event.target.value.trim() || null; if (value !== ticket.assigned_to) void update({ assigned_to: value }) }} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-2 py-2 text-sm text-zinc-200" placeholder={t("unassigned")} /></label>
        </div>
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div className="rounded-xl border border-white/10 bg-zinc-950/30 p-4"><h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-100"><MessageSquare size={16} className="text-sky-400" />{t("conversation")}</h2><div className="space-y-3">{(ticket.comments ?? []).map((item) => <article key={item.id} className="rounded-lg bg-white/[3%] p-3"><div className="mb-1 flex items-center gap-2 text-[11px] text-zinc-500"><UserRound size={13} />{item.author_id} · {new Date(item.created_at).toLocaleString()}</div><p className="whitespace-pre-wrap text-sm text-zinc-300">{item.body}</p></article>)}{(ticket.comments ?? []).length === 0 && <p className="text-sm text-zinc-500">{t("noComments")}</p>}</div><div className="mt-4 flex gap-2"><textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder={t("commentPlaceholder")} rows={3} className="min-w-0 flex-1 rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-sky-400/50" /><button disabled={busy || !comment.trim()} onClick={() => void addComment()} className="self-end rounded-lg bg-sky-500 p-2.5 text-white disabled:opacity-40" title={t("comment")}><Send size={16} /></button></div></div>
          <aside className="rounded-xl border border-white/10 bg-zinc-950/30 p-4"><h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><Paperclip size={16} className="text-sky-400" />{t("attachments")}</h2><label className="mb-3 flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-white/15 px-3 py-3 text-xs text-zinc-400 hover:border-sky-400/50 hover:text-zinc-200"><FileText size={15} />{t("upload")}<input type="file" className="hidden" disabled={busy} onChange={(event) => void upload(event.target.files?.[0])} /></label><div className="space-y-2">{attachments.map((attachment) => <button key={attachment.id} onClick={() => void downloadAttachment(ticket.id, attachment)} className="flex w-full items-center gap-2 rounded-lg bg-white/[3%] p-2 text-left text-xs text-zinc-300 hover:bg-white/[7%]"><Check size={13} className="shrink-0 text-emerald-400" /><span className="min-w-0 flex-1 truncate">{attachment.original_name}</span><span className="text-zinc-600">{Math.ceil(attachment.size_bytes / 1024)} KB</span></button>)}{attachments.length === 0 && <p className="text-xs text-zinc-500">{t("noAttachments")}</p>}</div></aside>
        </div>
        {(ticket.project_id || ticket.task_id || ticket.session_id) && <div className="rounded-xl border border-white/10 bg-zinc-950/30 p-4 text-xs text-zinc-500"><span className="font-semibold text-zinc-300">{t("links")}</span><div className="mt-2 flex flex-wrap gap-3">{ticket.project_id && <span>{t("project")}: {ticket.project_id}</span>}{ticket.task_id && <span>{t("task")}: {ticket.task_id}</span>}{ticket.session_id && <span>{t("session")}: {ticket.session_id}</span>}</div></div>}
      </div>
    </section>
  )
}
