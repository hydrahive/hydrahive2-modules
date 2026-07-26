import { CheckCircle2, CircleAlert, PlugZap, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { ConnectionTest, ModuleStatus } from "./types"

interface Props {
  status: ModuleStatus | null
  details: ConnectionTest | null
  loading: boolean
  error: string | null
  onTest: () => void
}

function ServiceState({ label, configured, state }: { label: string; configured: boolean; state: string }) {
  const Icon = configured ? CheckCircle2 : CircleAlert
  return <div className="flex items-center gap-2 text-xs">
    <Icon size={14} className={configured ? "text-emerald-300" : "text-amber-300"} />
    <span className="text-[#d4deeb]">{label}</span>
    <span className="text-[#78869d]">{state}</span>
  </div>
}

export function ConnectionStatus({ status, details, loading, error, onTest }: Props) {
  const { t } = useTranslation("mediacenter")
  return <section className="rounded-[6px] border border-[#28354a] bg-[#101724] p-4" aria-label={t("connection.title")}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-2">
          <PlugZap size={16} className="text-cyan-300" />
          <h2 className="text-sm font-bold text-[#e8eef8]">{t("connection.title")}</h2>
        </div>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
          <ServiceState label="Treasure Maps" configured={status?.indexer_configured ?? false} state={t(status?.indexer_configured ? "connection.configured" : "connection.missing")} />
          <ServiceState label="SABnzbd" configured={status?.sab_configured ?? false} state={t(status?.sab_configured ? "connection.configured" : "connection.missing")} />
        </div>
      </div>
      <button type="button" onClick={onTest} disabled={loading || status?.state !== "ready"}
        className="flex items-center gap-2 rounded-[4px] border border-[#34445d] bg-[#151e2d] px-3 py-2 text-xs font-bold text-[#d4deeb] transition hover:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-40">
        <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        {loading ? t("connection.testing") : t("connection.test")}
      </button>
    </div>
    {details && <p className="mt-3 text-xs text-emerald-300">
      {t("connection.success", { version: details.sab_version ?? "–" })}
    </p>}
    {error && <p className="mt-3 text-xs text-rose-300" role="alert">{error}</p>}
    {status?.state === "not_configured" && <p className="mt-3 text-xs leading-5 text-amber-200/90">
      {t("connection.configure")}
    </p>}
  </section>
}
