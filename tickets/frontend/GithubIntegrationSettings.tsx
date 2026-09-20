import { useEffect, useState } from "react"
import { GitBranch, Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Input } from "@/shared/ui"
import { ticketsApi } from "./api"
import type { GithubConnection } from "./types"

export function GithubIntegrationSettings() {
  const { t } = useTranslation("tickets")
  const [projectId, setProjectId] = useState("")
  const [owner, setOwner] = useState("")
  const [repository, setRepository] = useState("")
  const [credential, setCredential] = useState("")
  const [connections, setConnections] = useState<GithubConnection[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!projectId.trim()) { setConnections([]); return }
    void ticketsApi.githubConnections(projectId.trim()).then(setConnections).catch(() => setConnections([]))
  }, [projectId])

  async function create() {
    if (!projectId.trim() || !owner.trim() || !repository.trim() || !credential.trim()) return
    setBusy(true); setMessage(null)
    try {
      const connection = await ticketsApi.createGithubConnection({ project_id: projectId.trim(), owner: owner.trim(), repository: repository.trim(), credential_name: credential.trim() })
      setConnections((current) => [...current, connection]); setOwner(""); setRepository(""); setMessage(t("githubSaved"))
    } catch { setMessage(t("githubSettingsError")) } finally { setBusy(false) }
  }

  async function disable(id: string) {
    setBusy(true)
    try { await ticketsApi.disableGithubConnection(id); setConnections((current) => current.filter((item) => item.id !== id)) } catch { setMessage(t("githubSettingsError")) } finally { setBusy(false) }
  }

  return <section className="border-t border-[#1f2a3b] p-3">
    <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-[#c8d2df]"><GitBranch size={14} className="text-[#69d7ff]" />{t("githubSettings")}</div>
    <div className="space-y-2">
      <Input value={projectId} onChange={(event) => setProjectId(event.target.value)} placeholder={t("githubProjectId")} className="h-8 border-[#253247] bg-[#111b29] text-[11px]" />
      <div className="grid grid-cols-2 gap-2"><Input value={owner} onChange={(event) => setOwner(event.target.value)} placeholder={t("githubOwner")} className="h-8 border-[#253247] bg-[#111b29] text-[11px]" /><Input value={repository} onChange={(event) => setRepository(event.target.value)} placeholder={t("githubRepository")} className="h-8 border-[#253247] bg-[#111b29] text-[11px]" /></div>
      <Input value={credential} onChange={(event) => setCredential(event.target.value)} placeholder={t("githubCredential")} className="h-8 border-[#253247] bg-[#111b29] text-[11px]" />
      <button type="button" disabled={busy} onClick={() => void create()} className="inline-flex w-full items-center justify-center gap-1 rounded border border-[#2b4058] bg-[#111b29] px-2 py-1.5 text-[11px] text-[#a8dff2] hover:border-[#69d7ff]/60 disabled:opacity-40"><Plus size={12} />{t("githubAdd")}</button>
      {message && <p className="text-[10px] text-orange-200">{message}</p>}
      {connections.map((connection) => <div key={connection.id} className="flex items-center gap-2 rounded border border-[#1f2a3b] bg-[#0d1420] px-2 py-1.5 text-[10px] text-[#91a3b8]"><span className="min-w-0 flex-1 truncate">{connection.owner}/{connection.repository}</span><button type="button" disabled={busy} onClick={() => void disable(connection.id)} className="text-[#607188] hover:text-orange-200" title={t("githubDisable")}><Trash2 size={12} /></button></div>)}
    </div>
  </section>
}
