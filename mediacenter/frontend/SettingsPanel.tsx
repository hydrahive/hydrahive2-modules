import { CheckCircle2, CircleAlert, ExternalLink, KeyRound, RefreshCw, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { ArrService, ConnectionTest, ModuleStatus } from "./types"

interface Props {
  status: ModuleStatus | null
  details: ConnectionTest | null
  loading: boolean
  statusLoading: boolean
  error: string | null
  onTest: () => void
}

type Level = "ok" | "warn" | "error"

/**
 * Eine Seite für alle Mediacenter-Dienste: Indexer, SABnzbd, Radarr, Sonarr.
 *
 * Vorher war der Zustand über mehrere Stellen verteilt und Radarr/Sonarr
 * tauchten überhaupt nicht auf. Alle Adressen und Schlüssel kommen aus dem
 * Credential-Store — diese Ansicht zeigt nur, was daraus folgt, und verlinkt
 * zum Pflegen dorthin. Kein zweiter Ort für dieselbe Information.
 */
export function SettingsPanel({ status, details, loading, statusLoading, error, onTest }: Props) {
  const { t } = useTranslation("mediacenter")
  const arr = details?.arr_services ?? []

  const arrRow = (service: "radarr" | "sonarr"): { level: Level; note: string } => {
    const configured = service === "radarr" ? status?.radarr_configured : status?.sonarr_configured
    if (!configured) return { level: "warn", note: t("settings.notConfigured") }
    const found = arr.find((entry: ArrService) => entry.service === service)
    if (!found) return { level: "ok", note: t("settings.configuredUntested") }
    if (found.reachable) return { level: "ok", note: `${found.app_name ?? ""} ${found.version ?? ""}`.trim() }
    return { level: "error", note: t(`settings.errors.${found.error}`, { defaultValue: found.error ?? "" }) }
  }

  return <section className="space-y-4" aria-label={t("settings.title")}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-sm font-bold text-[#e8eef8]">{t("settings.title")}</h2>
        <p className="mt-1 text-xs text-[#8d9ab0]">{t("settings.subtitle")}</p>
      </div>
      <button type="button" onClick={onTest} disabled={loading || status?.state !== "ready"}
        className="flex items-center gap-2 rounded-[4px] border border-[#34445d] bg-[#151e2d] px-3 py-2 text-xs font-bold text-[#d4deeb] transition hover:border-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-40">
        <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        {loading ? t("connection.testing") : t("connection.test")}
      </button>
    </div>

    {error && <p className="rounded-[4px] border border-rose-500/25 bg-rose-500/[8%] p-3 text-xs text-rose-200" role="alert">{error}</p>}
    {statusLoading && !status && <p className="text-xs text-[#8d9ab0]">{t("connection.loading")}</p>}

    <div className="space-y-2">
      <ServiceRow name={t("settings.services.indexer")} required
        level={status?.indexer_configured ? "ok" : "error"}
        note={status?.indexer_configured
          ? (details ? t("settings.indexerLimit", { limit: details.max_limit }) : t("settings.configuredUntested"))
          : t("settings.notConfigured")}
        credential="tresuere_token" />

      <ServiceRow name={t("settings.services.sab")} required
        level={status?.sab_configured ? "ok" : "error"}
        note={status?.sab_configured
          ? (details?.sab_version ? `SABnzbd ${details.sab_version}` : t("settings.configuredUntested"))
          : t("settings.notConfigured")}
        credential="sabnzb_token" />

      <ServiceRow name="Radarr" {...arrRow("radarr")} credential="radarr_token"
        origin={arr.find((e: ArrService) => e.service === "radarr")?.origin ?? null} />
      <ServiceRow name="Sonarr" {...arrRow("sonarr")} credential="sonarr_token"
        origin={arr.find((e: ArrService) => e.service === "sonarr")?.origin ?? null} />
    </div>

    <div className="rounded-[6px] border border-[#28354a] bg-[#0d141f] p-3">
      <div className="flex items-start gap-2">
        <KeyRound size={14} className="mt-0.5 shrink-0 text-cyan-300" />
        <div className="min-w-0 text-xs leading-relaxed text-[#a9b6c9]">
          <p>{t("settings.credentialHint")}</p>
          <a href="/credentials" className="mt-1.5 inline-flex items-center gap-1 font-bold text-cyan-200 hover:underline">
            {t("settings.openCredentials")}<ExternalLink size={11} />
          </a>
        </div>
      </div>
    </div>
  </section>
}

function ServiceRow({ name, level, note, credential, origin, required = false }: {
  name: string; level: Level; note: string; credential: string
  origin?: string | null; required?: boolean
}) {
  const Icon = level === "ok" ? CheckCircle2 : level === "warn" ? CircleAlert : XCircle
  const color = level === "ok" ? "text-emerald-300" : level === "warn" ? "text-amber-300" : "text-rose-300"
  return <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[6px] border border-[#28354a] bg-[#101724] px-3 py-2.5">
    <Icon size={15} className={`shrink-0 ${color}`} />
    <span className="text-xs font-bold text-[#e8eef8]">{name}</span>
    {!required && <span className="rounded-full bg-white/[6%] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#8d9ab0]">
      optional
    </span>}
    <span className="text-[11px] text-[#8d9ab0]">{note}</span>
    <span className="ml-auto flex items-center gap-3">
      {origin && <code className="text-[10px] text-[#5f6d82]">{origin}</code>}
      <code className="rounded bg-white/[5%] px-1.5 py-0.5 text-[10px] text-[#78869d]">{credential}</code>
    </span>
  </div>
}
