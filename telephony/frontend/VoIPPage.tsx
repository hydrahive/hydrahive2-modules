import { AlertCircle, Loader2, PhoneCall, RefreshCw } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { FoundationOverview } from "./_FoundationOverview"
import { JobsSection } from "./_JobsSection"
import { SectionPlaceholder } from "./_SectionPlaceholder"
import { ConnectionSettings } from "./ConnectionSettings"
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
  useEffect(() => {
    if (active === "overview") void telephonyApi.status().then(setStatus).catch(() => undefined)
  }, [active])
  const activeDefinition = sections.find((section) => section.id === active) ?? sections[0]

  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden" hideHeader>
      <CockpitTopbar active="/voip" />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl p-4 sm:p-6">
          <header className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <span className="rounded-xl bg-[#69d7ff]/10 p-3 text-[#69d7ff]"><PhoneCall size={25} /></span>
              <div>
                <h1 className="text-xl font-semibold text-[#e8eef8]">{t("title")}</h1>
                <p className="text-sm text-[#9aa7bc]">{t("subtitle")}</p>
              </div>
            </div>
            <span data-voip-badge={status?.status ?? "unknown"}
              className="w-fit rounded-full border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-3 py-1 text-xs font-medium text-[#c8d2df]">
              {t("in_development")} · {t(`conn.status.${status?.status ?? "not_configured"}.title`)}
            </span>
          </header>

          <nav className="mb-5 flex gap-1 overflow-x-auto rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-1.5" aria-label="VoIP">
            {sections.map(({ id, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setActive(id)}
                aria-pressed={active === id}
                className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${active === id ? "bg-[#69d7ff]/15 text-[#69d7ff]" : "text-[#9aa7bc] hover:bg-[rgb(var(--hh-s-hebung,27_37_54)/0.7)] hover:text-[#c8d2df]"}`}
              >
                <Icon size={15} />
                {t(`sections.${id}`)}
              </button>
            ))}
          </nav>

          {loading && (
            <div role="status" className="flex min-h-64 items-center justify-center gap-2 text-sm text-[#9aa7bc]">
              <Loader2 size={17} className="animate-spin" /> {t("loading")}
            </div>
          )}
          {!loading && error && (
            <div role="alert" className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 text-center">
              <AlertCircle size={24} className="text-red-400" />
              <p className="mt-3 text-sm text-red-200">{t("status_error")}</p>
              <button type="button" onClick={() => void loadStatus()} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-2 text-sm text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">
                <RefreshCw size={14} /> {t("retry")}
              </button>
            </div>
          )}
          {!loading && !error && active === "overview" && status && (
            <FoundationOverview status={status.status} onSetup={() => setActive("settings")} />
          )}
          {!loading && !error && active === "settings" && <ConnectionSettings />}
          {!loading && !error && active === "jobs" && <JobsSection onSetup={() => setActive("settings")} />}
          {!loading && !error && !["overview", "settings", "jobs"].includes(active) && (
            <SectionPlaceholder section={active} icon={activeDefinition.icon} />
          )}
        </div>
      </main>
    </CockpitShell>
  )
}
