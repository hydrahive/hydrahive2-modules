import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"

type Status = { enabled: boolean; worker_ready: boolean; tor_reachable: boolean }
type Policy = { enabled: boolean; max_chars: number; retention_days: number; allowed_modes: string[] }
type SearchOutput = { data?: { results?: Array<{ title: string; url: string; engine: string; confidence?: number }>; content_boundary?: string }; warning?: string }

export function OpenTorPage() {
  const { t } = useTranslation("opentor")
  const isAdmin = useAuthStore((state) => state.role) === "admin"
  const [status, setStatus] = useState<Status | null>(null)
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [query, setQuery] = useState("")
  const [url, setUrl] = useState("")
  const [results, setResults] = useState<SearchOutput | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const refresh = () => {
    Promise.all([
      api.get<Status>("/modules/opentor/status"),
      api.get<Policy>("/modules/opentor/policy"),
    ]).then(([nextStatus, nextPolicy]) => {
      setStatus(nextStatus)
      setPolicy(nextPolicy)
    }).catch((e) => setError(String(e)))
  }

  useEffect(() => { refresh() }, [])

  const search = () => {
    if (!query.trim()) return
    setBusy(true)
    setError(null)
    api.post<SearchOutput>("/modules/opentor/search", { query, mode: "threat_intel", limit: 10 })
      .then(setResults).catch((e) => setError(String(e))).finally(() => setBusy(false))
  }

  const fetchUrl = () => {
    if (!url.trim()) return
    setBusy(true)
    setError(null)
    api.post<SearchOutput>("/modules/opentor/fetch", { url, max_chars: 8000 })
      .then(setResults).catch((e) => setError(String(e))).finally(() => setBusy(false))
  }

  const toggle = () => {
    if (!policy) return
    api.put<Policy>("/modules/opentor/policy", { ...policy, enabled: !policy.enabled })
      .then((next) => { setPolicy(next); refresh() }).catch((e) => setError(String(e)))
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
        <p className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{t("warning")}</p>
      </div>

      {error && <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-zinc-900/60 p-4 text-sm text-zinc-300"><b>{t("status")}</b><br />{status?.enabled ? t("enabled") : t("disabled")}</div>
        <div className="rounded-lg border border-white/10 bg-zinc-900/60 p-4 text-sm text-zinc-300">Tor: {status?.tor_reachable ? "OK" : "—"}</div>
        <div className="rounded-lg border border-white/10 bg-zinc-900/60 p-4 text-sm text-zinc-300">Worker: {status?.worker_ready ? "OK" : t("unavailable")}</div>
      </div>

      {isAdmin && policy && <button onClick={toggle} className="rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-200 hover:bg-white/5">{policy.enabled ? t("adminDisable") : t("adminEnable")}</button>}

      <div className="space-y-2 rounded-xl border border-white/10 bg-zinc-900/40 p-4">
        <label className="block text-sm text-zinc-400">{t("query")}</label>
        <div className="flex gap-2"><input value={query} onChange={(e) => setQuery(e.target.value)} className="min-w-0 flex-1 rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" /><button disabled={busy || !query.trim()} onClick={search} className="rounded-lg bg-zinc-700 px-4 py-2 text-sm disabled:opacity-40">{t("search")}</button></div>
        <label className="block pt-3 text-sm text-zinc-400">{t("fetchUrl")}</label>
        <div className="flex gap-2"><input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" className="min-w-0 flex-1 rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" /><button disabled={busy || !url.trim()} onClick={fetchUrl} className="rounded-lg bg-zinc-700 px-4 py-2 text-sm disabled:opacity-40">{t("fetch")}</button></div>
      </div>

      <section className="space-y-2"><h2 className="text-sm font-semibold text-zinc-200">{t("results")} <span className="ml-2 text-xs text-amber-300">{results?.data?.content_boundary ?? ""}</span></h2>{!results ? <p className="text-sm text-zinc-500">{t("empty")}</p> : <pre className="max-h-[32rem] overflow-auto rounded-lg border border-white/10 bg-zinc-950 p-4 text-xs text-zinc-300">{JSON.stringify(results, null, 2)}</pre>}</section>
    </div>
  )
}
