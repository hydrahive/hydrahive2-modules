import { useEffect, useState } from "react"
import type { ReactNode } from "react"
import { CalendarDays, CircleUserRound, Clock3, Download, FileText, Github, Link2, MessageSquare, Paperclip, Send, Tag, Unlink, UsersRound } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Input, Select, Textarea } from "@/shared/ui"
import { downloadAttachment, ticketsApi } from "./api"
import type { GithubLink, Team, Ticket, TicketAttachment, TicketComment, TicketPriority, TicketStatus } from "./types"

interface Props {
  ticket: Ticket
  teams: Team[]
  onUpdated: (ticket: Ticket) => void
}

const statuses: TicketStatus[] = ["open", "triaged", "in_progress", "waiting", "resolved", "closed", "cancelled"]
const priorities: TicketPriority[] = ["low", "normal", "high", "urgent"]

const statusTone: Record<TicketStatus, string> = {
  open: "border-sky-400/35 bg-sky-400/10 text-sky-200",
  triaged: "border-cyan-400/35 bg-cyan-400/10 text-cyan-200",
  in_progress: "border-violet-400/35 bg-violet-400/10 text-violet-200",
  waiting: "border-amber-400/35 bg-amber-400/10 text-amber-200",
  resolved: "border-emerald-400/35 bg-emerald-400/10 text-emerald-200",
  closed: "border-zinc-500/35 bg-zinc-500/10 text-zinc-300",
  cancelled: "border-orange-400/35 bg-orange-400/10 text-orange-200",
}

const priorityTone: Record<TicketPriority, string> = {
  low: "bg-zinc-500",
  normal: "bg-sky-400",
  high: "bg-amber-400",
  urgent: "bg-orange-400",
}

function initials(value: string) {
  const parts = value.split(/[\s._-]+/).filter(Boolean)
  return (parts.length > 1 ? `${parts[0][0]}${parts[1][0]}` : value.slice(0, 2)).toUpperCase()
}

function formatDate(value: string, locale: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(date)
}

function fileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${Math.ceil(bytes / 1024)} KB`
  return `${(bytes / 1_048_576).toFixed(1)} MB`
}

export function TicketDetail({ ticket, teams, onUpdated }: Props) {
  const { t, i18n } = useTranslation("tickets")
  const [comment, setComment] = useState("")
  const [comments, setComments] = useState<TicketComment[]>(ticket.comments ?? [])
  const [attachments, setAttachments] = useState<TicketAttachment[]>(ticket.attachments ?? [])
  const [assignedTo, setAssignedTo] = useState(ticket.assigned_to ?? "")
  const [manualDueAt, setManualDueAt] = useState(ticket.manual_due_at ? ticket.manual_due_at.slice(0, 16) : "")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [githubLink, setGithubLink] = useState<GithubLink | null>(null)
  const [githubConnectionId, setGithubConnectionId] = useState("")
  const [githubOwner, setGithubOwner] = useState("")
  const [githubRepository, setGithubRepository] = useState("")
  const [githubIssueNumber, setGithubIssueNumber] = useState("")

  useEffect(() => {
    setComments(ticket.comments ?? [])
    setAttachments(ticket.attachments ?? [])
    setAssignedTo(ticket.assigned_to ?? "")
    setManualDueAt(ticket.manual_due_at ? ticket.manual_due_at.slice(0, 16) : "")
    void Promise.all([ticketsApi.comments(ticket.id), ticketsApi.attachments(ticket.id)]).then(([nextComments, nextAttachments]) => {
      setComments(nextComments)
      setAttachments(nextAttachments)
    }).catch(() => {})
    void ticketsApi.githubLink(ticket.id).then(setGithubLink).catch(() => setGithubLink(null))
  }, [ticket.id, ticket.comments, ticket.attachments, ticket.assigned_to])

  async function update(patch: Partial<Ticket>) {
    setBusy(true)
    setError(null)
    try {
      onUpdated(await ticketsApi.update(ticket.id, patch))
    } catch {
      setError(t("saveError"))
    } finally {
      setBusy(false)
    }
  }

  async function addComment() {
    if (!comment.trim()) return
    setBusy(true)
    setError(null)
    try {
      const added = await ticketsApi.comment(ticket.id, comment.trim())
      setComments((current) => [...current, added])
      setComment("")
      onUpdated({ ...ticket, comments: [...comments, added], updated_at: new Date().toISOString() })
    } catch {
      setError(t("saveError"))
    } finally {
      setBusy(false)
    }
  }

  async function saveDue(value: string | null) {
    const next = value ? new Date(value).toISOString() : null
    setManualDueAt(value ? value.slice(0, 16) : "")
    await update({ due_at: next })
  }

  async function upload(file: File | undefined) {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const added = await ticketsApi.upload(ticket.id, file)
      setAttachments((current) => [...current, added])
    } catch {
      setError(t("uploadError"))
    } finally {
      setBusy(false)
    }
  }

  async function linkGithub() {
    const issueNumber = Number(githubIssueNumber)
    if (!githubConnectionId || !githubOwner || !githubRepository || !Number.isInteger(issueNumber) || issueNumber < 1) return
    setBusy(true)
    setError(null)
    try {
      const linked = await ticketsApi.linkGithubIssue(ticket.id, { connection_id: githubConnectionId, owner: githubOwner, repository: githubRepository, issue_number: issueNumber, issue_url: `https://github.com/${githubOwner}/${githubRepository}/issues/${issueNumber}` })
      setGithubLink(linked)
    } catch {
      setError(t("githubLinkError"))
    } finally { setBusy(false) }
  }

  async function unlinkGithub() {
    setBusy(true)
    try { await ticketsApi.unlinkGithubIssue(ticket.id); setGithubLink(null) } catch { setError(t("githubLinkError")) } finally { setBusy(false) }
  }

  return (
    <section className="min-h-0 flex-1 overflow-y-auto bg-[#0a1019]">
      <div className="mx-auto max-w-[1240px] px-4 py-5 lg:px-8 lg:py-7">
        <div className="mb-5 flex items-center gap-2 text-[11px] text-[#607188]"><span>{t("title")}</span><span className="text-[#354357]">/</span><span className="font-mono text-[#69d7ff]">#{ticket.number}</span><span className="ml-auto">{t("lastUpdated")} {formatDate(ticket.updated_at, i18n.language)}</span></div>

        <header className="border-b border-[#1f2a3b] pb-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="mb-3 flex flex-wrap items-center gap-2"><span className="font-mono text-xs font-semibold text-[#69d7ff]">#{ticket.number}</span><span className={`rounded-[5px] border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] ${statusTone[ticket.status]}`}>{t(`status.${ticket.status}`)}</span><span className="flex items-center gap-1.5 text-[11px] text-[#8998ac]"><span className={`h-1.5 w-1.5 rounded-full ${priorityTone[ticket.priority]}`} />{t(`priority.${ticket.priority}`)}</span></div>
              <h2 className="max-w-4xl text-2xl font-semibold tracking-[-0.025em] text-[#f1f5fb] lg:text-[28px]">{ticket.title}</h2>
              <p className="mt-3 max-w-3xl whitespace-pre-wrap text-sm leading-6 text-[#98a6b9]">{ticket.description || t("noDescription")}</p>
            </div>
            {error && <div className="max-w-xs rounded-[6px] border border-orange-500/25 bg-orange-500/[7%] px-3 py-2 text-xs text-orange-200">{error}</div>}
          </div>

          <div className="mt-6 flex flex-wrap gap-2">
            <MetadataChip icon={<CircleUserRound size={13} />} label={t("requester")} value={ticket.created_by} />
            <MetadataChip icon={<UsersRound size={13} />} label={t("team")} value={teams.find((team) => team.id === ticket.team_id)?.name ?? t("unassigned")} />
            <MetadataChip icon={<CalendarDays size={13} />} label={t("created")} value={formatDate(ticket.created_at, i18n.language)} />
            {ticket.category && <MetadataChip icon={<Tag size={13} />} label={t("categoryField")} value={ticket.category} />}
          </div>
        </header>

        <div className="grid gap-5 pt-6 xl:grid-cols-[minmax(0,1fr)_290px]">
          <div className="min-w-0 space-y-5">
            <section className="rounded-[8px] border border-[#1f2a3b] bg-[#0d1420]">
              <div className="flex items-center justify-between border-b border-[#1f2a3b] px-4 py-3.5"><div className="flex items-center gap-2 text-sm font-semibold text-[#e8eef8]"><MessageSquare size={16} className="text-[#69d7ff]" />{t("conversation")}</div><span className="text-[11px] text-[#607188]">{comments.length} {t("commentsCount")}</span></div>
              <div className="space-y-4 p-4">
                {comments.length === 0 ? <p className="py-5 text-center text-xs text-[#607188]">{t("noComments")}</p> : comments.map((item) => <article key={item.id} className="flex gap-3"><div className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-[#2b4058] bg-[#17283c] text-[10px] font-semibold text-[#a9dff1]">{initials(item.author_id)}</div><div className="min-w-0 flex-1"><div className="mb-1.5 flex flex-wrap items-center gap-x-2 gap-y-1"><span className="text-xs font-semibold text-[#c8d2df]">{item.author_id}</span><span className="text-[10px] text-[#607188]">{formatDate(item.created_at, i18n.language)}</span>{item.author_kind === "agent" && <span className="rounded-[4px] border border-violet-400/25 bg-violet-400/10 px-1.5 py-0.5 text-[9px] uppercase tracking-[0.08em] text-violet-200">{t("agent")}</span>}</div><div className="rounded-[7px] border border-[#1f2a3b] bg-[#111b29] px-3 py-2.5 text-sm leading-6 text-[#b4c0cf]"><p className="whitespace-pre-wrap">{item.body}</p></div></div></article>)}
                <div className="border-t border-[#1f2a3b] pt-4"><div className="flex items-end gap-2"><Textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder={t("commentPlaceholder")} rows={3} className="min-h-[82px] border-[#253247] bg-[#0b131f] text-sm" /><button disabled={busy || !comment.trim()} onClick={() => void addComment()} className="grid h-10 w-10 shrink-0 place-items-center rounded-[6px] border border-[#3b83a8] bg-[#163248] text-[#c8f2ff] transition-colors hover:border-[#69d7ff] hover:bg-[#1b3d56] disabled:cursor-not-allowed disabled:opacity-40" title={t("comment")}><Send size={15} /></button></div></div>
              </div>
            </section>

            <section className="rounded-[8px] border border-[#1f2a3b] bg-[#0d1420] p-4">
              <div className="mb-3 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-semibold text-[#e8eef8]"><Github size={15} className="text-[#69d7ff]" />{t("githubIntegration")}</div>{githubLink && <span className={`rounded px-1.5 py-0.5 text-[9px] uppercase ${githubLink.sync_state === "linked" ? "bg-emerald-400/10 text-emerald-200" : "bg-orange-400/10 text-orange-200"}`}>{githubLink.sync_state}</span>}</div>
              {githubLink ? <div className="flex items-center gap-2"><a href={githubLink.issue_url} target="_blank" rel="noreferrer" className="min-w-0 flex-1 truncate text-xs text-[#69d7ff] hover:underline">{githubLink.owner}/{githubLink.repository}#{githubLink.issue_number}</a><button type="button" disabled={busy} onClick={() => void unlinkGithub()} className="rounded border border-[#2b4058] p-1.5 text-[#91a3b8] hover:border-orange-400/50 hover:text-orange-200" title={t("githubUnlink")}><Unlink size={13} /></button></div> : <div className="grid gap-2"><div className="grid grid-cols-2 gap-2"><Input value={githubConnectionId} onChange={(event) => setGithubConnectionId(event.target.value)} placeholder={t("githubConnectionId")} className="border-[#253247] bg-[#111b29] text-xs" /><Input value={githubOwner} onChange={(event) => setGithubOwner(event.target.value)} placeholder={t("githubOwner")} className="border-[#253247] bg-[#111b29] text-xs" /></div><div className="grid grid-cols-[1fr_90px] gap-2"><Input value={githubRepository} onChange={(event) => setGithubRepository(event.target.value)} placeholder={t("githubRepository")} className="border-[#253247] bg-[#111b29] text-xs" /><Input type="number" min={1} value={githubIssueNumber} onChange={(event) => setGithubIssueNumber(event.target.value)} placeholder="#" className="border-[#253247] bg-[#111b29] text-xs" /></div><button type="button" disabled={busy} onClick={() => void linkGithub()} className="rounded border border-[#3b83a8] bg-[#163248] px-3 py-2 text-xs text-[#c8f2ff] hover:border-[#69d7ff]">{t("githubLink")}</button></div>}
            </section>

            {(ticket.project_id || ticket.task_id || ticket.session_id) && <section className="rounded-[8px] border border-[#1f2a3b] bg-[#0d1420] p-4"><div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#e8eef8]"><Link2 size={15} className="text-[#69d7ff]" />{t("links")}</div><div className="flex flex-wrap gap-2">{ticket.project_id && <LinkChip label={t("project")} value={ticket.project_id} />} {ticket.task_id && <LinkChip label={t("task")} value={ticket.task_id} />} {ticket.session_id && <LinkChip label={t("session")} value={ticket.session_id} />}</div></section>}
          </div>

          <aside className="space-y-5">
            <section className="rounded-[8px] border border-[#1f2a3b] bg-[#0d1420] p-4"><div className="mb-4 flex items-center gap-2 text-sm font-semibold text-[#e8eef8]"><Clock3 size={15} className="text-[#69d7ff]" />{t("ticketControls")}</div><div className="space-y-3"><label className="block text-[10px] font-semibold uppercase tracking-[0.1em] text-[#718096]">{t("statusLabel")}<Select disabled={busy} value={ticket.status} onChange={(event) => void update({ status: event.target.value as TicketStatus })} className="mt-1.5 border-[#253247] bg-[#111b29] text-xs">{statuses.map((status) => <option key={status} value={status}>{t(`status.${status}`)}</option>)}</Select></label><label className="block text-[10px] font-semibold uppercase tracking-[0.1em] text-[#718096]">{t("priorityLabel")}<Select disabled={busy} value={ticket.priority} onChange={(event) => void update({ priority: event.target.value as TicketPriority })} className="mt-1.5 border-[#253247] bg-[#111b29] text-xs">{priorities.map((priority) => <option key={priority} value={priority}>{t(`priority.${priority}`)}</option>)}</Select></label><label className="block text-[10px] font-semibold uppercase tracking-[0.1em] text-[#718096]">{t("team")}<Select disabled={busy} value={ticket.team_id ?? ""} onChange={(event) => void update({ team_id: event.target.value || null })} className="mt-1.5 border-[#253247] bg-[#111b29] text-xs"><option value="">{t("unassigned")}</option>{teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}</Select></label><label className="block text-[10px] font-semibold uppercase tracking-[0.1em] text-[#718096]">{t("assignedTo")}<Input disabled={busy} value={assignedTo} onChange={(event) => setAssignedTo(event.target.value)} onBlur={() => { const value = assignedTo.trim() || null; if (value !== ticket.assigned_to) void update({ assigned_to: value }) }} className="mt-1.5 border-[#253247] bg-[#111b29] text-xs" placeholder={t("unassigned")} /></label><label className="block text-[10px] font-semibold uppercase tracking-[0.1em] text-[#718096]">{t("dueDate")}<input type="datetime-local" disabled={busy} value={manualDueAt} onChange={(event) => setManualDueAt(event.target.value)} onBlur={() => { if (manualDueAt !== (ticket.manual_due_at ? ticket.manual_due_at.slice(0, 16) : "")) void saveDue(manualDueAt || null) }} className="mt-1.5 block w-full rounded-[5px] border border-[#253247] bg-[#111b29] px-2.5 py-2 text-xs text-[#c8d2df]" />{ticket.due_at && <span className={`mt-1 block text-[10px] ${ticket.due_at_source === "manual" ? "text-cyan-300" : "text-[#718096]"}`}>{ticket.due_at_source === "manual" ? t("manualDueDate") : t("slaDueDate")} · {formatDate(ticket.due_at, i18n.language)}</span>}{ticket.due_at_source === "manual" && <button type="button" disabled={busy} onClick={() => void saveDue(null)} className="mt-1 text-[10px] text-[#69d7ff] hover:text-[#c8f2ff]">{t("resetDueDate")}</button>}</label></div></section>

            <section className="rounded-[8px] border border-[#1f2a3b] bg-[#0d1420] p-4"><div className="mb-3 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-semibold text-[#e8eef8]"><Paperclip size={15} className="text-[#69d7ff]" />{t("attachments")}</div><span className="text-[11px] text-[#607188]">{attachments.length}</span></div><label className="mb-3 flex cursor-pointer items-center justify-center gap-2 rounded-[6px] border border-dashed border-[#2c4058] bg-[#111b29] px-3 py-2.5 text-[11px] font-medium text-[#8fa1b8] transition-colors hover:border-[#69d7ff]/60 hover:text-[#c8f2ff]"><FileText size={14} />{t("upload")}<input type="file" className="hidden" disabled={busy} onChange={(event) => void upload(event.target.files?.[0])} /></label><div className="space-y-2">{attachments.map((attachment) => <button key={attachment.id} onClick={() => void downloadAttachment(ticket.id, attachment)} className="flex w-full items-center gap-2 rounded-[6px] border border-[#1f2a3b] bg-[#111b29] px-2.5 py-2 text-left transition-colors hover:border-[#31506c] hover:bg-[#132235]"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-[5px] bg-[#1b2b3e] text-[#82cce7]"><FileText size={13} /></span><span className="min-w-0 flex-1"><span className="block truncate text-[11px] font-medium text-[#c8d2df]">{attachment.original_name}</span><span className="block text-[10px] text-[#607188]">{fileSize(attachment.size_bytes)}</span></span><Download size={13} className="shrink-0 text-[#607188]" /></button>)}{attachments.length === 0 && <p className="py-2 text-center text-[11px] text-[#607188]">{t("noAttachments")}</p>}</div></section>
          </aside>
        </div>
      </div>
    </section>
  )
}

function MetadataChip({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="flex items-center gap-2 rounded-[6px] border border-[#1f2a3b] bg-[#0d1420] px-2.5 py-2"><span className="text-[#6b849c]">{icon}</span><span><span className="mr-1.5 text-[10px] text-[#607188]">{label}</span><span className="text-[11px] font-medium text-[#b7c4d3]">{value}</span></span></div>
}

function LinkChip({ label, value }: { label: string; value: string }) {
  return <span className="inline-flex items-center gap-1.5 rounded-[5px] border border-[#293c52] bg-[#111b29] px-2.5 py-1.5 text-[11px] text-[#91a3b8]"><span className="text-[#607188]">{label}</span><span className="font-mono text-[#b9c9d9]">{value}</span></span>
}
