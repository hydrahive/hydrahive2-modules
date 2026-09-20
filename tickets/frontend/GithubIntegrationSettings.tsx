import { useEffect, useState } from "react"
import { GitBranch, Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Select } from "@/shared/ui"
import { chatApi, type ProjectBrief } from "@/features/chat/api"
import { ProjectPicker } from "@/features/chat/ProjectPicker"
import { projectsApi } from "@/features/projects/api"
import type { ProjectGitRepo } from "@/features/projects/types"
import { ticketsApi } from "./api"
import type { GithubConnection } from "./types"

interface GithubRepoChoice {
  key: string
  owner: string
  repository: string
  label: string
}

function parseGithubRemote(repo: ProjectGitRepo): GithubRepoChoice | null {
  if (!repo.has_token) return null
  const remote = repo.status.remote_url ?? ""
  const match = remote.match(/github\.com[/:]([^/]+)\/([^/#]+?)(?:\.git)?$/i)
  if (!match) return null
  return { key: `${match[1]}/${match[2]}`, owner: match[1], repository: match[2], label: `${match[1]}/${match[2]}` }
}

export function GithubIntegrationSettings() {
  const { t } = useTranslation("tickets")
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [projectsLoading, setProjectsLoading] = useState(true)
  const [projectsError, setProjectsError] = useState(false)
  const [projectId, setProjectId] = useState("")
  const [repoChoices, setRepoChoices] = useState<GithubRepoChoice[]>([])
  const [repoLoading, setRepoLoading] = useState(false)
  const [repoError, setRepoError] = useState(false)
  const [selectedRepo, setSelectedRepo] = useState("")
  const [connections, setConnections] = useState<GithubConnection[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    void chatApi.listProjects().then((available) => {
      setProjects(available)
      setProjectsError(false)
    }).catch(() => {
      setProjects([])
      setProjectsError(true)
    }).finally(() => setProjectsLoading(false))
  }, [])

  useEffect(() => {
    setConnections([])
    setRepoChoices([])
    setSelectedRepo("")
    setRepoError(false)
    if (!projectId) return
    setRepoLoading(true)
    void Promise.all([projectsApi.getRepos(projectId), ticketsApi.githubConnections(projectId)]).then(([repos, configured]) => {
      setRepoChoices(repos.map(parseGithubRemote).filter((repo): repo is GithubRepoChoice => repo !== null))
      setConnections(configured)
    }).catch(() => {
      setRepoChoices([])
      setConnections([])
      setRepoError(true)
    }).finally(() => setRepoLoading(false))
  }, [projectId])

  function pickProject(nextProjectId: string | null) {
    setProjectId(nextProjectId ?? "")
    setMessage(null)
  }

  async function create() {
    const selected = repoChoices.find((repo) => repo.key === selectedRepo)
    if (!projectId || !selected) return
    setBusy(true); setMessage(null)
    try {
      const connection = await ticketsApi.createGithubConnection({ project_id: projectId, owner: selected.owner, repository: selected.repository })
      setConnections((current) => [...current, connection])
      setMessage(t("githubSaved"))
    } catch { setMessage(t("githubSettingsError")) } finally { setBusy(false) }
  }

  async function disable(id: string) {
    setBusy(true)
    try { await ticketsApi.disableGithubConnection(id); setConnections((current) => current.filter((item) => item.id !== id)) } catch { setMessage(t("githubSettingsError")) } finally { setBusy(false) }
  }

  return <section className="border-t border-[#1f2a3b] p-3">
    <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-[#c8d2df]"><GitBranch size={14} className="text-[#69d7ff]" />{t("githubSettings")}</div>
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <ProjectPicker current={projectId || null} projects={projects} onPick={pickProject} busy={projectsLoading || busy} />
        {projectsLoading && <span className="text-[10px] text-[#607188]">{t("githubProjectsLoading")}</span>}
      </div>
      {projectsError && <p className="text-[10px] text-orange-200">{t("githubProjectsError")}</p>}
      {!projectsLoading && !projectsError && projects.length === 0 && <p className="text-[10px] text-[#607188]">{t("githubProjectsEmpty")}</p>}
      <Select value={selectedRepo} onChange={(event) => setSelectedRepo(event.target.value)} disabled={!projectId || repoLoading || busy} className="h-8 border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubChooseRepository")}</option>{repoChoices.map((repo) => <option key={repo.key} value={repo.key}>{repo.label}</option>)}</Select>
      {repoLoading && <p className="text-[10px] text-[#607188]">{t("githubReposLoading")}</p>}
      {repoError && <p className="text-[10px] text-orange-200">{t("githubReposError")}</p>}
      {!repoLoading && !repoError && projectId && repoChoices.length === 0 && <p className="text-[10px] text-[#607188]">{t("githubReposEmpty")}</p>}
      <button type="button" disabled={busy || !projectId || !selectedRepo} onClick={() => void create()} className="inline-flex w-full items-center justify-center gap-1 rounded border border-[#2b4058] bg-[#111b29] px-2 py-1.5 text-[11px] text-[#a8dff2] hover:border-[#69d7ff]/60 disabled:opacity-40"><Plus size={12} />{t("githubAdd")}</button>
      {message && <p className="text-[10px] text-orange-200">{message}</p>}
      {connections.map((connection) => <div key={connection.id} className="flex items-center gap-2 rounded border border-[#1f2a3b] bg-[#0d1420] px-2 py-1.5 text-[10px] text-[#91a3b8]"><span className="min-w-0 flex-1 truncate">{connection.owner}/{connection.repository}</span><button type="button" disabled={busy} onClick={() => void disable(connection.id)} className="text-[#607188] hover:text-orange-200" title={t("githubDisable")}><Trash2 size={12} /></button></div>)}
    </div>
  </section>
}
