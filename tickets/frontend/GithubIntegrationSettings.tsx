import { useEffect, useState } from "react"
import { GitBranch, Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Select } from "@/shared/ui"
import { chatApi, type ProjectBrief } from "@/features/chat/api"
import { ProjectPicker } from "@/features/chat/ProjectPicker"
import { credentialsApi } from "@/features/credentials/api"
import type { Credential } from "@/features/credentials/types"
import { ticketsApi } from "./api"
import type { GithubConnection, GithubDiscoveryOwner, GithubRepository } from "./types"

function matchesGithubApi(pattern: string) {
  if (!pattern || pattern === "*") return true
  const expression = new RegExp(`^${pattern.split("*").map((part) => part.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&")).join(".*")}$`)
  return expression.test("https://api.github.com/graphql")
}

export function GithubIntegrationSettings() {
  const { t } = useTranslation("tickets")
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [projectsLoading, setProjectsLoading] = useState(true)
  const [projectsError, setProjectsError] = useState(false)
  const [projectId, setProjectId] = useState("")
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [credential, setCredential] = useState("")
  const [owners, setOwners] = useState<GithubDiscoveryOwner[]>([])
  const [owner, setOwner] = useState("")
  const [repositories, setRepositories] = useState<GithubRepository[]>([])
  const [repository, setRepository] = useState("")
  const [discoveryBusy, setDiscoveryBusy] = useState(false)
  const [discoveryError, setDiscoveryError] = useState(false)
  const [connections, setConnections] = useState<GithubConnection[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    void Promise.all([chatApi.listProjects(), credentialsApi.list()]).then(([availableProjects, availableCredentials]) => {
      setProjects(availableProjects)
      setCredentials(availableCredentials.filter((item) => item.type === "bearer" && item.value_set && matchesGithubApi(item.url_pattern)))
      setProjectsError(false)
    }).catch(() => {
      setProjects([])
      setCredentials([])
      setProjectsError(true)
    }).finally(() => setProjectsLoading(false))
  }, [])

  useEffect(() => {
    if (!projectId) { setConnections([]); return }
    void ticketsApi.githubConnections(projectId).then(setConnections).catch(() => setConnections([]))
  }, [projectId])

  useEffect(() => {
    setOwners([])
    setOwner("")
    setRepositories([])
    setRepository("")
    setDiscoveryError(false)
    if (!projectId || !credential) return
    setDiscoveryBusy(true)
    void ticketsApi.githubDiscovery({ project_id: projectId, credential_name: credential }).then((result) => {
      setOwners(result.owners)
      setDiscoveryError(false)
    }).catch(() => {
      setOwners([])
      setDiscoveryError(true)
    }).finally(() => setDiscoveryBusy(false))
  }, [projectId, credential])

  useEffect(() => {
    setRepositories([])
    setRepository("")
    if (!projectId || !credential || !owner) return
    setDiscoveryBusy(true)
    void ticketsApi.githubDiscovery({ project_id: projectId, credential_name: credential, owner }).then((result) => {
      setRepositories(result.repositories)
      setDiscoveryError(false)
    }).catch(() => {
      setRepositories([])
      setDiscoveryError(true)
    }).finally(() => setDiscoveryBusy(false))
  }, [projectId, credential, owner])

  function pickProject(nextProjectId: string | null) {
    setProjectId(nextProjectId ?? "")
    setCredential("")
    setConnections([])
    setMessage(null)
  }

  async function create() {
    if (!projectId || !owner || !repository || !credential) return
    setBusy(true); setMessage(null)
    try {
      const connection = await ticketsApi.createGithubConnection({ project_id: projectId, owner, repository, credential_name: credential })
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
      <Select value={credential} onChange={(event) => setCredential(event.target.value)} disabled={!projectId || busy} className="h-8 border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubChooseCredential")}</option>{credentials.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</Select>
      <Select value={owner} onChange={(event) => setOwner(event.target.value)} disabled={!credential || discoveryBusy || busy} className="h-8 border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubChooseOwner")}</option>{owners.map((item) => <option key={item.login} value={item.login}>{item.login} ({item.kind})</option>)}</Select>
      <Select value={repository} onChange={(event) => setRepository(event.target.value)} disabled={!owner || discoveryBusy || busy} className="h-8 border-[#253247] bg-[#111b29] text-[11px]"><option value="">{t("githubChooseRepository")}</option>{repositories.map((item) => <option key={item.nameWithOwner} value={item.name}>{item.name}</option>)}</Select>
      {discoveryBusy && <p className="text-[10px] text-[#607188]">{t("githubDiscoveryLoading")}</p>}
      {discoveryError && <p className="text-[10px] text-orange-200">{t("githubDiscoveryError")}</p>}
      {credentials.length === 0 && !projectsLoading && <p className="text-[10px] text-orange-200">{t("githubNoCredential")}</p>}
      <button type="button" disabled={busy || !projectId || !credential || !owner || !repository} onClick={() => void create()} className="inline-flex w-full items-center justify-center gap-1 rounded border border-[#2b4058] bg-[#111b29] px-2 py-1.5 text-[11px] text-[#a8dff2] hover:border-[#69d7ff]/60 disabled:opacity-40"><Plus size={12} />{t("githubAdd")}</button>
      {message && <p className="text-[10px] text-orange-200">{message}</p>}
      {connections.map((connection) => <div key={connection.id} className="flex items-center gap-2 rounded border border-[#1f2a3b] bg-[#0d1420] px-2 py-1.5 text-[10px] text-[#91a3b8]"><span className="min-w-0 flex-1 truncate">{connection.owner}/{connection.repository}</span><button type="button" disabled={busy} onClick={() => void disable(connection.id)} className="text-[#607188] hover:text-orange-200" title={t("githubDisable")}><Trash2 size={12} /></button></div>)}
    </div>
  </section>
}
