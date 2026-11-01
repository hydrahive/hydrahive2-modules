import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { getSettings } from "./api"
import { ClientsPanel } from "./ClientsPanel"
import { DevicesPanel } from "./DevicesPanel"
import { NetPanel } from "./NetPanel"
import { OutagesPanel } from "./OutagesPanel"
import { OverviewPanel } from "./OverviewPanel"
import { SettingsPanel } from "./SettingsPanel"
import { TrafficPanel } from "./TrafficPanel"

type Tab = "overview" | "devices" | "clients" | "net" | "traffic" | "outages" | "settings"
const VIEW_TABS: Tab[] = ["overview", "devices", "clients", "net", "traffic", "outages"]

/** Modulseite Netzwerk: Übersicht, Geräte, Clients, Netz, Verkehr, Störungen (ansehen); Einrichtung nur mit network.configure. */
export function NetworkPage() {
  const { t } = useTranslation("network")
  const [tab, setTab] = useState<Tab>("overview")
  const [canConfigure, setCanConfigure] = useState(false)
  const [rev, setRev] = useState(0)
  // Darf ich einrichten? Der Server sagt es (403 = nein) – kein eigenes Rollen-Raten im Browser.
  useEffect(() => { getSettings().then(() => setCanConfigure(true)).catch(() => setCanConfigure(false)) }, [])
  const tabs: Tab[] = canConfigure ? [...VIEW_TABS, "settings"] : VIEW_TABS
  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-[#e8eef8]">{t("title")}</h1>
        <p className="text-sm text-[#c8d2df]">{t("subtitle")}</p>
      </header>
      <nav className="flex gap-1 overflow-x-auto border-b border-[rgb(var(--hh-s-rand,42_54_75))]" role="tablist">
        {tabs.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm ${tab === k ? "border-emerald-400 text-[#e8eef8]" : "border-transparent text-[#c8d2df] hover:text-[#e8eef8]"}`}>
            {t(`tab.${k}`)}
          </button>
        ))}
      </nav>
      {tab === "overview" && <OverviewPanel key={rev} canConfigure={canConfigure} />}
      {tab === "devices" && <DevicesPanel key={rev} />}
      {tab === "clients" && <ClientsPanel key={rev} />}
      {tab === "net" && <NetPanel key={rev} />}
      {tab === "traffic" && <TrafficPanel key={rev} />}
      {tab === "outages" && <OutagesPanel key={rev} />}
      {tab === "settings" && <SettingsPanel onSaved={() => setRev((r) => r + 1)} />}
    </div>
  )
}
