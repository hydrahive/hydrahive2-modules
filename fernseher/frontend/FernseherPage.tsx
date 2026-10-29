import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { RefreshCw } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { getSettings, getStatus, type TvSettings, type TvStatus } from "./api"
import { errorKey } from "./logic"
import { NowPlaying } from "./NowPlaying"
import { Remote } from "./Remote"
import { Setup } from "./Setup"

export function FernseherPage() {
  const { t } = useTranslation("fernseher")
  const isAdmin = useAuthStore((s: { role?: string | null }) => s.role) === "admin"
  const [cfg, setCfg] = useState<TvSettings | null>(null)
  const [status, setStatus] = useState<TvStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Laden ohne sofortiges setState: Zustand ändert sich erst in den Antworten (react-hooks/set-state-in-effect)
  const fetchAll = useCallback(() => getSettings().then((s) => {
    setCfg(s)
    if (!s.configured) { setStatus(null); setError(null); return }
    return getStatus().then((st) => { setStatus(st); setError(null) })
      .catch((e) => { setStatus(null); setError(t(errorKey(e))) })
  }).catch((e) => setError(t(errorKey(e)))), [t])

  const load = () => { setLoading(true); fetchAll().finally(() => setLoading(false)) }

  useEffect(() => { fetchAll() }, [fetchAll])

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{cfg?.name || t("title")}</h1>
          <p className="text-sm text-zinc-400">{t("subtitle")}</p>
        </div>
        <button onClick={load} disabled={loading} aria-label={t("refresh")}
          className="flex min-h-11 items-center gap-1.5 rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-700 disabled:opacity-40">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          <span className="hidden sm:inline">{t("refresh")}</span>
        </button>
      </div>
      {cfg && !cfg.configured && !isAdmin && <p className="text-sm text-zinc-400">{t("setup.ask_admin")}</p>}
      {error && <p role="alert" className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</p>}
      {status && <NowPlaying status={status} />}
      {status && <Remote status={status} onChange={setStatus} />}
      {status && !isAdmin && <p className="text-xs text-zinc-500">{t("remote.only_admin")}</p>}
      {isAdmin && <Setup onSaved={load} />}
    </div>
  )
}
