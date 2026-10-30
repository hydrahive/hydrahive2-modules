import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { getSource } from "./api"
import { Library } from "./Library"
import { SettingsPanel } from "./SettingsPanel"
import { StationPanel } from "./StationPanel"

type Tab = "library" | "station" | "settings"

/** Modulseite Radiostream: Reiter Bibliothek und Sender (alle); Admins zusätzlich Musikquelle. */
export function RadiostreamPage() {
  const { t } = useTranslation("radiostream")
  const isAdmin = useAuthStore((s: { role?: string | null }) => s.role) === "admin"
  const [tab, setTab] = useState<Tab>("library")
  const [hasSource, setHasSource] = useState(false)
  const [rev, setRev] = useState(0)

  // Nur Admins dürfen die Quelle lesen; für alle anderen ist „eingerichtet“ egal (sie sehen keinen Knopf).
  useEffect(() => {
    if (isAdmin) getSource().then((s) => setHasSource(!!s.url)).catch(() => {})
  }, [isAdmin, rev])
  const configured = !isAdmin || hasSource

  const tabs: Tab[] = isAdmin ? ["library", "station", "settings"] : ["library", "station"]
  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-[#e8eef8]">{t("title")}</h1>
        <p className="text-sm text-[#c8d2df]">{t("subtitle")}</p>
      </header>
      <nav className="flex gap-1 border-b border-[rgb(var(--hh-s-rand,42_54_75))]" role="tablist">
        {tabs.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === k ? "border-emerald-400 text-[#e8eef8]" : "border-transparent text-[#c8d2df] hover:text-[#e8eef8]"}`}>
            {t(`tab.${k}`)}
          </button>
        ))}
      </nav>
      {tab === "library" && <Library key={rev} isAdmin={isAdmin} configured={configured} />}
      {tab === "station" && <StationPanel />}
      {tab === "settings" && <SettingsPanel onSaved={() => { setRev((r) => r + 1); setTab("library") }} />}
    </div>
  )
}
