import { useTranslation } from "react-i18next"
import { RefreshCw } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { useMyAccess } from "@/features/access/useMyAccess"
import { ClorePanel } from "./components/ClorePanel"
import { CoinTable } from "./components/CoinTable"
import { PowerPanel } from "./components/PowerPanel"
import { RigsPanel } from "./components/RigsPanel"
import { SettingsPanel } from "./components/SettingsPanel"
import { isStale, minutesSince } from "./format"
import { useMining } from "./useMining"

export function MiningPage() {
  const { t } = useTranslation("mining")
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const access = useMyAccess()
  const canControl = isAdmin || access?.capabilities?.["mining.control"] !== undefined
  const { gpus, gpu, setGpu, overview, config, error, loading, refreshNow, saveConfig } = useMining()
  const age = minutesSince(overview?.fetched_at ?? null)
  const stale = isStale(overview?.fetched_at ?? null)

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-xs text-zinc-500">{t("subtitle")}</p>
        </div>
        {canControl && (
          <button onClick={refreshNow} disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-700 disabled:opacity-40">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span>{t("refresh")}</span>
          </button>
        )}
      </div>

      {error && <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}

      <RigsPanel canControl={canControl} powerActive={(config?.power_mode ?? "off") !== "off"} />

      <h2 className="pt-2 text-sm font-semibold text-zinc-200">{t("earnings_title")}</h2>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="text-zinc-400">{t("gpu")}</label>
        <select value={gpu} onChange={(e) => setGpu(e.target.value)}
          className="rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-zinc-100">
          {gpus.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
        <span className={stale ? "text-amber-300" : "text-zinc-500"}>
          {age === null ? t("never_fetched") : stale ? t("stale", { min: age }) : t("fresh", { min: age })}
        </span>
      </div>

      {overview && overview.rows.length > 0 && <CoinTable rows={overview.rows} hasEur={overview.usd_per_eur !== null} />}
      {overview && overview.rows.length === 0 && (
        <div className="rounded-lg border border-white/10 p-4 text-sm text-zinc-400">{t("empty")}</div>
      )}
      {overview && <p className="text-xs text-zinc-500">{t("reference_note", { date: overview.reference.fetched })} {t("estimated_note")}</p>}

      <ClorePanel usdPerEur={overview?.usd_per_eur ?? null} />

      {config && <SettingsPanel key={JSON.stringify(config)} config={config} canEdit={canControl} onSave={saveConfig} />}
      {config && canControl && <PowerPanel key={`p${JSON.stringify(config)}`} config={config} canEdit={canControl} onSave={saveConfig} />}
    </div>
  )
}
