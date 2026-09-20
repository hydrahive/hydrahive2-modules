import { useEffect, useState } from "react"
import { ExternalLink, FolderGit2, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Select } from "@/shared/ui"
import { chatApi, type ProjectBrief } from "@/features/chat/api"
import { ProjectPicker } from "@/features/chat/ProjectPicker"
import { ticketsApi } from "./api"
import type { GithubConnection, GithubIssue, GithubProject, GithubProjectItem } from "./types"

export function GithubProjectItems() {
  const { t } = useTranslation("tickets")
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [projectId, setProjectId] = useState("")
  const [connections, setConnections] = useState<GithubConnection[]>([])
  const [connectionId, setConnectionId] = useState("")
  const [githubProjects, setGithubProjects] = useState<GithubProject[]>([])
  const [githubProjectId, setGithubProjectId] = useState("")
  const [items, setItems] = useState<GithubProjectItem[]>([])
  const [issues, setIssues] = useState<GithubIssue[]>([])
  const [issuesLoading, setIssuesLoading] = useState(false)
  const [issuesError, setIssuesError] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    void chatApi.listProjects().then(setProjects).catch(() => setProjects([]))
  }, [])

  useEffect(() => {
    setConnections([])
    setConnectionId("")
    setGithubProjects([])
    setGithubProjectId("")
    setItems([])
    if (!projectId) return
    setLoading(true)
    void ticketsApi.githubConnections(projectId).then((available) => {
      setConnections(available)
      setConnectionId(available[0]?.id ?? "")
      setError(false)
    }).catch(() => {
      setConnections([])
      setError(true)
    }).finally(() => setLoading(false))
  }, [projectId])

  useEffect(() => {
    setGithubProjects([])
    setGithubProjectId("")
    setItems([])
    setIssues([])
    setIssuesError(false)
    if (!connectionId) return
    setLoading(true)
    void ticketsApi.githubProjects(connectionId).then((available) => {
      setGithubProjects(available)
      setGithubProjectId(available[0] ? String(available[0].number) : "")
      setError(false)
    }).catch(() => {
      setGithubProjects([])
      setError(true)
    }).finally(() => setLoading(false))
  }, [connectionId])

  useEffect(() => {
    setIssues([])
    setIssuesError(false)
    if (!connectionId) return
    setIssuesLoading(true)
    void ticketsApi.githubAssignedIssues(connectionId).then(setIssues).catch(() => {
      setIssues([])
      setIssuesError(true)
    }).finally(() => setIssuesLoading(false))
  }, [connectionId])

  useEffect(() => {
    setItems([])
    if (!connectionId || !githubProjectId) return
    const selected = githubProjects.find((item) => String(item.number) === githubProjectId)
    if (!selected) return
    setLoading(true)
    void ticketsApi.githubProjectItems(githubProjectId, connectionId, selected.number).then(setItems).catch(() => {
      setItems([])
      setError(true)
    }).finally(() => setLoading(false))
  }, [connectionId, githubProjectId, githubProjects])

  function pickProject(nextProjectId: string | null) {
    setProjectId(nextProjectId ?? "")
    setError(false)
  }

  return <section className="border-t border-[#1f2a3b] p-3">
    <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-[#c8d2df]"><FolderGit2 size={14} className="text-[#69d7ff]" />{t("githubItemsTitle")}</div>
    <div className="space-y-2">
      <ProjectPicker current={projectId || null} projects={projects} onPick={pickProject} busy={loading} />
      <Select value={connectionId} onChange={(event) => setConnectionId(event.target.value)} disabled={loading || connections.length === 0} className="h-8 border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubChooseConnection")}</option>{connections.map((connection) => <option key={connection.id} value={connection.id}>{connection.owner}/{connection.repository}</option>)}</Select>
      <Select value={githubProjectId} onChange={(event) => setGithubProjectId(event.target.value)} disabled={loading || githubProjects.length === 0} className="h-8 border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubChooseProject")}</option>{githubProjects.map((project) => <option key={project.id} value={String(project.number)}>{project.title}</option>)}</Select>
      {loading && <div className="flex items-center gap-1 text-[10px] text-[#607188]"><Loader2 size={11} className="animate-spin" />{t("githubItemsLoading")}</div>}
      {issuesLoading && <div className="flex items-center gap-1 text-[10px] text-[#607188]"><Loader2 size={11} className="animate-spin" />{t("githubIssuesLoading")}</div>}
      {error && <p className="text-[10px] text-orange-200">{t("githubItemsError")}</p>}
      {issuesError && <p className="text-[10px] text-orange-200">{t("githubIssuesError")}</p>}
      {connectionId && !issuesLoading && !issuesError && issues.length === 0 && <p className="text-[10px] text-[#607188]">{t("githubIssuesEmpty")}</p>}
      {issues.map((issue) => <div key={issue.id} className="flex items-center gap-2 rounded border border-[#1f2a3b] bg-[#0d1420] px-2 py-1.5 text-[10px] text-[#91a3b8]"><span className="min-w-0 flex-1 truncate">#{issue.number} {issue.title}</span><span className="text-[9px] text-[#607188]">{t("githubIssueOpen")}</span><a href={issue.url} target="_blank" rel="noreferrer" className="text-[#69d7ff] hover:text-[#c8f2ff]" title={t("githubOpenItem")}><ExternalLink size={12} /></a></div>)}
      {!loading && !error && projectId && connections.length === 0 && <p className="text-[10px] text-[#607188]">{t("githubItemsNoConnection")}</p>}
      {!loading && !error && connectionId && githubProjects.length === 0 && <p className="text-[10px] text-[#607188]">{t("githubItemsNoProjects")}</p>}
      {!loading && !error && githubProjectId && items.length === 0 && <p className="text-[10px] text-[#607188]">{t("githubItemsEmpty")}</p>}
      {items.map((item) => item.content && <div key={item.id} className="flex items-center gap-2 rounded border border-[#1f2a3b] bg-[#0d1420] px-2 py-1.5 text-[10px] text-[#91a3b8]"><span className="min-w-0 flex-1 truncate">{item.content.title ?? t("githubItemsUntitled")}</span>{item.content.state && <span className="text-[9px] uppercase text-[#607188]">{item.content.state}</span>}{item.content.url && <a href={item.content.url} target="_blank" rel="noreferrer" className="text-[#69d7ff] hover:text-[#c8f2ff]" title={t("githubOpenItem")}><ExternalLink size={12} /></a>}</div>)}
    </div>
  </section>
}
