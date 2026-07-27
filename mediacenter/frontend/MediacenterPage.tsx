import { History, ListTodo, Search, Settings } from "lucide-react"
import { useCallback, useEffect, useRef, useState, type ComponentType } from "react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { errorMessage, mediacenterApi } from "./api"
import { SettingsPanel } from "./SettingsPanel"
import { JobsPanel } from "./JobsPanel"
import { ResultGrid } from "./ResultGrid"
import { SearchPanel } from "./SearchPanel"
import type { ConnectionTest, ModuleStatus, SearchFilters, SearchResponse, View } from "./types"

const VIEWS: { id: View; icon: ComponentType<{ size?: number }> }[] = [
  { id: "search", icon: Search },
  { id: "queue", icon: ListTodo },
  { id: "history", icon: History },
  { id: "settings", icon: Settings },
]

export function MediacenterPage() {
  const { t } = useTranslation("mediacenter")
  const [view, setView] = useState<View>("search")
  const [status, setStatus] = useState<ModuleStatus | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [connection, setConnection] = useState<ConnectionTest | null>(null)
  const [testing, setTesting] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [searching, setSearching] = useState(false)
  const [searched, setSearched] = useState(false)
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [queueRefresh, setQueueRefresh] = useState(0)
  const statusRequest = useRef(0)

  const loadStatus = useCallback(async () => {
    const request = ++statusRequest.current
    setStatusLoading(true)
    setStatusError(null)
    try {
      const nextStatus = await mediacenterApi.status()
      if (request === statusRequest.current) setStatus(nextStatus)
    } catch (cause) {
      if (request === statusRequest.current) {
        setStatus(null)
        setStatusError(errorMessage(cause))
      }
    } finally {
      if (request === statusRequest.current) setStatusLoading(false)
    }
  }, [])
  useEffect(() => {
    void loadStatus()
    return () => { statusRequest.current += 1 }
  }, [loadStatus])

  const testConnections = async () => {
    setTesting(true)
    setConnectionError(null)
    try {
      setConnection(await mediacenterApi.testConnections())
    } catch (cause) {
      setConnection(null)
      setConnectionError(errorMessage(cause))
    } finally {
      setTesting(false)
    }
  }

  const search = async (filters: SearchFilters) => {
    setSearching(true)
    setSearched(true)
    setSearchResponse(null)
    setSearchError(null)
    try {
      setSearchResponse(await mediacenterApi.search(filters))
    } catch (cause) {
      setSearchResponse(null)
      setSearchError(errorMessage(cause))
    } finally {
      setSearching(false)
    }
  }

  return <CockpitShell title="Mediacenter" className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
    <CockpitTopbar active="/mediacenter" context={t("subtitle")} />
    <main className="min-h-0 flex-1 overflow-y-auto p-[10px]">
      <div className="mx-auto max-w-7xl space-y-4">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div><h1 className="text-xl font-black tracking-tight text-[#e8eef8]">{t("title")}</h1><p className="mt-1 text-sm text-[#8d9ab0]">{t("subtitle")}</p></div>
          <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-cyan-200">V2</span>
        </header>
        {statusError && <div className="flex items-center justify-between gap-3 rounded-[4px] border border-rose-500/25 bg-rose-500/[8%] p-3 text-xs text-rose-200" role="alert"><span>{statusError}</span><button type="button" onClick={() => void loadStatus()} className="shrink-0 font-bold underline">{t("connection.retry")}</button></div>}
        {status?.state === "not_configured" && view !== "settings" && <button type="button" onClick={() => setView("settings")}
          className="flex w-full items-center justify-between gap-3 rounded-[4px] border border-amber-500/30 bg-amber-500/[8%] p-3 text-left text-xs text-amber-200 transition hover:border-amber-400/60">
          <span>{t("connection.configure")}</span>
          <span className="shrink-0 font-bold underline">{t("views.settings")}</span>
        </button>}
        <nav className="flex gap-1 overflow-x-auto border-b border-[#263247] pb-px" aria-label={t("views.label")}>
          {VIEWS.map((item) => { const Icon = item.icon; return <button key={item.id} type="button" onClick={() => setView(item.id)}
            className={`flex shrink-0 items-center gap-2 border-b-2 px-3 py-2 text-xs font-bold transition ${view === item.id ? "border-cyan-300 text-cyan-200" : "border-transparent text-[#8d9ab0] hover:text-[#d4deeb]"}`}>
            <Icon size={14} />{t(`views.${item.id}`)}
          </button> })}
        </nav>
        {view === "search" && <div className="space-y-4">
          <SearchPanel loading={searching} disabled={status?.state !== "ready"}
            onSearch={(filters) => void search(filters)} interpreted={searchResponse?.interpreted ?? null} />
          <ResultGrid response={searchResponse} searched={searched} error={searchError} onQueued={() => setQueueRefresh((value) => value + 1)} />
        </div>}
        {view === "queue" && <JobsPanel mode="queue" refreshKey={queueRefresh} />}
        {view === "history" && <JobsPanel mode="history" />}
        {view === "settings" && <SettingsPanel status={status} details={connection} loading={testing}
          statusLoading={statusLoading} error={connectionError} onTest={() => void testConnections()} />}
      </div>
    </main>
  </CockpitShell>
}
