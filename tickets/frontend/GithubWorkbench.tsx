import { useEffect, useState } from "react"
import { ExternalLink, GitBranch, Loader2, RefreshCw, Ticket as TicketIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Select } from "@/shared/ui"
import { chatApi, type ProjectBrief } from "@/features/chat/api"
import { ProjectPicker } from "@/features/chat/ProjectPicker"
import { ticketsApi } from "./api"
import type { GithubConnection, GithubIssue, GithubLinkedTicket, GithubProject, GithubProjectItem } from "./types"

interface GithubWorkbenchProps {
  onSelectTicket: (ticketId: string) => void
}

export function GithubWorkbench({ onSelectTicket }: GithubWorkbenchProps) {
  const { t } = useTranslation("tickets")
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [projectId, setProjectId] = useState("")
  const [connections, setConnections] = useState<GithubConnection[]>([])
  const [connectionId, setConnectionId] = useState("")
  const [issues, setIssues] = useState<GithubIssue[]>([])
  const [linkedTickets, setLinkedTickets] = useState<GithubLinkedTicket[]>([])
  const [githubProjects, setGithubProjects] = useState<GithubProject[]>([])
  const [projectNumber, setProjectNumber] = useState("")
  const [projectItems, setProjectItems] = useState<GithubProjectItem[]>([])
  const [tab, setTab] = useState<"issues" | "board">("issues")
  const [issueState, setIssueState] = useState<"open" | "closed" | "all">("open")
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    void chatApi.listProjects().then(setProjects).catch(() => setProjects([]))
  }, [])

  useEffect(() => {
    setConnections([])
    setConnectionId("")
    setIssues([])
    setLinkedTickets([])
    setGithubProjects([])
    setProjectNumber("")
    setProjectItems([])
    setError(false)
    if (!projectId) return
    setLoading(true)
    void ticketsApi.githubConnections(projectId).then((available) => {
      setConnections(available)
      setConnectionId(available[0]?.id ?? "")
    }).catch(() => {
      setConnections([])
      setError(true)
    }).finally(() => setLoading(false))
  }, [projectId])

  async function reloadConnection(id = connectionId) {
    if (!id) return
    setLoading(true)
    try {
      const [remote, local, availableProjects] = await Promise.all([ticketsApi.githubIssues(id, issueState), ticketsApi.githubLinkedTickets(id), ticketsApi.githubProjects(id)])
      setIssues(remote)
      setLinkedTickets(local)
      setGithubProjects(availableProjects)
      setProjectNumber((current) => current || (availableProjects[0] ? String(availableProjects[0].number) : ""))
      setError(false)
    } catch { setError(true) } finally { setLoading(false) }
  }

  useEffect(() => {
    const project = githubProjects.find((item) => String(item.number) === projectNumber)
    if (!connectionId || !project) { setProjectItems([]); return }
    void ticketsApi.githubProjectItems(String(project.number), connectionId, project.number).then(setProjectItems).catch(() => setError(true))
  }, [connectionId, projectNumber, githubProjects])

  async function sync(issueNumber?: number) {
    if (!connectionId) return
    setSyncing(true); setNotice(null)
    try {
      const result = await ticketsApi.githubSync(connectionId, issueState)
      await reloadConnection()
      const imported = issueNumber === undefined ? null : result.tickets.find((item) => item.link.issue_number === issueNumber)
      setNotice(t("githubSyncDone", { count: result.count, created: result.created }))
      if (imported) onSelectTicket(imported.ticket.id)
    } catch { setError(true) } finally { setSyncing(false) }
  }

  async function moveItem(item: GithubProjectItem, field: { id?: string; options?: { id: string; name: string }[] }, optionId: string) {
    const project = githubProjects.find((candidate) => String(candidate.number) === projectNumber)
    if (!connectionId || !project || !field.id || !optionId) return
    setSyncing(true)
    try {
      await ticketsApi.githubProjectFieldUpdate(connectionId, { project_id: project.id, item_id: item.id, field_id: field.id, option_id: optionId })
      const refreshed = await ticketsApi.githubProjectItems(String(project.number), connectionId, project.number)
      setProjectItems(refreshed)
    } catch { setError(true) } finally { setSyncing(false) }
  }

  async function addToProject(issue: GithubIssue) {
    const project = githubProjects.find((candidate) => String(candidate.number) === projectNumber)
    if (!connectionId || !project || !issue.id) return
    setSyncing(true)
    try {
      await ticketsApi.githubProjectItemAdd(connectionId, { project_id: project.id, content_id: issue.id })
      const refreshed = await ticketsApi.githubProjectItems(String(project.number), connectionId, project.number)
      setProjectItems(refreshed)
    } catch { setError(true) } finally { setSyncing(false) }
  }

  const linkedByIssue = new Map(linkedTickets.map((ticket) => [ticket.issue_number, ticket]))
  const selectedConnection = connections.find((item) => item.id === connectionId)
  const canWrite = selectedConnection?.sync_mode === "push" || selectedConnection?.sync_mode === "bidirectional"

  return <main className="flex min-h-0 flex-1 flex-col overflow-hidden bg-[#0a1019]">
    <div className="flex flex-wrap items-center gap-3 border-b border-[#1f2a3b] bg-[#0d1420] px-5 py-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-[#e8eef8]"><GitBranch size={16} className="text-[#69d7ff]" />{t("githubWorkbench")}</div>
      <ProjectPicker current={projectId || null} projects={projects} onPick={(value) => setProjectId(value ?? "")} busy={loading || syncing} />
      <Select value={connectionId} onChange={(event) => setConnectionId(event.target.value)} disabled={loading || connections.length === 0} className="h-8 min-w-[210px] border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubChooseConnection")}</option>{connections.map((connection) => <option key={connection.id} value={connection.id}>{connection.owner}/{connection.repository}</option>)}</Select>
      <Select value={issueState} onChange={(event) => setIssueState(event.target.value as "open" | "closed" | "all")} disabled={loading || !connectionId} className="h-8 border-[#253247] bg-[#111b29] text-[11px]"><option value="open">{t("githubStateOpen")}</option><option value="closed">{t("githubStateClosed")}</option><option value="all">{t("githubStateAll")}</option></Select>
      <Select value={projectNumber} onChange={(event) => setProjectNumber(event.target.value)} disabled={loading || githubProjects.length === 0} className="h-8 min-w-[170px] border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubChooseProject")}</option>{githubProjects.map((project) => <option key={project.id} value={String(project.number)}>{project.title}</option>)}</Select>
      <button type="button" onClick={() => setTab("issues")} className={`rounded px-2 py-1.5 text-[11px] ${tab === "issues" ? "bg-[#163248] text-[#c8f2ff]" : "text-[#91a3b8]"}`}>{t("githubIssuesTab")}</button><button type="button" onClick={() => setTab("board")} className={`rounded px-2 py-1.5 text-[11px] ${tab === "board" ? "bg-[#163248] text-[#c8f2ff]" : "text-[#91a3b8]"}`}>{t("githubBoardTab")}</button>
      <button type="button" disabled={!connectionId || loading || syncing} onClick={() => void sync()} className="inline-flex items-center gap-1 rounded border border-[#2b4058] bg-[#111b29] px-2.5 py-1.5 text-[11px] text-[#a8dff2] hover:border-[#69d7ff]/60 disabled:opacity-40"><RefreshCw size={12} className={syncing ? "animate-spin" : ""} />{t("githubSync")}</button>
    </div>
    {notice && <div className="border-b border-emerald-500/20 bg-emerald-500/[7%] px-5 py-2 text-xs text-emerald-200">{notice}</div>}
    {error && <div className="border-b border-orange-500/25 bg-orange-500/[7%] px-5 py-2 text-xs text-orange-200">{t("githubWorkbenchError")}</div>}
    <div className="min-h-0 flex-1 overflow-y-auto p-5">
      {!projectId && <div className="flex h-full items-center justify-center text-sm text-[#718096]">{t("githubWorkbenchChooseProject")}</div>}
      {projectId && connections.length === 0 && !loading && <div className="flex h-full items-center justify-center text-sm text-[#718096]">{t("githubWorkbenchNoConnection")}</div>}
      {connectionId && <div className="mx-auto max-w-5xl space-y-5">
        {tab === "issues" ? <>
        <section className="rounded-lg border border-[#253247] bg-[#0d1420]">
          <div className="flex items-center justify-between border-b border-[#1f2a3b] px-4 py-3"><div><h2 className="text-sm font-semibold text-[#e8eef8]">{t("githubRemoteIssues")}</h2><p className="mt-0.5 text-[11px] text-[#718096]">{t("githubRemoteIssuesHint")}</p></div><span className="rounded-full border border-[#29405a] px-2 py-0.5 text-[10px] text-[#91a3b8]">{issues.length}</span></div>
          {loading && <div className="flex items-center gap-2 px-4 py-5 text-xs text-[#718096]"><Loader2 size={14} className="animate-spin" />{t("githubLoading")}</div>}
          {!loading && issues.length === 0 && <p className="px-4 py-5 text-xs text-[#718096]">{t("githubNoRemoteIssues")}</p>}
          {!loading && issues.map((issue) => { const linked = linkedByIssue.get(issue.number); return <div key={issue.id} className="flex items-center gap-3 border-t border-[#1f2a3b] px-4 py-3"><TicketIcon size={14} className="shrink-0 text-[#69d7ff]" /><div className="min-w-0 flex-1"><div className="truncate text-sm text-[#d8e2ef]">#{issue.number} {issue.title}</div><div className="mt-1 text-[10px] text-[#718096]">{linked ? t("githubImportedTicket", { number: linked.number }) : t("githubNotImported")}</div></div><button type="button" disabled={syncing} onClick={() => linked ? onSelectTicket(linked.id) : void sync(issue.number)} className="rounded border border-[#2b4058] px-2 py-1 text-[10px] text-[#a8dff2] hover:border-[#69d7ff]/60 disabled:opacity-40">{linked ? t("githubOpenTicket") : t("githubImportTicket")}</button>{projectNumber && <button type="button" disabled={syncing || !canWrite} onClick={() => void addToProject(issue)} className="rounded border border-[#2b4058] px-2 py-1 text-[10px] text-[#a8dff2] hover:border-[#69d7ff]/60 disabled:opacity-40">{t("githubAddToProject")}</button>}<a href={issue.url} target="_blank" rel="noreferrer" className="text-[#69d7ff] hover:text-[#c8f2ff]" title={t("githubOpenExternal")}><ExternalLink size={14} /></a></div> })}
        </section>
        <section className="rounded-lg border border-[#253247] bg-[#0d1420]"><div className="border-b border-[#1f2a3b] px-4 py-3"><h2 className="text-sm font-semibold text-[#e8eef8]">{t("githubLocalTickets")}</h2><p className="mt-0.5 text-[11px] text-[#718096]">{t("githubLocalTicketsHint")}</p></div>{linkedTickets.length === 0 && <p className="px-4 py-5 text-xs text-[#718096]">{t("githubNoImportedTickets")}</p>}{linkedTickets.map((ticket) => <button type="button" key={ticket.id} onClick={() => onSelectTicket(ticket.id)} className="flex w-full items-center gap-3 border-t border-[#1f2a3b] px-4 py-3 text-left hover:bg-[#111b29]"><TicketIcon size={14} className="shrink-0 text-[#8ee6ad]" /><span className="min-w-0 flex-1 truncate text-sm text-[#d8e2ef]">#{ticket.number} {ticket.title}</span><span className="text-[10px] text-[#718096]">{ticket.status}</span></button>)}</section>
        </> : <section className="rounded-lg border border-[#253247] bg-[#0d1420]"><div className="flex items-center justify-between border-b border-[#1f2a3b] px-4 py-3"><div><h2 className="text-sm font-semibold text-[#e8eef8]">{t("githubBoardTitle")}</h2><p className="mt-0.5 text-[11px] text-[#718096]">{t("githubBoardHint")}</p></div><span className="text-[10px] text-[#718096]">{canWrite ? t("githubBoardWriteEnabled") : t("githubBoardReadOnly")}</span></div>{projectItems.length === 0 && <p className="px-4 py-5 text-xs text-[#718096]">{t("githubBoardEmpty")}</p>}{projectItems.map((item) => { const status = (item.fieldValues?.nodes ?? []).find((field) => field.field?.name === "Status" && field.field.options?.length); const field = status?.field; return <div key={item.id} className="flex items-center gap-3 border-t border-[#1f2a3b] px-4 py-3"><TicketIcon size={14} className="shrink-0 text-violet-300" /><span className="min-w-0 flex-1 truncate text-sm text-[#d8e2ef]">{item.content?.title ?? t("githubItemsUntitled")}</span>{field?.id && <Select value={status?.optionId ?? ""} disabled={!canWrite || syncing} onChange={(event) => void moveItem(item, field, event.target.value)} className="h-8 w-[170px] border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubBoardNoStatus")}</option>{(field.options ?? []).map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</Select>}{item.content?.url && <a href={item.content.url} target="_blank" rel="noreferrer" className="text-[#69d7ff]" title={t("githubOpenExternal")}><ExternalLink size={13} /></a>}</div> })}</section>}
      </div>}
    </div>
  </main>
}
