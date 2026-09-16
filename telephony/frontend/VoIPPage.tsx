import { AlertCircle, Loader2, PhoneCall, RefreshCw } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { FoundationOverview } from "./_FoundationOverview"
import { SectionPlaceholder } from "./_SectionPlaceholder"
import { RegistrationProbeSettings } from "./RegistrationProbeSettings"
import { telephonyApi } from "./api"
import { sections } from "./sections"
import type { TelephonyStatus, VoIPSection } from "./types"

export function VoIPPage() {
  const { t } = useTranslation("voip")
  const [active, setActive] = useState<VoIPSection>("overview")
  const [status, setStatus] = useState<TelephonyStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const loadStatus = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      setStatus(await telephonyApi.status())
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let mounted = true
    void telephonyApi.status()
      .then((result) => { if (mounted) setStatus(result) })
      .catch(() => { if (mounted) setError(true) })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])
  const activeDefinition = sections.find((section) => section.id === active) ?? sections[0]

  return (
    <CockpitShell title={t("title")} hideHeader>
      <CockpitTopbar active="/voip" />
      <main className="mx-auto max-w-7xl p-4 sm:p-6">
        <header className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="rounded-xl bg-indigo-500/10 p-3 text-indigo-400"><PhoneCall size={25} /></span>
            <div>
              <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
              <p className="text-sm text-zinc-500">{t("subtitle")}</p>
            </div>
          </div>
          <span className="w-fit rounded-full border border-zinc-700 bg-zinc-900 px-3 py-1 text-xs font-medium text-zinc-400">
            {t("foundation")} · {t("not_configured")}
          </span>
        </header>

        <nav className="mb-5 flex gap-1 overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900/60 p-1.5" aria-label="VoIP">
          {sections.map(({ id, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActive(id)}
              aria-pressed={active === id}
              className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${active === id ? "bg-indigo-500/15 text-indigo-300" : "text-zinc-500 hover:bg-zinc-800/70 hover:text-zinc-300"}`}
            >
              <Icon size={15} />
              {t(`sections.${id}`)}
            </button>
          ))}
        </nav>

        {loading && (
          <div role="status" className="flex min-h-64 items-center justify-center gap-2 text-sm text-zinc-500">
            <Loader2 size={17} className="animate-spin" /> {t("loading")}
          </div>
        )}
        {!loading && error && (
          <div role="alert" className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 text-center">
            <AlertCircle size={24} className="text-red-400" />
            <p className="mt-3 text-sm text-red-200">{t("status_error")}</p>
            <button type="button" onClick={() => void loadStatus()} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800">
              <RefreshCw size={14} /> {t("retry")}
            </button>
          </div>
        )}
        {!loading && !error && active === "overview" && <FoundationOverview loaded={status?.stage === "foundation"} />}
        {!loading && !error && active === "settings" && status && (
          <RegistrationProbeSettings
            registrar={status.probe_target.registrar}
            port={status.probe_target.port}
          />
        )}
        {!loading && !error && active !== "overview" && active !== "settings" && (
          <SectionPlaceholder section={active} icon={activeDefinition.icon} />
        )}
      </main>
    </CockpitShell>
  )
}
