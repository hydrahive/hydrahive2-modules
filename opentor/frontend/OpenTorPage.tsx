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
        <h1 className="text-lg font-semibold text-[#e8eef8]">{t("title")}</h1>
        <p className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{t("warning")}</p>
      </div>

      {error && <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-4 text-sm text-[#c8d2df]"><b>{t("status")}</b><br />{status?.enabled ? t("enabled") : t("disabled")}</div>
        <div className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-4 text-sm text-[#c8d2df]">Tor: {status?.tor_reachable ? "OK" : "—"}</div>
        <div className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-4 text-sm text-[#c8d2df]">Worker: {status?.worker_ready ? "OK" : t("unavailable")}</div>
      </div>

      {isAdmin && policy && <button onClick={toggle} className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-2 text-sm text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">{policy.enabled ? t("adminDisable") : t("adminEnable")}</button>}

      <div className="space-y-2 rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.4)] p-4">
        <label className="block text-sm text-[#c8d2df]">{t("query")}</label>
        <div className="flex gap-2"><input value={query} onChange={(e) => setQuery(e.target.value)} className="min-w-0 flex-1 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-2 text-sm text-[#e8eef8]" /><button disabled={busy || !query.trim()} onClick={search} className="rounded-lg bg-[rgb(var(--hh-s-hebung,27_37_54))] px-4 py-2 text-sm disabled:opacity-40">{t("search")}</button></div>
        <label className="block pt-3 text-sm text-[#c8d2df]">{t("fetchUrl")}</label>
        <div className="flex gap-2"><input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" className="min-w-0 flex-1 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-2 text-sm text-[#e8eef8]" /><button disabled={busy || !url.trim()} onClick={fetchUrl} className="rounded-lg bg-[rgb(var(--hh-s-hebung,27_37_54))] px-4 py-2 text-sm disabled:opacity-40">{t("fetch")}</button></div>
      </div>

      <section className="space-y-2"><h2 className="text-sm font-semibold text-[#e8eef8]">{t("results")} <span className="ml-2 text-xs text-amber-300">{results?.data?.content_boundary ?? ""}</span></h2>{!results ? <p className="text-sm text-[#9aa7bc]">{t("empty")}</p> : <pre className="max-h-[32rem] overflow-auto rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] p-4 text-xs text-[#c8d2df]">{JSON.stringify(results, null, 2)}</pre>}</section>
    </div>
  )
}
