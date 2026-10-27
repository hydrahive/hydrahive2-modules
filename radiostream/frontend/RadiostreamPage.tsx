import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { getSource } from "./api"
import { Library } from "./Library"
import { SettingsPanel } from "./SettingsPanel"

type Tab = "library" | "settings"

/** Modulseite Radiostream (SPEC Etappe 1): Reiter Bibliothek; Admins zusätzlich Einstellungen. */
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

  const tabs: Tab[] = isAdmin ? ["library", "settings"] : ["library"]
  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
        <p className="text-sm text-zinc-400">{t("subtitle")}</p>
      </header>
      <nav className="flex gap-1 border-b border-white/10" role="tablist">
        {tabs.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === k ? "border-emerald-400 text-zinc-100" : "border-transparent text-zinc-400 hover:text-zinc-200"}`}>
            {t(`tab.${k}`)}
          </button>
        ))}
      </nav>
      {tab === "library"
        ? <Library key={rev} isAdmin={isAdmin} configured={configured} />
        : <SettingsPanel onSaved={() => { setRev((r) => r + 1); setTab("library") }} />}
    </div>
  )
}
